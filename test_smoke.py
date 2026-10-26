import os, re, datetime as dt
os.environ.pop("PORT", None)
if os.path.exists("nidhisetu.db"): os.remove("nidhisetu.db")
from app import app
c = lambda: app.test_client()
def login(cl, u, p): return cl.post("/login", data={"username": u, "password": p}, follow_redirects=True)
inst, off, adm = c(), c(), c()
assert b"My FDRs" in login(inst, "college", "college123").data
t = dt.date.today()
r = inst.post("/fdr/new", data={"fdr_no": "FDR123", "bank": "SBI", "bank_type": "Scheduled commercial", "amount": "600000", "issue": str(t - dt.timedelta(days=400)), "maturity": str(t + dt.timedelta(days=20)), "seats": "300", "lien": "on", "signatory": "A"}, follow_redirects=True)
assert b"FDR123" in r.data; print("submit ok")
login(off, "officer", "officer123"); login(adm, "admin", "admin123")
assert b"Runway" in off.get("/dashboard").data
for a in ("doc_ok", "scrutiny", "verify"): off.post("/fdr/1/act", data={"action": a})
r = off.post("/fdr/1/act", data={"action": "bank_link"}, follow_redirects=True)
link = re.search(r"/bank/[\w\-]+", r.data.decode()).group(0)
assert b"Release readiness: BLOCKED" in r.data
b = c(); assert b"FDR123" in b.get(link).data
assert b"recorded" in b.post(link, data={"name": "X", "designation": "Mgr", "decision": "confirm"}).data
assert b"invalid" in b.get(link).data; print("bank link ok")
inst.post("/fdr/1/release", data={"reason": "closing", "cycle": "on"})
assert b"READY" in off.get("/releases").data
off.post("/release/1", data={"action": "recommend"}); adm.post("/release/1", data={"action": "approve"})
code = re.search(r"Order code: <b>(\w+)", adm.get("/order/1").data.decode()).group(1)
assert b"VALID" in c().get("/verify/" + code).data; print("release ok")
assert b"verified" in adm.get("/audit").data and b"CHAIN BROKEN" not in adm.get("/audit").data; print("audit ok")
assert b"FDR123" in adm.get("/export.csv").data
assert off.get("/fdr/new").status_code == 403
dup = inst.post("/fdr/new", data={"fdr_no": "FDR123", "bank": "SBI", "amount": "1000", "issue": str(t), "maturity": str(t)}, follow_redirects=True)
assert b"already submitted" in dup.data and b"below" in dup.data; print("flags ok\nALL TESTS PASSED")
