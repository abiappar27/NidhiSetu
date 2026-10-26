CSS = """*{box-sizing:border-box}body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f3f6fb;color:#1a1a1a}
nav{background:#004aad;color:#fff;padding:10px 24px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}nav a{color:#fff;text-decoration:none;font-weight:600}
nav .b{font-size:20px;margin-right:auto}main{max-width:1150px;margin:20px auto;padding:0 16px}
.card{background:#fff;border:1px solid #cfd8e6;border-radius:10px;padding:16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:7px 8px;border-bottom:1px solid #e3e8f0;text-align:left;vertical-align:top}th{background:#eaf2fb}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}.st{background:#fff;border:1px solid #cfd8e6;border-radius:10px;padding:12px;text-align:center}
.st b{display:block;font-size:26px;color:#004aad}input,select,textarea{width:100%;padding:8px;border:1px solid #b9c5d8;border-radius:6px;margin:4px 0 10px;font:inherit}
input[type=checkbox],input[type=radio]{width:auto}button,.btn{background:#004aad;color:#fff;border:0;border-radius:6px;padding:8px 14px;cursor:pointer;text-decoration:none;display:inline-block;font:inherit;font-weight:600}
.btn2{background:#e8751a}.btn3{background:#c0392b}.btn4{background:#1e8449}.tag{padding:2px 9px;border-radius:12px;color:#fff;font-size:12px;font-weight:700}
.High,.high{background:#c0392b}.Med,.medium{background:#e8751a}.Low{background:#1e8449}.msg{padding:10px;border-radius:6px;margin-bottom:12px}.ok{background:#dff3e4}.err{background:#fbdcd8}
.lad{display:flex;gap:6px}.lad div{flex:1;padding:10px;text-align:center;background:#dde5f0;border-radius:6px;font-size:13px}.lad .on{background:#1e8449;color:#fff;font-weight:700}
form.inline{display:inline}.small{font-size:12px;color:#555}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:800px){.two{grid-template-columns:1fr}}
code{background:#eef2f8;padding:2px 5px;border-radius:4px;word-break:break-all}"""

BASE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>NidhiSetu</title><style>""" + CSS + """</style></head><body>
<nav><span class=b>NidhiSetu <small style="font-weight:400">| AICTE Security Deposit / FDR Portal</small></span>
{% if session.u %}<a href="/dashboard">Dashboard</a>{% if session.role=='institution' %}<a href="/fdr/new">Submit FDR</a>{% else %}<a href="/releases">Releases</a><a href="/audit">Audit</a><a href="/export.csv">Export CSV</a>{% endif %}<span>{{session.name}} ({{session.role}})</span><a href="/logout">Logout</a>{% endif %}</nav>
<main>{% with m=get_flashed_messages(with_categories=true) %}{% for c,t in m %}<div class="msg {{c}}">{{t}}</div>{% endfor %}{% endwith %}{% block c %}{% endblock %}</main></body></html>"""

LOGIN = """{% extends 'base.html' %}{% block c %}<div class=card style="max-width:420px;margin:40px auto"><h2>Login</h2><form method=post>
Username<input name=username required autofocus>Password<input type=password name=password required><button>Login</button></form>
<p class=small>Institution? <a href="/register">Register here</a>.</p>
<p class=small>Demo accounts: admin/admin123, officer/officer123, college/college123. Change these before real use.</p></div>{% endblock %}"""

REGISTER = """{% extends 'base.html' %}{% block c %}<div class=card style="max-width:480px;margin:30px auto"><h2>Institution registration</h2><form method=post>
Institution name<input name=name required>AICTE ID<input name=aicte_id required>Username<input name=username required>Password<input type=password name=password minlength=6 required><button>Register</button></form></div>{% endblock %}"""

ROW = """<td>#{{r.id}}</td>{% if officer %}<td>{{r.inst}}</td>{% endif %}<td><a href="/fdr/{{r.id}}">{{r.fdr_no}}</a><br><span class=small>{{r.bank}}</span></td><td>{{r.amount|inr}}</td><td>{{r.maturity}}<br><span class=small>{{r.dl}} days</span></td><td>{{r.label}}</td><td>L{{r.lvl}}</td><td><span class="tag {{'High' if r.risk>=70 else ('Med' if r.risk>=40 else 'Low')}}">{{r.risk}}</span></td>"""

DASH_INST = """{% extends 'base.html' %}{% block c %}<h2>My FDRs</h2><a class=btn href="/fdr/new">+ Submit new FDR</a><div class=card style="margin-top:14px"><table>
<tr><th>Case</th><th>FDR</th><th>Amount (Rs)</th><th>Maturity</th><th>Status</th><th>Trust</th><th>Risk</th></tr>
{% for r in rows %}<tr>""" + ROW + """</tr>{% else %}<tr><td colspan=7>No FDRs yet.</td></tr>{% endfor %}</table></div>
{% for r in rows if r.flaglist and r.status!='released' %}<div class=card><b>{{r.fdr_no}}</b> needs attention:<ul>{% for s,m in r.flaglist %}<li>{{m}}</li>{% endfor %}</ul></div>{% endfor %}{% endblock %}"""

DASH_OFF = """{% extends 'base.html' %}{% block c %}<h2>Regulation Bureau Dashboard</h2><div class=grid>{% for k,v in stats.items() %}<div class=st><b>{{v}}</b>{{k}}</div>{% endfor %}<div class=st><b>{{rel}}</b>Release requests open</div></div>
<div class=card><h3>Runway: highest risk first</h3><table><tr><th>Case</th><th>Institution</th><th>FDR</th><th>Amount (Rs)</th><th>Maturity</th><th>Status</th><th>Trust</th><th>Risk</th><th>Escalated to</th></tr>
{% for r in runway %}{% set officer=true %}<tr>""" + ROW + """<td>{{r.esc}}</td></tr>{% else %}<tr><td colspan=9>Nothing pending.</td></tr>{% endfor %}</table></div>
<div class=card><h3>Issuer concentration (live FDRs by bank)</h3><table><tr><th>Bank</th><th>FDRs</th><th>Amount (Rs)</th></tr>{% for b,v in banks %}<tr><td>{{b}}</td><td>{{v[0]}}</td><td>{{v[1]|inr}}</td></tr>{% endfor %}</table></div>{% endblock %}"""

NEW = """{% extends 'base.html' %}{% block c %}<div class=card style="max-width:640px;margin:auto"><h2>{{'Submit renewal / replacement FDR' if parent else 'Submit FDR'}}</h2>
<form method=post enctype=multipart/form-data>FDR number<input name=fdr_no required>Issuing bank<input name=bank required>
Bank type<select name=bank_type><option>Scheduled commercial</option><option>Cooperative</option><option>Small finance</option><option>Other</option></select>
Amount (Rs)<input name=amount type=number step=0.01 required>Issue date<input name=issue type=date required>Maturity date<input name=maturity type=date required>
Approved seats supported by this FDR<input name=seats type=number min=0 value=0>Authorised signatory<input name=signatory>
<label><input type=checkbox name=lien> Lien is marked in favour of AICTE</label><br><br>FDR document (PDF/PNG/JPG, max 6 MB)<input type=file name=doc accept=".pdf,.png,.jpg,.jpeg"><button>Submit</button></form></div>{% endblock %}"""

DETAIL = """{% extends 'base.html' %}{% block c %}<h2>Case #{{f.id}}: {{f.fdr_no}}</h2><div class=two><div class=card><table>
<tr><th>Institution</th><td>{{f.inst}}</td></tr><tr><th>Bank</th><td>{{f.bank}} ({{f.bank_type}})</td></tr><tr><th>Amount</th><td>Rs {{f.amount|inr}}</td></tr>
<tr><th>Issue / Maturity</th><td>{{f.issue}} to {{f.maturity}} ({{f.dl}} days left)</td></tr><tr><th>Status</th><td>{{f.label}}</td></tr><tr><th>Seats supported</th><td>{{f.seats}}</td></tr>
<tr><th>Signatory</th><td>{{f.signatory or '-'}}</td></tr><tr><th>Lien to AICTE</th><td>{{'Declared' if f.lien else 'Not declared'}}</td></tr>
<tr><th>Risk / escalation</th><td><span class="tag {{'High' if f.risk>=70 else ('Med' if f.risk>=40 else 'Low')}}">{{f.risk}}</span> {{f.esc}}</td></tr>
<tr><th>Document</th><td>{% if f.doc %}<a href="/fdr/{{f.id}}/doc" target=_blank>View</a><br><span class=small>SHA-256 {{f.doc_hash[:20]}}...</span>{% else %}None{% endif %}</td></tr>
<tr><th>Bank confirmation</th><td>{{f.bank_conf_by or 'Not yet'}} {{f.bank_conf_at or ''}}</td></tr><tr><th>AICTE reconciliation</th><td>{{f.recon or 'Not yet'}}</td></tr></table></div>
<div class=card><h3>Provenance ladder</h3><div class=lad>{% for n,t in [(0,'Claimed'),(1,'Document matched'),(2,'Scrutiny passed'),(3,'Bank confirmed'),(4,'AICTE reconciled')] %}<div class="{{'on' if f.lvl>=n}}">L{{n}}<br>{{t}}</div>{% endfor %}</div>
<h3>Flags</h3>{% for s,m in f.flaglist %}<p><span class="tag {{s}}">{{s}}</span> {{m}}</p>{% else %}<p>No flags raised.</p>{% endfor %}
<h3>History</h3>{% for c in chain %}<p class=small>Earlier: <a href="/fdr/{{c.id}}">{{c.fdr_no}}</a> (matured {{c.maturity}}, {{c.status}})</p>{% endfor %}{% for c in kids %}<p class=small>Renewal: <a href="/fdr/{{c.id}}">{{c.fdr_no}}</a> ({{c.status}})</p>{% endfor %}</div></div>
{% if session.role!='institution' %}<div class=card><h3>Officer actions</h3>
{% if link %}<div class="msg ok">Send this one-time link to the bank officer:<br><code>{{link}}</code></div>{% endif %}
{% for a,t,c in [('doc_ok','Mark document checked','btn'),('scrutiny','Pass scrutiny','btn'),('bank_link','Create bank confirmation link','btn2'),('verify','Mark verified','btn4'),('reject','Reject','btn3')] %}<form class=inline method=post action="/fdr/{{f.id}}/act"><input type=hidden name=action value={{a}}><button class="{{c}}">{{t}}</button></form> {% endfor %}
<form method=post action="/fdr/{{f.id}}/act" style="margin-top:12px"><input type=hidden name=action value=recon>AICTE receipt / lien reference<input name=ref><button>Reconcile (L4)</button></form>
<form method=post action="/fdr/{{f.id}}/act"><input type=hidden name=action value=remark>Scrutiny remark<textarea name=text rows=2></textarea><button>Add remark</button></form></div>
{% elif f.status not in ('released','rejected') %}<div class=card><a class=btn href="/fdr/new?parent={{f.id}}">Submit renewal / replacement</a>
<h3 style="margin-top:16px">Request release / refund</h3><form method=post action="/fdr/{{f.id}}/release">Reason<textarea name=reason required rows=2></textarea><label><input type=checkbox name=cycle> Approval cycle is closed or a replacement FDR is in place</label><br><br><button>Request release</button></form></div>{% endif %}
<div class=card><h3>Release readiness: {{'READY' if ready else 'BLOCKED'}}</h3>{% for r in reasons %}<p>- {{r}}</p>{% endfor %}
{% for r in rels %}<p>Request #{{r.id}} ({{r.created}}): <b>{{r.status}}</b> {% if r.status=='approved' %}<a href="/order/{{r.id}}">Release order</a>{% endif %}</p>{% endfor %}</div>
<div class=card><h3>Remarks</h3>{% for m in remarks %}<p><b>{{m.user}}</b> <span class=small>{{m.ts}}</span><br>{{m.text}}</p>{% else %}<p>None.</p>{% endfor %}</div>{% endblock %}"""

BANK = """{% extends 'base.html' %}{% block c %}<div class=card style="max-width:560px;margin:30px auto"><h2>Bank FDR confirmation</h2>
{% if msg %}<p>{{msg}}</p>{% else %}<p>Please confirm whether this FDR exists and is lien-marked in favour of AICTE.</p><table><tr><th>FDR number</th><td>{{f.fdr_no}}</td></tr><tr><th>Bank</th><td>{{f.bank}}</td></tr><tr><th>Amount</th><td>Rs {{f.amount|inr}}</td></tr><tr><th>Issue / Maturity</th><td>{{f.issue}} / {{f.maturity}}</td></tr></table>
<form method=post>Your name<input name=name required>Designation / branch<input name=designation required>
<label><input type=radio name=decision value=confirm checked> Confirm: details are correct and lien is marked</label><br><label><input type=radio name=decision value=dispute> Dispute</label>
Reason (if disputing)<textarea name=reason></textarea><button>Submit</button></form>{% endif %}</div>{% endblock %}"""

RELS = """{% extends 'base.html' %}{% block c %}<h2>Release / refund requests</h2>{% for r,f,ok,reasons in rows %}<div class=card><b>Request #{{r.id}}</b> for <a href="/fdr/{{f.id}}">{{f.fdr_no}}</a> ({{f.inst}}) - <b>{{r.status}}</b><br>Reason: {{r.reason}}<br>
Readiness: <b>{{'READY' if ok else 'BLOCKED'}}</b>{% for x in reasons %}<br>- {{x}}{% endfor %}<br><br>
{% if r.status=='requested' %}<form class=inline method=post action="/release/{{r.id}}"><input type=hidden name=action value=recommend><button>Recommend</button></form>{% endif %}
{% if r.status=='recommended' and session.role=='admin' %}<form class=inline method=post action="/release/{{r.id}}"><input type=hidden name=action value=approve><button class=btn4>Approve and issue order</button></form>{% endif %}
{% if r.status in ('requested','recommended') %}<form class=inline method=post action="/release/{{r.id}}"><input type=hidden name=action value=reject><button class=btn3>Reject</button></form>{% endif %}
{% if r.status=='approved' %}<a class=btn href="/order/{{r.id}}">Release order</a>{% endif %}</div>{% else %}<p>No requests.</p>{% endfor %}{% endblock %}"""

ORDER = """{% extends 'base.html' %}{% block c %}<div class=card style="max-width:700px;margin:auto"><h2>Release Order</h2><p>Order code: <b>{{r.code}}</b></p><p>FDR <b>{{f.fdr_no}}</b> ({{f.bank}}, Rs {{f.amount|inr}}) of <b>{{f.inst}}</b> is approved for release / discharge of AICTE lien.</p>
<p>Banks and third parties can verify this order at: <code>{{url}}</code></p><button onclick="window.print()">Print</button></div>{% endblock %}"""

VERIFY = """{% extends 'base.html' %}{% block c %}<div class=card style="max-width:560px;margin:30px auto"><h2>Release order verification</h2>{% if r %}<p class=ok style="padding:10px">VALID release order {{r.code}}</p>
<p>FDR {{f.fdr_no}} ({{f.bank}}, Rs {{f.amount|inr}}) of {{f.iname}} was approved for release.</p>{% else %}<p class=err style="padding:10px">NOT FOUND: this code does not match any approved release order.</p>{% endif %}</div>{% endblock %}"""

AUDIT = """{% extends 'base.html' %}{% block c %}<h2>Tamper-evident audit trail</h2><div class="msg {{'ok' if ok else 'err'}}">{{'Hash chain verified: no record has been altered.' if ok else 'CHAIN BROKEN at entry #%s: records were altered.'%bad}}</div><div class=card><table><tr><th>#</th><th>Time</th><th>Actor</th><th>Action</th><th>Detail</th><th>Hash</th></tr>
{% for r in rows %}<tr><td>{{r.id}}</td><td>{{r.ts}}</td><td>{{r.actor}}</td><td>{{r.action}}</td><td>{{r.detail}}</td><td class=small>{{r.hash[:12]}}</td></tr>{% endfor %}</table></div>{% endblock %}"""

T = {"base.html": BASE, "login.html": LOGIN, "register.html": REGISTER, "dash_inst.html": DASH_INST, "dash_officer.html": DASH_OFF,
     "fdr_new.html": NEW, "fdr_detail.html": DETAIL, "bank.html": BANK, "releases.html": RELS, "order.html": ORDER, "verify.html": VERIFY, "audit.html": AUDIT}
