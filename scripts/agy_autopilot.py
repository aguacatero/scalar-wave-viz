#!/usr/bin/env python3
"""Fail-closed local AGY scheduler. Counts only runs launched by this scheduler."""
import argparse
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import time
import uuid

WINDOW = 5 * 3600
STATE = Path.home()/".local/state/agy-autopilot/ledger.sqlite3"
CONFIG = Path.home()/".config/agy-autopilot/config.json"

def config(path):
    c = json.loads(Path(path).expanduser().read_text())
    budget = c.get("token_budget_per_5h")
    if c.get("version") != 1 or type(budget) is not int or budget <= 0:
        raise ValueError("Set a real, conservative token_budget_per_5h; no work launched")
    ps = c.get("projects", [])
    if len(ps) < 2 or len({p["id"] for p in ps}) != len(ps):
        raise ValueError("Configure two distinct projects")
    if c.get("project_cap_fraction") != 0.35 or c.get("protected_fraction") != 0.30:
        raise ValueError("35% per project / 30% protected policy required")
    models = {p.get("model") for p in ps}
    if len(models) != 1 or not next(iter(models)) or not next(iter(models)).startswith("gemini-"):
        raise ValueError("Set the SAME explicit Gemini model for both projects (agy models)")
    for p in ps:
        if not Path(p["repo_path"]).is_absolute() or not p.get("repo_full_name"):
            raise ValueError("Set absolute clone paths and repo names")
    if not 1000 <= c.get("min_run_tokens",3000) <= c.get("max_run_tokens",12000) <= budget*.35:
        raise ValueError("Run allowance cannot exceed a project cap")
    if c.get("max_parallel",2) not in (1,2):
        raise ValueError("max_parallel must be 1 or 2")
    return c

def db(path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    cn=sqlite3.connect(str(path),timeout=30,isolation_level=None)
    cn.execute("PRAGMA busy_timeout=30000")
    cn.execute("PRAGMA journal_mode=WAL")
    cn.executescript("""
        CREATE TABLE IF NOT EXISTS usage(
          run_id TEXT PRIMARY KEY, project TEXT NOT NULL,
          timestamp REAL NOT NULL, tokens INTEGER NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reserved(
          run_id TEXT PRIMARY KEY, project TEXT NOT NULL,
          timestamp REAL NOT NULL, tokens INTEGER NOT NULL, expires REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_usage_at ON usage(timestamp);
    """)
    return cn

def recover(cn,now):
    # A crashed worker never gets free quota. Conservatively charge its reservation.
    for rid,p,t,n in cn.execute(
        "SELECT run_id,project,timestamp,tokens FROM reserved WHERE expires<=?",(now,)).fetchall():
        cn.execute("INSERT OR IGNORE INTO usage VALUES(?,?,?,?,?)",
                   (rid,p,t,n,"UNVERIFIED_EXPIRED"))
        cn.execute("DELETE FROM reserved WHERE run_id=?",(rid,))

def summary(cn,c,p,now):
    since=now-WINDOW
    rows=cn.execute(
        "SELECT project,SUM(tokens) FROM usage WHERE timestamp>? GROUP BY project",(since,)).fetchall()
    hold=cn.execute(
        "SELECT project,SUM(tokens) FROM reserved WHERE timestamp>? GROUP BY project",(since,)).fetchall()
    counts=dict(rows)
    for project,n in hold: counts[project]=counts.get(project,0)+n
    per=int(c["token_budget_per_5h"]*.35)
    combined=int(c["token_budget_per_5h"]*.70)
    total=sum(counts.values())
    spent=counts.get(p,0)
    ratio=spent/per
    wait=10 if ratio<.25 else 20 if ratio<.60 else 40 if ratio<.85 else 75
    last=cn.execute("SELECT MAX(timestamp) FROM usage WHERE project=?",(p,)).fetchone()[0]
    return dict(project=p,spent=spent,cap=per,combined_spent=total,
                combined_cap=combined,remaining=max(0,min(per-spent,combined-total)),
                cooldown_minutes=wait,next_eligible=(last+wait*60 if last else None),
                active=cn.execute("SELECT COUNT(*) FROM reserved").fetchone()[0])

def claim(cn,c,p,now,rid):
    cn.execute("BEGIN IMMEDIATE")
    try:
        recover(cn,now)
        s=summary(cn,c,p,now)
        cfg=next((x for x in c["projects"] if x["id"]==p),None)
        if not cfg or not cfg.get("enabled",False):
            reason="not enabled"
        elif s["active"]>=c.get("max_parallel",2):
            reason="parallel work slots full"
        elif cn.execute("SELECT COUNT(*) FROM reserved WHERE project=?",(p,)).fetchone()[0]:
            reason="project already running"
        elif s["next_eligible"] and now<s["next_eligible"]:
            reason="cooldown"
        elif s["remaining"]<c.get("min_run_tokens",3000):
            reason="project or shared budget exhausted"
        else:
            tokens=min(c.get("max_run_tokens",12000),s["remaining"])
            cn.execute("INSERT INTO reserved VALUES(?,?,?,?,?)",
                       (rid,p,now,tokens,now+c.get("timeout_seconds",900)+120))
            cn.execute("COMMIT")
            return tokens,s
        cn.execute("COMMIT")
        return 0,dict(s,reason=reason)
    except Exception:
        cn.execute("ROLLBACK")
        raise

def settle(cn,rid,p,observed,success):
    cn.execute("BEGIN IMMEDIATE")
    try:
        row=cn.execute("SELECT timestamp,tokens FROM reserved WHERE run_id=? AND project=?",(rid,p)).fetchone()
        if not row: raise RuntimeError("Missing reservation; cannot account for this run")
        when,cap=row
        n=observed if success and observed is not None else max(cap,observed or 0)
        status="SUCCESS" if success and observed is not None and n<=cap else "UNVERIFIED_OR_OVER_LIMIT"
        cn.execute("INSERT INTO usage VALUES(?,?,?,?,?)",(rid,p,when,n,status))
        cn.execute("DELETE FROM reserved WHERE run_id=?",(rid,))
        cn.execute("COMMIT")
        return n,status
    except Exception:
        cn.execute("ROLLBACK")
        raise

def run(c,p,allowance):
    repo=Path(p["repo_path"])
    skill=repo/".agents/skills/fresh-session/SKILL.md"
    if not (repo/".git").exists() or not skill.is_file():
        return None,False,"Missing repo checkout or fresh-session skill"
    prompt=("NEW independent conversation. In this repo, read "
            ".agents/skills/fresh-session/SKILL.md and follow it. "
            "Refresh current GitHub issues/reviews and commit status. "
            "Complete one bounded, authorized unit of work; checkpoint safely. "
            f"Planned maximum {allowance} tokens. No merges, spending, or unreviewed promotion.")
    cmd=[c.get("agy_binary","agy"),"-p",prompt,"--model",p["model"],
         "--output-format","stream-json","--print-timeout",
         str(max(1,c.get("timeout_seconds",900)//60))+"m"]
    used=None
    done="NO_RESULT"
    timeout=time.monotonic()+c.get("timeout_seconds",900)+15
    try:
        with subprocess.Popen(cmd,cwd=str(repo),stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,bufsize=0) as proc:
            sel=selectors.DefaultSelector()
            sel.register(proc.stdout,selectors.EVENT_READ)
            partial=b""
            while sel.get_map():
                if time.monotonic()>timeout:
                    done="TIMEOUT"
                    proc.terminate()
                    break
                for key,_ in sel.select(timeout=.5):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:
                        sel.unregister(key.fileobj)
                        continue
                    partial+=chunk
                    while b"\n" in partial:
                        line,partial=partial.split(b"\n",1)
                        try: event=json.loads(line)
                        except (ValueError,UnicodeDecodeError): continue
                        if not isinstance(event,dict): continue
                        for part in ("step_update","result"):
                            obj=event.get(part)
                            if isinstance(obj,dict):
                                token=obj.get("usage",{}).get("total_tokens")
                                if type(token) is int and token>=0:
                                    used=max(used or 0,token)
                        if event.get("event")=="result":
                            done=event.get("result",{}).get("status","UNKNOWN")
                        # Best effort live cutoff; token observations may be delayed.
                        if used is not None and used>=allowance:
                            proc.terminate()
                            break
                if proc.poll() is not None and not sel.get_map(): break
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            ok=(done=="SUCCESS" and proc.returncode==0 and
                used is not None and used<=allowance)
            return used,ok,done
    except OSError as exc:
        return used,False,"AGY execution error: "+type(exc).__name__

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("command",choices=("status","tick"))
    ap.add_argument("--config",type=Path,default=CONFIG)
    ap.add_argument("--state",type=Path,default=STATE)
    ap.add_argument("--project")
    ap.add_argument("--execute",action="store_true")
    a=ap.parse_args()
    try:
        c=config(a.config)
        cn=db(a.state)
        now=time.time()
        if a.command=="status":
            cn.execute("BEGIN IMMEDIATE")
            recover(cn,now)
            cn.execute("COMMIT")
            print(json.dumps({"quota_source":"LOCAL_CONFIG_NOT_GOOGLE",
              "window_hours":5,"projects":[summary(cn,c,p["id"],now) for p in c["projects"]]},indent=2))
            return 0
        if a.project not in [p["id"] for p in c["projects"]]:
            raise ValueError("Specify --project with an ID from the config")
        if not a.execute:
            print(json.dumps({"dry_run":True,**summary(cn,c,a.project,now)},indent=2))
            return 0
        rid=uuid.uuid4().hex
        allowance,info=claim(cn,c,a.project,now,rid)
        if not allowance:
            print(json.dumps({"launched":False,**info}))
            return 2
        p=next(p for p in c["projects"] if p["id"]==a.project)
        used,ok,reason=run(c,p,allowance)
        charged,state=settle(cn,rid,a.project,used,ok)
        print(json.dumps({"project":a.project,"charged":charged,
              "measured":used,"allowance":allowance,"state":state,
              "agy_status":reason}))
        return 0 if state=="SUCCESS" else 1
    except (ValueError,OSError,sqlite3.Error,RuntimeError) as exc:
        print("AUTOPILOT BLOCKED: "+str(exc),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
