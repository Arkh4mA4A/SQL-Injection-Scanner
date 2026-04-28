from flask import Flask, request, render_template_string, session, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "securebank_secret"

# ─── Shared CSS styles used across all pages ────────────────────────────────

BASE_STYLE = """
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f0f4f8;
    min-height: 100vh;
  }
  nav {
    background: #1a3c6e;
    padding: 14px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  nav .brand {
    color: #fff;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1px;
  }
  nav .brand span { color: #f0c040; }
  nav a {
    color: #cfd8e8;
    text-decoration: none;
    margin-left: 24px;
    font-size: 14px;
  }
  nav a:hover { color: #fff; }
  .container {
    max-width: 480px;
    margin: 70px auto;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    padding: 40px 44px;
  }
  .wide-container {
    max-width: 720px;
    margin: 50px auto;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    padding: 40px 44px;
  }
  h2 {
    color: #1a3c6e;
    margin-bottom: 6px;
    font-size: 22px;
  }
  .subtitle {
    color: #7a8fa6;
    font-size: 13px;
    margin-bottom: 28px;
  }
  label {
    display: block;
    font-size: 13px;
    color: #4a5568;
    margin-bottom: 5px;
    font-weight: 600;
  }
  input[type=text], input[type=password] {
    width: 100%;
    padding: 11px 14px;
    border: 1px solid #cbd5e0;
    border-radius: 6px;
    font-size: 14px;
    margin-bottom: 18px;
    outline: none;
    transition: border 0.2s;
  }
  input[type=text]:focus, input[type=password]:focus {
    border-color: #1a3c6e;
  }
  button[type=submit] {
    width: 100%;
    padding: 12px;
    background: #1a3c6e;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }
  button[type=submit]:hover { background: #254d8e; }
  .message {
    margin-top: 18px;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 14px;
  }
  .message.success { background: #ebf8f0; color: #276749; border-left: 4px solid #38a169; }
  .message.error   { background: #fff5f5; color: #9b2c2c; border-left: 4px solid #e53e3e; }
  .message.warning { background: #fffbeb; color: #7b4f12; border-left: 4px solid #d69e2e; }
  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 24px;
  }
  .card {
    background: #f7fafc;
    border-radius: 8px;
    padding: 20px 24px;
    border: 1px solid #e2e8f0;
  }
  .card h3 { color: #1a3c6e; font-size: 15px; margin-bottom: 8px; }
  .card p  { color: #718096; font-size: 13px; }
  .card .amount { font-size: 26px; font-weight: 700; color: #276749; margin: 6px 0; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; }
  th { background: #1a3c6e; color: #fff; padding: 10px 14px; text-align: left; font-size: 13px; }
  td { padding: 10px 14px; font-size: 13px; border-bottom: 1px solid #e2e8f0; color: #4a5568; }
  tr:hover td { background: #f7fafc; }
  .search-row { display: flex; gap: 10px; margin-bottom: 10px; }
  .search-row input { flex: 1; margin-bottom: 0; }
  .search-row button { width: auto; padding: 11px 22px; }
  .logout-btn {
    background: none;
    border: 1px solid #cfd8e8;
    color: #cfd8e8;
    padding: 6px 16px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 13px;
  }
  .logout-btn:hover { background: rgba(255,255,255,0.1); }
  footer {
    text-align: center;
    padding: 28px;
    color: #a0aec0;
    font-size: 12px;
  }
</style>
"""

# ─── Home / Login page ───────────────────────────────────────────────────────

LOGIN_PAGE = BASE_STYLE + """
<nav>
  <div class="brand">Secure<span>Bank</span></div>
  <div>
    <a href="/">Vulnerable Login</a>
    <a href="/secure">Secure Login</a>
  </div>
</nav>
<div class="container">
  <div style="display:inline-block;background:#fff5f5;color:#c53030;border:1px solid #feb2b2;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;margin-bottom:16px;">
    VULNERABLE MODE
  </div>
  <h2>Welcome Back</h2>
  <p class="subtitle">Sign in to access your SecureBank account</p>
  <form method="POST" action="/login">
    <label>Username</label>
    <input type="text" name="username" placeholder="Enter your username" autocomplete="off">
    <label>Password</label>
    <input type="password" name="password" placeholder="Enter your password">
    <button type="submit">Sign In</button>
  </form>
  {% if message %}
    <div class="message {{ msg_class }}">{{ message }}</div>
  {% endif %}
</div>
<footer>SecureBank &copy; 2026. All rights reserved.</footer>
"""

# ─── Dashboard page (shown after login) ─────────────────────────────────────

DASHBOARD_PAGE = BASE_STYLE + """
<nav>
  <div class="brand">Secure<span>Bank</span></div>
  <div>
    <a href="/search">User Search</a>
    <form method="POST" action="/logout" style="display:inline">
      <button class="logout-btn" type="submit">Sign Out</button>
    </form>
  </div>
</nav>
<div class="wide-container">
  <h2>Account Dashboard</h2>
  <p class="subtitle">Welcome, {{ username }} &mdash; {{ role }}</p>
  <div class="dashboard-grid">
    <div class="card">
      <h3>Checking Account</h3>
      <div class="amount">$4,821.50</div>
      <p>Available balance</p>
    </div>
    <div class="card">
      <h3>Savings Account</h3>
      <div class="amount">$12,340.00</div>
      <p>Available balance</p>
    </div>
    <div class="card">
      <h3>Recent Transactions</h3>
      <p>Last login: today</p>
    </div>
    <div class="card">
      <h3>Account Status</h3>
      <p style="color:#276749; font-weight:600;">Active</p>
    </div>
  </div>
</div>
<footer>SecureBank &copy; 2026. All rights reserved.</footer>
"""

# ─── User Search page (second vulnerable endpoint) ───────────────────────────

SEARCH_PAGE = BASE_STYLE + """
<nav>
  <div class="brand">Secure<span>Bank</span></div>
  <div>
    <a href="/dashboard">Dashboard</a>
    <form method="POST" action="/logout" style="display:inline">
      <button class="logout-btn" type="submit">Sign Out</button>
    </form>
  </div>
</nav>
<div class="wide-container">
  <h2>User Lookup</h2>
  <p class="subtitle">Search for a registered account by username</p>
  <form method="POST" action="/search">
    <div class="search-row">
      <input type="text" name="query" placeholder="Enter username to search..." autocomplete="off">
      <button type="submit">Search</button>
    </div>
  </form>
  {% if results is not none %}
    {% if error %}
      <div class="message warning">{{ error }}</div>
    {% elif results %}
      <table>
        <tr><th>ID</th><th>Username</th><th>Role</th></tr>
        {% for row in results %}
          <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[3] }}</td></tr>
        {% endfor %}
      </table>
    {% else %}
      <div class="message error">No users found matching that query.</div>
    {% endif %}
  {% endif %}
</div>
<footer>SecureBank &copy; 2026. All rights reserved.</footer>
"""

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # Redirect to dashboard if already logged in, otherwise show login
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template_string(LOGIN_PAGE, message=None, msg_class="")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # INTENTIONALLY VULNERABLE: user input injected directly into SQL query
    # A real application would use parameterized queries to prevent this
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchone()
    except Exception as e:
        conn.close()
        return render_template_string(LOGIN_PAGE,
            message=f"Database error: {e}", msg_class="warning")
    conn.close()

    if result:
        # Store the logged-in user in the session
        session["user"] = result[1]
        session["role"] = result[3]
        return redirect(url_for("dashboard"))

    return render_template_string(LOGIN_PAGE,
        message="Invalid username or password. Please try again.", msg_class="error")

@app.route("/dashboard")
def dashboard():
    # Protect the dashboard — redirect to login if not authenticated
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template_string(DASHBOARD_PAGE,
        username=session["user"], role=session["role"])

@app.route("/search", methods=["GET", "POST"])
def search():
    # Protect the search page
    if not session.get("user"):
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template_string(SEARCH_PAGE, results=None, error=None)

    query_input = request.form.get("query", "")

    # INTENTIONALLY VULNERABLE: unsanitized input used directly in SQL
    sql = f"SELECT * FROM users WHERE username = '{query_input}'"

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
    except Exception as e:
        conn.close()
        return render_template_string(SEARCH_PAGE, results=[], error=f"Database error: {e}")
    conn.close()

    return render_template_string(SEARCH_PAGE, results=rows, error=None)

@app.route("/logout", methods=["POST"])
def logout():
    # Clear the session and return to login page
    session.clear()
    return redirect(url_for("index"))

# ─── Secure login page (parameterized queries — injection-proof) ─────────────

SECURE_LOGIN_PAGE = BASE_STYLE + """
<nav>
  <div class="brand">Secure<span>Bank</span></div>
  <div>
    <a href="/">Vulnerable Login</a>
    <a href="/secure">Secure Login</a>
  </div>
</nav>
<div class="container">
  <div style="display:inline-block;background:#ebf8f0;color:#276749;border:1px solid #9ae6b4;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;margin-bottom:16px;">
    SECURE MODE
  </div>
  <h2>Welcome Back</h2>
  <p class="subtitle">This login is protected against SQL injection</p>
  <form method="POST" action="/secure">
    <label>Username</label>
    <input type="text" name="username" placeholder="Enter your username" autocomplete="off">
    <label>Password</label>
    <input type="password" name="password" placeholder="Enter your password">
    <button type="submit" style="background:#276749;">Sign In Securely</button>
  </form>
  {% if message %}
    <div class="message {{ msg_class }}">{{ message }}</div>
  {% endif %}
  <div style="margin-top:24px;padding:14px 16px;background:#f7fafc;border-radius:6px;border:1px solid #e2e8f0;">
    <p style="font-size:12px;color:#4a5568;font-weight:600;margin-bottom:6px;">How this login is protected:</p>
    <code style="font-size:11px;color:#2d3748;line-height:1.8;">
      cursor.execute(<br>
      &nbsp;&nbsp;"SELECT * FROM users WHERE username = ? AND password = ?",<br>
      &nbsp;&nbsp;(username, password)<br>
      )
    </code>
    <p style="font-size:11px;color:#718096;margin-top:8px;">
      The <strong>?</strong> placeholders tell the database to treat user input as plain text,
      never as part of the SQL command. Injection payloads are harmless here.
    </p>
  </div>
</div>
<footer>SecureBank &copy; 2026. All rights reserved.</footer>
"""

@app.route("/secure", methods=["GET", "POST"])
def secure_login():
    if request.method == "GET":
        return render_template_string(SECURE_LOGIN_PAGE, message=None, msg_class="")

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # SECURE: parameterized query — user input is never part of the SQL command
    # The database engine treats username and password as literal strings only
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        result = cursor.fetchone()
    except Exception as e:
        conn.close()
        return render_template_string(SECURE_LOGIN_PAGE,
            message=f"Database error: {e}", msg_class="warning")
    conn.close()

    if result:
        return render_template_string(SECURE_LOGIN_PAGE,
            message=f"Login successful! Welcome, {result[1]}.", msg_class="success")

    return render_template_string(SECURE_LOGIN_PAGE,
        message="Invalid username or password. Injection attempt blocked.", msg_class="error")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
