# SQL Injection Scanner

A cybersecurity project that demonstrates SQL injection vulnerabilities using a deliberately vulnerable Flask web application and an automated scanner.

Built for **Foundations of Cybersecurity** — CSCI 6738 / CSCI 3410 / INFO 4410

---

## Overview

This project consists of two parts:

1. **A vulnerable web application** — A fake bank login site (SecureBank) built with Flask and SQLite that intentionally contains SQL injection vulnerabilities for demonstration purposes.
2. **An automated scanner** — A Python tool that fires common SQL injection payloads at the vulnerable app, detects successful attacks, rates their risk level, and generates an HTML report.

---

## Project Structure

```
sql_injection_project/
├── setup_db.py        # Creates the SQLite database with sample users
├── vulnerable_app.py  # Flask web app with intentional SQL injection flaws
├── scanner.py         # Automated SQL injection scanner
├── requirements.txt   # Python dependencies
```

---

## Requirements

- Python 3.x
- Flask
- requests
- colorama

Install all dependencies with:

```bash
pip install flask requests colorama
```

---

## How to Run

### Step 1 — Set up the database
```bash
python setup_db.py
```

### Step 2 — Start the vulnerable web app
```bash
python vulnerable_app.py
```
Open your browser and go to `http://127.0.0.1:5000` to see the SecureBank login page.

### Step 3 — Run the scanner (in a second terminal)
```bash
python scanner.py
```

The scanner will test 17 payloads across two endpoints (login form and user search page), print color-coded results explaining what each attack does, and save a full HTML report to `scan_report.html`.

---

## Vulnerable Endpoints

| Endpoint | Vulnerability |
|---|---|
| `/login` | Username field — unsanitized SQL query allows authentication bypass |
| `/search` | Search field — unsanitized SQL query allows data extraction |

---

## Example Payloads

| Payload | Type | Effect |
|---|---|---|
| `' OR '1'='1` | Authentication Bypass | Logs in without a password |
| `' OR 1=1 --` | Authentication Bypass | Bypasses login using SQL comment |
| `' UNION SELECT id,username,password,role FROM users --` | Data Extraction | Dumps all user credentials |
| `'; DROP TABLE users; --` | Destructive | Deletes the entire users table |

---

## Risk Ratings

| Level | Color | Description |
|---|---|---|
| CRITICAL | Red | Destructive attacks (data deletion) |
| HIGH | Yellow | Authentication bypass, data extraction |
| MEDIUM | Cyan | Blind injection techniques |
| LOW | White | Informational probes |

---

## Disclaimer

This project is for **educational purposes only**. The vulnerable application is intentionally insecure and should only be run locally. Never deploy it on a public server. Always obtain proper authorization before testing any system for vulnerabilities.

---

## How to Fix SQL Injection

The vulnerability exists because user input is inserted directly into SQL queries. The fix is to use **parameterized queries**:

```python
# Vulnerable (DO NOT USE)
query = f"SELECT * FROM users WHERE username = '{username}'"

# Secure (use this instead)
cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
```
