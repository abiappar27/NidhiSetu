import os, sqlite3, hashlib, secrets, io, csv, json, datetime as dt, uuid
from functools import wraps
from flask import (Flask, request, session, redirect, url_for, flash, render_template, abort,
                   send_file, Response)
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "nidhisetu.db")
UP = os.path.join(BASE, "uploads"); os.makedirs(UP, exist_ok=True)
MIN_AMOUNT = int(os.environ.get("MIN_AMOUNT", 500000))   # configurable rule (set per AICTE norms)
MIN_MONTHS = int(os.environ.get("MIN_MONTHS", 12))       # configurable minimum tenure
app = Flask(__name__)
kf = os.path.join(BASE, ".secret")
if not os.path.exists(kf): open(kf, "w").write(secrets.token_hex(32))
app.secret_key = open(kf).read()
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

def q(sql, a=(), one=False, commit=False):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    cur = c.execute(sql, a)
    r = (cur.fetchone() if one else cur.fetchall()) if not commit else cur.lastrowid
    c.commit(); c.close(); return r

def init():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS institutions(id INTEGER PRIMARY KEY, name TEXT, aicte_id TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw TEXT, role TEXT, inst_id INTEGER, name TEXT);
    CREATE TABLE IF NOT EXISTS fdrs(id INTEGER PRIMARY KEY, inst_id INTEGER, fdr_no TEXT, bank TEXT, bank_type TEXT, amount REAL,
      issue TEXT, maturity TEXT, lien INTEGER, seats INTEGER, signatory TEXT, doc TEXT, doc_hash TEXT, doc_ok INTEGER DEFAULT 0,
      status TEXT DEFAULT 'submitted', scrutiny INTEGER DEFAULT 0, bank_conf_by TEXT, bank_conf_at TEXT, recon TEXT,
      flags TEXT, parent_id INTEGER, created TEXT);
    CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY, fdr_id INTEGER, expires TEXT, used INTEGER DEFAULT 0, kind TEXT);
    CREATE TABLE IF NOT EXISTS releases(id INTEGER PRIMARY KEY, fdr_id INTEGER, reason TEXT, cycle_closed INTEGER, status TEXT, code TEXT, created TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS remarks(id INTEGER PRIMARY KEY, fdr_id INTEGER, user TEXT, text TEXT, ts TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, ts TEXT, actor TEXT, action TEXT, detail TEXT, prev TEXT, hash TEXT);
    """); c.commit()
    if not c.execute("SELECT 1 FROM users").fetchone():
        c.execute("INSERT INTO institutions(name,aicte_id) VALUES('Demo Institute of Technology','1-0000001')")
        for u, p, r, i, n in [("admin", "admin123", "admin", None, "Regulation Bureau Head"),
                              ("officer", "officer123", "officer", None, "Section Officer"),
                              ("college", "college123", "institution", 1, "Demo Institute Registrar")]:
            c.execute("INSERT INTO users(username,pw,role,inst_id,name) VALUES(?,?,?,?,?)", (u, generate_password_hash(p), r, i, n))
        c.commit()
    c.close()

def audit(action, detail=""):
    actor = session.get("u", "system"); ts = dt.datetime.now().isoformat(timespec="seconds")
    last = q("SELECT hash FROM audit ORDER BY id DESC LIMIT 1", one=True)
    prev = last["hash"] if last else "GENESIS"
    h = hashlib.sha256(f"{prev}|{ts}|{actor}|{action}|{detail}".encode()).hexdigest()
    q("INSERT INTO audit(ts,actor,action,detail,prev,hash) VALUES(?,?,?,?,?,?)", (ts, actor, action, detail, prev, h), commit=True)

def d(s): return dt.date.fromisoformat(s)
def days_left(f): return (d(f["maturity"]) - dt.date.today()).days

def make_flags(f, fid=None):
    out = []
    i, m = d(f["issue"]), d(f["maturity"])
    if m <= i: out.append(("high", "Maturity date is not after the issue date."))
    elif (m - i).days < MIN_MONTHS * 30: out.append(("medium", f"Tenure is below the configured minimum of {MIN_MONTHS} months."))
    if m < dt.date.today(): out.append(("high", "FDR has already matured."))
    if f["amount"] < MIN_AMOUNT: out.append(("high", f"Amount is below the configured minimum of Rs {MIN_AMOUNT:,}."))
    if not f["lien"]: out.append(("high", "Lien in favour of AICTE is not declared."))
    if not f["doc"]: out.append(("medium", "No supporting document uploaded."))
    dup = q("SELECT f.id,i.name FROM fdrs f JOIN institutions i ON i.id=f.inst_id WHERE lower(f.fdr_no)=lower(?) AND f.bank=? AND f.id!=?", (f["fdr_no"], f["bank"], fid or 0))
    for r in dup:
        out.append(("high", f"Same FDR number and bank already submitted (case #{r['id']}, {r['name']})."))
    if f["doc_hash"]:
        for r in q("SELECT id FROM fdrs WHERE doc_hash=? AND id!=?", (f["doc_hash"], fid or 0)):
            out.append(("high", f"Identical document file already attached to case #{r['id']}."))
    return out

def level(f):
    fl = json.loads(f["flags"] or "[]"); high = any(s == "high" for s, _ in fl)
    l = 0
    if f["doc_ok"]: l = 1
    if l >= 1 and f["scrutiny"] and not high: l = 2
    if l >= 2 and f["bank_conf_by"]: l = 3
    if l >= 3 and f["recon"]: l = 4
    return l

def risk(f):
    if f["status"] in ("released", "renewed", "rejected"): return 0
    dl = days_left(f)
    base = 60 if dl < 0 else max(0, 60 * (90 - dl) / 90)
    renewed = q("SELECT 1 FROM fdrs WHERE parent_id=?", (f["id"],), one=True)
    r = base + (20 if (dl <= 60 and not renewed) else 0) + (10 if level(f) < 3 else 0)
    r += min(10, (f["seats"] or 0) / 50)
    return int(min(100, r))

def escalation(f):
    if f["status"] in ("released", "renewed", "rejected"): return "-"
    dl = days_left(f)
    if dl < 0: return "Overdue: Bureau Head"
    if dl <= 7: return "Bureau Head"
    if dl <= 15: return "Regional Officer"
    if dl <= 30: return "Section Officer"
    if dl <= 60: return "Institution reminder"
    return "-"

def view(f):
    f = dict(f); f["lvl"] = level(f); f["risk"] = risk(f); f["dl"] = days_left(f); f["esc"] = escalation(f)
    f["flaglist"] = json.loads(f["flags"] or "[]"); f["inst"] = (q("SELECT name FROM institutions WHERE id=?", (f["inst_id"],), one=True) or {"name": "?"})["name"]
    s = f["status"]
    f["label"] = {"released": "Released", "renewed": "Renewed", "rejected": "Rejected"}.get(s) or ("Matured" if f["dl"] < 0 else ("Active (pending verification)" if s == "submitted" else "Active"))
    return f

def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def w(*a, **k):
            if "u" not in session: return redirect(url_for("login"))
            if roles and session["role"] not in roles: abort(403)
            return fn(*a, **k)
        return w
    return deco

def get_fdr(fid):
    f = q("SELECT * FROM fdrs WHERE id=?", (fid,), one=True)
    if not f: abort(404)
    if session["role"] == "institution" and f["inst_id"] != session["inst"]: abort(403)
    return f

def readiness(f):
    f = dict(f); reasons = []
    if level(f) < 3: reasons.append("Bank confirmation (L3) is missing.")
    if any(s == "high" for s, _ in json.loads(f["flags"] or "[]")): reasons.append("Unresolved high-severity flags.")
    rel = q("SELECT cycle_closed FROM releases WHERE fdr_id=? ORDER BY id DESC LIMIT 1", (f["id"],), one=True)
    child = q("SELECT 1 FROM fdrs WHERE parent_id=? AND status='verified'", (f["id"],), one=True)
    if not ((rel and rel["cycle_closed"]) or child): reasons.append("Approval cycle not declared closed and no verified replacement FDR.")
    return (not reasons), reasons

# ---------------- routes ----------------
@app.route("/")
def home(): return redirect(url_for("dash") if "u" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE username=?", (request.form["username"].strip(),), one=True)
        if u and check_password_hash(u["pw"], request.form["password"]):
            session.clear(); session.update(u=u["username"], role=u["role"], inst=u["inst_id"], name=u["name"]); audit("login"); return redirect(url_for("dash"))
        flash("Invalid username or password.", "err")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        try:
            iid = q("INSERT INTO institutions(name,aicte_id) VALUES(?,?)", (f["name"].strip(), f["aicte_id"].strip()), commit=True)
            q("INSERT INTO users(username,pw,role,inst_id,name) VALUES(?,?,?,?,?)", (f["username"].strip(), generate_password_hash(f["password"]), "institution", iid, f["name"].strip()), commit=True)
            flash("Registered. Please log in.", "ok"); return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or AICTE ID already exists.", "err")
    return render_template("register.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.route("/dashboard")
@login_required()
def dash():
    if session["role"] == "institution":
        rows = [view(r) for r in q("SELECT * FROM fdrs WHERE inst_id=? ORDER BY id DESC", (session["inst"],))]
        return render_template("dash_inst.html", rows=rows)
    rows = [view(r) for r in q("SELECT * FROM fdrs ORDER BY id DESC")]
    live = [r for r in rows if r["status"] not in ("released", "renewed", "rejected")]
    stats = {"Total": len(rows), "Active": sum(1 for r in live if r["dl"] >= 0), "Expiring in 30 days": sum(1 for r in live if 0 <= r["dl"] <= 30),
             "Matured / overdue": sum(1 for r in live if r["dl"] < 0), "Pending verification": sum(1 for r in rows if r["status"] == "submitted"),
             "Renewed": sum(1 for r in rows if r["status"] == "renewed"), "Released": sum(1 for r in rows if r["status"] == "released"),
             "Trust L3+": sum(1 for r in rows if r["lvl"] >= 3)}
    runway = sorted(live, key=lambda r: -r["risk"])[:15]
    banks = {}
    for r in live: b = banks.setdefault(r["bank"], [0, 0.0]); b[0] += 1; b[1] += r["amount"]
    rel = q("SELECT COUNT(*) c FROM releases WHERE status IN ('requested','recommended')", one=True)["c"]
    return render_template("dash_officer.html", stats=stats, runway=runway, banks=sorted(banks.items(), key=lambda x: -x[1][1]), rel=rel)

@app.route("/fdr/new", methods=["GET", "POST"])
@login_required("institution")
def fdr_new():
    parent = request.args.get("parent", type=int)
    if request.method == "POST":
        f = request.form
        try:
            rec = {"fdr_no": f["fdr_no"].strip(), "bank": f["bank"].strip(), "amount": float(f["amount"]), "issue": f["issue"], "maturity": f["maturity"],
                   "lien": 1 if f.get("lien") else 0, "doc": None, "doc_hash": None}
            d(rec["issue"]); d(rec["maturity"])
        except Exception:
            flash("Please enter valid numbers and dates.", "err"); return render_template("fdr_new.html", parent=parent)
        doc_ok = 0; file = request.files.get("doc")
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext not in ("pdf", "png", "jpg", "jpeg"): flash("Only PDF, PNG or JPG files are allowed.", "err"); return render_template("fdr_new.html", parent=parent)
            data = file.read(); rec["doc_hash"] = hashlib.sha256(data).hexdigest(); rec["doc"] = uuid.uuid4().hex + "." + ext
            open(os.path.join(UP, rec["doc"]), "wb").write(data)
            if ext == "pdf" and PdfReader:
                try:
                    txt = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
                    doc_ok = 1 if rec["fdr_no"].lower() in txt.lower() else 0
                except Exception: pass
        rec["flags"] = json.dumps(make_flags(rec))
        fid = q("INSERT INTO fdrs(inst_id,fdr_no,bank,bank_type,amount,issue,maturity,lien,seats,signatory,doc,doc_hash,doc_ok,flags,parent_id,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (session["inst"], rec["fdr_no"], rec["bank"], f.get("bank_type", ""), rec["amount"], rec["issue"], rec["maturity"], rec["lien"], int(f.get("seats") or 0),
                 f.get("signatory", ""), rec["doc"], rec["doc_hash"], doc_ok, rec["flags"], parent, dt.datetime.now().isoformat(timespec="seconds")), commit=True)
        audit("fdr_submitted", f"case {fid} {rec['fdr_no']}" + (f" renewal of {parent}" if parent else ""))
        flash("FDR submitted. " + ("Document text matched the FDR number (L1)." if doc_ok else "Awaiting officer document check."), "ok")
        return redirect(url_for("fdr_detail", fid=fid))
    return render_template("fdr_new.html", parent=parent)

@app.route("/fdr/<int:fid>")
@login_required()
def fdr_detail(fid):
    f = view(get_fdr(fid))
    chain = []
    p = f["parent_id"]
    while p:
        r = q("SELECT id,fdr_no,maturity,status FROM fdrs WHERE id=?", (p,), one=True)
        if not r: break
        chain.insert(0, r); p = q("SELECT parent_id FROM fdrs WHERE id=?", (p,), one=True)["parent_id"]
    kids = q("SELECT id,fdr_no,maturity,status FROM fdrs WHERE parent_id=?", (fid,))
    ok, reasons = readiness(f)
    return render_template("fdr_detail.html", f=f, chain=chain, kids=kids, remarks=q("SELECT * FROM remarks WHERE fdr_id=? ORDER BY id DESC", (fid,)),
                           rels=q("SELECT * FROM releases WHERE fdr_id=? ORDER BY id DESC", (fid,)), ready=ok, reasons=reasons,
                           link=session.pop("link_%d" % fid, None))

@app.route("/fdr/<int:fid>/doc")
@login_required()
def fdr_doc(fid):
    f = get_fdr(fid)
    if not f["doc"]: abort(404)
    return send_file(os.path.join(UP, f["doc"]))

@app.route("/fdr/<int:fid>/act", methods=["POST"])
@login_required("officer", "admin")
def fdr_act(fid):
    f = get_fdr(fid); a = request.form["action"]
    if a == "doc_ok": q("UPDATE fdrs SET doc_ok=1 WHERE id=?", (fid,), commit=True); msg = "Document checked manually (L1)."
    elif a == "scrutiny": q("UPDATE fdrs SET scrutiny=1 WHERE id=?", (fid,), commit=True); msg = "Scrutiny passed."
    elif a == "verify":
        q("UPDATE fdrs SET status='verified' WHERE id=?", (fid,), commit=True)
        if f["parent_id"]: q("UPDATE fdrs SET status='renewed' WHERE id=?", (f["parent_id"],), commit=True)
        msg = "Case marked verified."
    elif a == "reject": q("UPDATE fdrs SET status='rejected' WHERE id=?", (fid,), commit=True); msg = "Case rejected."
    elif a == "recon":
        ref = request.form.get("ref", "").strip()
        if not ref: flash("Enter the AICTE receipt / lien reference.", "err"); return redirect(url_for("fdr_detail", fid=fid))
        q("UPDATE fdrs SET recon=? WHERE id=?", (ref, fid), commit=True); msg = "Reconciled with AICTE record (L4)."
    elif a == "bank_link":
        tok = secrets.token_urlsafe(24)
        q("INSERT INTO tokens(token,fdr_id,expires,kind) VALUES(?,?,?,?)", (tok, fid, (dt.date.today() + dt.timedelta(days=7)).isoformat(), "confirm"), commit=True)
        session["link_%d" % fid] = request.host_url.rstrip("/") + url_for("bank_confirm", token=tok); msg = "Bank confirmation link created (valid 7 days)."
    elif a == "remark":
        t = request.form.get("text", "").strip()
        if t: q("INSERT INTO remarks(fdr_id,user,text,ts) VALUES(?,?,?,?)", (fid, session["u"], t, dt.datetime.now().strftime("%Y-%m-%d %H:%M")), commit=True)
        msg = "Remark added."
    else: abort(400)
    audit("fdr_" + a, f"case {fid}"); flash(msg, "ok"); return redirect(url_for("fdr_detail", fid=fid))

@app.route("/bank/<token>", methods=["GET", "POST"])
def bank_confirm(token):
    t = q("SELECT * FROM tokens WHERE token=?", (token,), one=True)
    if not t or t["used"] or t["expires"] < dt.date.today().isoformat(): return render_template("bank.html", f=None, msg="This link is invalid, expired or already used."), 410
    f = q("SELECT * FROM fdrs WHERE id=?", (t["fdr_id"],), one=True)
    if request.method == "POST":
        who = f"{request.form['name'].strip()} ({request.form['designation'].strip()})"
        q("UPDATE tokens SET used=1 WHERE token=?", (token,), commit=True)
        if request.form["decision"] == "confirm":
            q("UPDATE fdrs SET bank_conf_by=?, bank_conf_at=? WHERE id=?", (who, dt.datetime.now().isoformat(timespec="seconds"), f["id"]), commit=True)
            audit("bank_confirmed", f"case {f['id']} by {who}"); m = "Thank you. Confirmation recorded."
        else:
            fl = json.loads(f["flags"] or "[]"); fl.append(["high", "Bank DISPUTED this FDR: " + request.form.get("reason", "no reason given")])
            q("UPDATE fdrs SET flags=? WHERE id=?", (json.dumps(fl), f["id"]), commit=True)
            audit("bank_disputed", f"case {f['id']} by {who}"); m = "Dispute recorded. AICTE will follow up."
        return render_template("bank.html", f=None, msg=m)
    return render_template("bank.html", f=f, msg=None)

@app.route("/fdr/<int:fid>/release", methods=["POST"])
@login_required("institution")
def release_req(fid):
    get_fdr(fid)
    q("INSERT INTO releases(fdr_id,reason,cycle_closed,status,created) VALUES(?,?,?,?,?)", (fid, request.form["reason"], 1 if request.form.get("cycle") else 0, "requested", dt.date.today().isoformat()), commit=True)
    audit("release_requested", f"case {fid}"); flash("Release request submitted.", "ok"); return redirect(url_for("fdr_detail", fid=fid))

@app.route("/releases")
@login_required("officer", "admin")
def releases():
    rows = []
    for r in q("SELECT * FROM releases ORDER BY id DESC"):
        f = view(q("SELECT * FROM fdrs WHERE id=?", (r["fdr_id"],), one=True)); ok, reasons = readiness(f); rows.append((r, f, ok, reasons))
    return render_template("releases.html", rows=rows)

@app.route("/release/<int:rid>", methods=["POST"])
@login_required("officer", "admin")
def release_decide(rid):
    r = q("SELECT * FROM releases WHERE id=?", (rid,), one=True) or abort(404); a = request.form["action"]
    f = q("SELECT * FROM fdrs WHERE id=?", (r["fdr_id"],), one=True); ok, reasons = readiness(f)
    if a == "recommend":
        if not ok: flash("Blocked: " + " ".join(reasons), "err"); return redirect(url_for("releases"))
        q("UPDATE releases SET status='recommended' WHERE id=?", (rid,), commit=True)
    elif a == "approve":
        if session["role"] != "admin": abort(403)
        if r["status"] != "recommended" or not ok: flash("Only a ready, recommended request can be approved.", "err"); return redirect(url_for("releases"))
        q("UPDATE releases SET status='approved', code=? WHERE id=?", (uuid.uuid4().hex[:12].upper(), rid), commit=True)
        q("UPDATE fdrs SET status='released' WHERE id=?", (f["id"],), commit=True)
    elif a == "reject": q("UPDATE releases SET status='rejected', note=? WHERE id=?", (request.form.get("note", ""), rid), commit=True)
    audit("release_" + a, f"release {rid} case {f['id']}"); flash("Done.", "ok"); return redirect(url_for("releases"))

@app.route("/order/<int:rid>")
@login_required()
def order(rid):
    r = q("SELECT * FROM releases WHERE id=? AND status='approved'", (rid,), one=True) or abort(404)
    f = view(get_fdr(r["fdr_id"])); return render_template("order.html", r=r, f=f, url=request.host_url.rstrip("/") + url_for("verify", code=r["code"]))

@app.route("/verify/<code>")
def verify(code):
    r = q("SELECT * FROM releases WHERE code=? AND status='approved'", (code,), one=True)
    f = q("SELECT f.*,i.name iname FROM fdrs f JOIN institutions i ON i.id=f.inst_id WHERE f.id=?", (r["fdr_id"],), one=True) if r else None
    return render_template("verify.html", r=r, f=f)

@app.route("/audit")
@login_required("admin", "officer")
def audit_view():
    rows = q("SELECT * FROM audit ORDER BY id"); prev = "GENESIS"; ok = True; bad = None
    for r in rows:
        h = hashlib.sha256(f"{prev}|{r['ts']}|{r['actor']}|{r['action']}|{r['detail']}".encode()).hexdigest()
        if r["prev"] != prev or r["hash"] != h: ok = False; bad = r["id"]; break
        prev = h
    return render_template("audit.html", rows=list(reversed(rows))[:300], ok=ok, bad=bad)

@app.route("/export.csv")
@login_required("admin", "officer")
def export():
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["case", "institution", "fdr_no", "bank", "amount", "issue", "maturity", "days_left", "status", "trust_level", "risk", "escalation", "flags"])
    for r in q("SELECT * FROM fdrs"):
        v = view(r); w.writerow([v["id"], v["inst"], v["fdr_no"], v["bank"], v["amount"], v["issue"], v["maturity"], v["dl"], v["label"], "L%d" % v["lvl"], v["risk"], v["esc"], "; ".join(m for _, m in v["flaglist"])])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=nidhisetu_fdrs.csv"})

from templates import T
app.jinja_loader = DictLoader(T)
app.jinja_env.filters["inr"] = lambda x: f"{x:,.0f}"
init()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
