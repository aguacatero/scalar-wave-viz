#!/usr/bin/env python3
"""Preview, then install two 10-minute macOS user LaunchAgents. No cloud scheduler."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys
from agy_autopilot import config

def launch_jobs(c, path, python):
    for p in c["projects"]:
        if not p.get("enabled",False): continue
        label="io.aguacatero.agy-autopilot."+p["id"]
        spec={
          "Label":label,
          "ProgramArguments":[python,str(Path(p["repo_path"])/"scripts/agy_autopilot.py"),
            "tick","--execute","--project",p["id"],"--config",str(path)],
          "StartInterval":600,
          "RunAtLoad":True,
          "ProcessType":"Background",
          "StandardOutPath":str(Path.home()/".local/state/agy-autopilot"/(p["id"]+".stdout.log")),
          "StandardErrorPath":str(Path.home()/".local/state/agy-autopilot"/(p["id"]+".stderr.log"))}
        yield label,spec

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,default=Path.home()/".config/agy-autopilot/config.json")
    parser.add_argument("--install",action="store_true")
    args=parser.parse_args()
    if sys.platform!="darwin":
        print("Install LaunchAgents from the actual macOS host",file=sys.stderr)
        return 1
    try:
        cfg=args.config.expanduser().resolve()
        c=config(cfg)
        agents=list(launch_jobs(c,cfg,sys.executable))
        if not agents: raise ValueError("No enabled projects")
        for p in c["projects"]:
            if p.get("enabled",False) and not (Path(p["repo_path"])/"scripts/agy_autopilot.py").is_file():
                raise ValueError("Missing local project script: "+p["repo_path"])
        for label,spec in agents:
            dest=Path.home()/"Library/LaunchAgents"/(label+".plist")
            print(label,"->",dest,"(every 10 minutes)")
            if args.install:
                dest.parent.mkdir(parents=True,exist_ok=True)
                Path.home().joinpath(".local/state/agy-autopilot").mkdir(parents=True,exist_ok=True,mode=0o700)
                dest.write_bytes(plistlib.dumps(spec))
                cmd=["launchctl","bootstrap","gui/"+str(os.getuid()),str(dest)]
                r=subprocess.run(cmd,capture_output=True,text=True)
                if r.returncode:
                    print("launchctl failed (maybe job already loaded):",r.stderr.strip(),file=sys.stderr)
                    return 1
        if not args.install: print("DRY RUN — add --install to actually activate")
        return 0
    except (ValueError,OSError) as exc:
        print("SETUP BLOCKED:",exc,file=sys.stderr)
        return 1

if __name__=="__main__": raise SystemExit(main())
