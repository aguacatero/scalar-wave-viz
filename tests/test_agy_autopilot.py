"""Unit tests for the local 5-hour, two-project scheduler. No AGY credentials used."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SRC=Path(__file__).resolve().parents[1]/"scripts/agy_autopilot.py"
spec=importlib.util.spec_from_file_location("agy_autopilot",SRC)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def settings(path):
    return {"version":1,"token_budget_per_5h":100000,
      "project_cap_fraction":0.35,"protected_fraction":0.30,
      "max_run_tokens":10000,"min_run_tokens":3000,"max_parallel":2,
      "projects":[
        {"id":"scalar-wave-viz","repo_full_name":"aguacatero/scalar-wave-viz",
         "repo_path":str(path),"model":"gemini-test","enabled":True},
        {"id":"septuagint-diaspora-book","repo_full_name":"aguacatero/septuagint-diaspora-book",
         "repo_path":str(path),"model":"gemini-test","enabled":True}]}

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)
        self.c=settings(self.path)
        self.db=a.db(self.path/"test.sqlite3")
        self.t=1700000000.0
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_fail_closed_unknown_quota_and_non_google_models(self):
        path=self.path/"config.json"
        path.write_text(json.dumps(dict(self.c,token_budget_per_5h=None)))
        with self.assertRaises(ValueError): a.config(path)
        self.c["projects"][0]["model"]="claude-not-allowed"
        path.write_text(json.dumps(self.c))
        with self.assertRaises(ValueError): a.config(path)

    def test_per_project_35_percent_and_30_percent_reserved(self):
        for p in ("scalar-wave-viz","septuagint-diaspora-book"):
            for i,n in enumerate((10000,10000,10000,5000)):
                self.db.execute("INSERT INTO usage VALUES(?,?,?,?,?)",
                                (p+str(i),p,self.t-1,n,"SUCCESS"))
        for p in ("scalar-wave-viz","septuagint-diaspora-book"):
            s=a.summary(self.db,self.c,p,self.t)
            self.assertEqual(s["cap"],35000)
            self.assertEqual(s["combined_cap"],70000)
            self.assertEqual(s["remaining"],0)

    def test_concurrent_and_no_duplicate_project(self):
        n,_=a.claim(self.db,self.c,"scalar-wave-viz",self.t,"a")
        self.assertEqual(n,10000)
        n,info=a.claim(self.db,self.c,"scalar-wave-viz",self.t,"b")
        self.assertEqual(n,0)
        self.assertIn("already",info["reason"])
        n,_=a.claim(self.db,self.c,"septuagint-diaspora-book",self.t,"c")
        self.assertEqual(n,10000)
        n,info=a.claim(self.db,self.c,"scalar-wave-viz",self.t,"d")
        self.assertEqual(n,0)
        self.assertIn("parallel",info["reason"])

    def test_missing_usage_charges_max_and_enforces_cooldown(self):
        a.claim(self.db,self.c,"scalar-wave-viz",self.t,"a")
        n,state=a.settle(self.db,"a","scalar-wave-viz",None,False)
        self.assertEqual(n,10000)
        self.assertEqual(state,"UNVERIFIED_OR_OVER_LIMIT")
        n,info=a.claim(self.db,self.c,"scalar-wave-viz",self.t+60,"b")
        self.assertEqual(n,0)
        self.assertEqual(info["reason"],"cooldown")

    def test_expired_reservations_are_charged(self):
        a.claim(self.db,self.c,"scalar-wave-viz",self.t,"a")
        self.db.execute("BEGIN IMMEDIATE")
        a.recover(self.db,self.t+5000)
        self.db.execute("COMMIT")
        row=self.db.execute("SELECT tokens,status FROM usage WHERE run_id='a'").fetchone()
        self.assertEqual(row,(10000,"UNVERIFIED_EXPIRED"))

    def test_window_aging_reopens_allocation(self):
        self.db.execute("INSERT INTO usage VALUES(?,?,?,?,?)",
                        ("old","scalar-wave-viz",self.t-20,30000,"SUCCESS"))
        self.assertEqual(a.summary(self.db,self.c,"scalar-wave-viz",self.t)["remaining"],5000)
        self.assertEqual(a.summary(self.db,self.c,"scalar-wave-viz",self.t+a.WINDOW+10)["remaining"],35000)

if __name__=="__main__":unittest.main()
