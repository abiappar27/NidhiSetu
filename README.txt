NidhiSetu - AICTE Security Deposit / FDR Management Portal

OPTION 1 (easiest, nothing to install): double-click index.html
  Opens in Chrome, Edge or Firefox. All data is stored in your browser (localStorage) on this computer.
  Demo logins:  admin / admin123    officer / officer123    college / college123
  Institutions can register themselves on the login page.
  Note: because data lives in one browser, the bank confirmation link works in the same browser only.
  Use the server edition if several people or computers must share the data.

OPTION 2 (shared multi-user server): open the "server" folder
  1. Install Python 3.9+   2. pip install -r requirements.txt   3. python app.py   4. open http://localhost:5000

Features (both editions): roles, FDR submission with document upload and hash, discrepancy flags, trust ladder L0-L4,
bank confirmation link, risk-scored runway with escalation, renewal chain, release workflow with Ready/Blocked verdict,
release order with public verification, tamper-evident audit log, CSV export, issuer concentration.
Minimum amount / tenure are placeholder defaults (Rs 5,00,000 / 12 months): set them per the current AICTE handbook.
