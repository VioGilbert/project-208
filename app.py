from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "library_athena"

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- READ ---
@app.route("/")
def home():
    return render_template("index.html")

# --- CREATE (User) ---
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form["role"]
        firstname = request.form["firstname"]
        surname = request.form["surname"]
        dob = request.form["dob"]
        phone = request.form["phone"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (role, firstname, surname, dob, phone, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (role, firstname, surname, dob, phone, password))
        conn.commit()
        conn.close()
        flash("Account created successfully!")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        user_id = request.form["user_id"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ? AND role = ? AND password = ?",
            (user_id, role, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid login details")
            return redirect(url_for("login"))

    return render_template("login.html")

# --- READ (Stats) ---
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    total_patrons = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'patron'").fetchone()[0]
    total_admins = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
    
    # Fetch current user info to display on dashboard
    user_info = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()

    return render_template(
        "dashboard.html",
        total_patrons=total_patrons,
        total_admins=total_admins,
        user=user_info
    )

# --- CREATE (Attendance) ---
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if "user_id" not in session:
        return redirect(url_for("login"))

    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    conn = get_db_connection()

    if request.method == "POST":
        existing = conn.execute(
            "SELECT * FROM attendance WHERE user_id = ? AND date = ?",
            (session["user_id"], today)
        ).fetchone()

        if existing:
            flash("Attendance already recorded today.")
        else:
            conn.execute(
                "INSERT INTO attendance (user_id, date, time) VALUES (?, ?, ?)",
                (session["user_id"], today, now_time)
            )
            conn.commit()
            flash("Attendance recorded successfully.")

    conn.close()
    return render_template("attendance.html")

# --- READ (Profile) ---
@app.route("/profile")
def view_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    if not user:
        flash("User profile not found.")
        return redirect(url_for("dashboard"))

    return render_template("profile.html", user=user)

# --- UPDATE ---
@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    
    if request.method == "POST":
        new_phone = request.form["phone"]
        
        conn.execute(
            "UPDATE users SET phone = ? WHERE id = ?",
            (new_phone, session["user_id"])
        )
        conn.commit()
        conn.close()
        flash("Profile updated successfully!")
        return redirect(url_for("dashboard"))

    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("edit_profile.html", user=user)

# --- DELETE ---
@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()
    
    # Delete user's attendance records first (Foreign Key constraint safety)
    conn.execute("DELETE FROM attendance WHERE user_id = ?", (user_id,))
    # Delete the user
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    
    session.clear()
    flash("Account deleted successfully.")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)