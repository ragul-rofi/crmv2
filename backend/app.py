from flask import Flask, request, render_template, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import os
from db import get_db_connection

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Local temporary uploads folder
LOCAL_UPLOAD_FOLDER = "uploads"
os.makedirs(LOCAL_UPLOAD_FOLDER, exist_ok=True)

# Google Drive sync folder (must exist, automatically synced)
GOOGLE_DRIVE_SYNC_PATH = r"G:\My Drive\crmv2"
os.makedirs(GOOGLE_DRIVE_SYNC_PATH, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # 1️⃣ Save locally (optional)
            local_path = os.path.join(LOCAL_UPLOAD_FOLDER, filename)
            file.save(local_path)

            # 2️⃣ Save directly to Google Drive sync folder
            gdrive_path = os.path.join(GOOGLE_DRIVE_SYNC_PATH, filename)
            file.seek(0)  # reset file pointer
            file.save(gdrive_path)

            # 3️⃣ Insert into PostgreSQL
            cur.execute(
                "INSERT INTO files (filename, gdrive_id) VALUES (%s, %s)",
                (filename, gdrive_path)  # storing local synced path as gdrive_id
            )
            conn.commit()
            flash("File uploaded successfully")
        else:
            flash("Only PDF files are allowed")

    # Fetch uploaded files to display
    cur.execute("SELECT id, filename, uploaded_at FROM files ORDER BY uploaded_at DESC")
    files = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("dashboard.html", role=session.get("role"), files=files)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded files from Google Drive sync folder"""
    return send_from_directory(GOOGLE_DRIVE_SYNC_PATH, filename)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
