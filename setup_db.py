import sqlite3

# Connect to (or create) the local database file
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Create the users table if it does not already exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
""")

# Remove any existing rows so we start fresh each time
cursor.execute("DELETE FROM users")

# Insert sample user accounts with roles
cursor.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", [
    ("admin",   "admin123",   "Administrator"),
    ("alice",   "password1",  "Customer"),
    ("bob",     "letmein",    "Customer"),
    ("charlie", "charlie99",  "Customer"),
    ("manager", "manage2024", "Manager"),
])

conn.commit()
conn.close()

print("[+] Database setup complete. Sample users created.")
