from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from functools import wraps
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "department.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")

ROLES = ("student", "faculty", "hod", "admin")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student','faculty','hod','admin')),
            program TEXT DEFAULT 'UG',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            program TEXT NOT NULL,
            submitted_by INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'Pending Faculty Review',
            faculty_id INTEGER REFERENCES users(id),
            hod_comment TEXT DEFAULT '',
            faculty_comment TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            program TEXT NOT NULL,
            supervisor_id INTEGER NOT NULL REFERENCES users(id),
            seats INTEGER NOT NULL DEFAULT 1,
            allocated_to INTEGER REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER REFERENCES users(id),
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            seed = [
                ("System Administrator","admin@dept.local","Admin123!","admin","UG"),
                ("Head of Department","hod@dept.local","Hod123!","hod","UG"),
                ("Faculty Member","faculty@dept.local","Faculty123!","faculty","UG"),
                ("Demo Student","student@dept.local","Student123!","student","UG"),
                ("PG Student","pgstudent@dept.local","Student123!","student","PG"),
            ]
            for name,email,password,role,program in seed:
                con.execute("INSERT INTO users(name,email,password_hash,role,program,created_at) VALUES(?,?,?,?,?,?)",
                            (name,email,generate_password_hash(password),role,program,now))
            faculty = con.execute("SELECT id FROM users WHERE role='faculty' LIMIT 1").fetchone()["id"]
            con.execute("INSERT INTO projects(title,description,program,supervisor_id,seats,status,created_at) VALUES(?,?,?,?,?,?,?)",
                        ("AI-Assisted Department Helpdesk","Build a searchable helpdesk with workflow tracking.","UG",faculty,2,"Open",now))
            con.execute("INSERT INTO projects(title,description,program,supervisor_id,seats,status,created_at) VALUES(?,?,?,?,?,?,?)",
                        ("Research Data Dashboard","Create a dashboard for research and academic activity data.","PG",faculty,1,"Open",now))

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to perform that action.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

def log_action(con, entity_type, entity_id, action, note=""):
    con.execute("INSERT INTO activity_log(actor_id,entity_type,entity_id,action,note,created_at) VALUES(?,?,?,?,?,?)",
                (session.get("user_id"), entity_type, entity_id, action, note, datetime.now().isoformat(timespec="seconds")))

@app.context_processor
def inject_user():
    return {"current_user": get_current_user(), "now": datetime.now}

def get_current_user():
    if session.get("user_id"):
        with db() as con:
            return con.execute("SELECT id,name,email,role,program FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return None

@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"], session["name"], session["role"] = user["id"], user["name"], user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    role = session["role"]
    with db() as con:
        if role == "student":
            requests_rows = con.execute("""SELECT r.*,u.name AS submitter FROM requests r JOIN users u ON u.id=r.submitted_by
                WHERE r.submitted_by=? ORDER BY r.created_at DESC""", (session["user_id"],)).fetchall()
            projects = con.execute("""SELECT p.*,u.name AS supervisor FROM projects p JOIN users u ON u.id=p.supervisor_id
                WHERE p.status='Open' AND p.program=(SELECT program FROM users WHERE id=?) ORDER BY p.id DESC""",
                (session["user_id"],)).fetchall()
        else:
            requests_rows = con.execute("""SELECT r.*,u.name AS submitter FROM requests r JOIN users u ON u.id=r.submitted_by
                ORDER BY r.created_at DESC LIMIT 12""").fetchall()
            projects = con.execute("""SELECT p.*,u.name AS supervisor, s.name AS student_name FROM projects p
                JOIN users u ON u.id=p.supervisor_id LEFT JOIN users s ON s.id=p.allocated_to ORDER BY p.id DESC""").fetchall()
        stats = {
            "requests": con.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
            "pending": con.execute("SELECT COUNT(*) FROM requests WHERE status NOT IN ('Approved','Rejected')").fetchone()[0],
            "projects": con.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "users": con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        }
    return render_template("dashboard.html", requests_rows=requests_rows, projects=projects, stats=stats)

@app.route("/requests")
@login_required
def requests_list():
    with db() as con:
        if session["role"] == "student":
            rows = con.execute("SELECT r.*,u.name AS submitter FROM requests r JOIN users u ON u.id=r.submitted_by WHERE submitted_by=? ORDER BY created_at DESC",
                               (session["user_id"],)).fetchall()
        else:
            rows = con.execute("SELECT r.*,u.name AS submitter FROM requests r JOIN users u ON u.id=r.submitted_by ORDER BY created_at DESC").fetchall()
    return render_template("requests.html", rows=rows)

@app.route("/requests/new", methods=["GET","POST"])
@roles_required("student","faculty")
def new_request():
    if request.method == "POST":
        title = request.form.get("title","").strip()
        category = request.form.get("category","").strip()
        description = request.form.get("description","").strip()
        program = request.form.get("program","UG")
        if not title or not category or not description or program not in ("UG","PG"):
            flash("Please complete all fields.", "error")
            return render_template("request_form.html")
        now = datetime.now().isoformat(timespec="seconds")
        with db() as con:
            cur = con.execute("""INSERT INTO requests(title,category,description,program,submitted_by,status,created_at,updated_at)
                VALUES(?,?,?,?,?,'Pending Faculty Review',?,?)""",
                (title,category,description,program,session["user_id"],now,now))
            log_action(con,"request",cur.lastrowid,"Submitted","Request submitted for faculty review")
        flash("Request submitted to the faculty review queue.", "success")
        return redirect(url_for("requests_list"))
    return render_template("request_form.html")

@app.route("/requests/<int:req_id>")
@login_required
def request_detail(req_id):
    with db() as con:
        row = con.execute("""SELECT r.*,u.name AS submitter,f.name AS faculty_name FROM requests r
            JOIN users u ON u.id=r.submitted_by LEFT JOIN users f ON f.id=r.faculty_id WHERE r.id=?""", (req_id,)).fetchone()
        logs = con.execute("SELECT a.*,u.name AS actor FROM activity_log a LEFT JOIN users u ON u.id=a.actor_id WHERE entity_type='request' AND entity_id=? ORDER BY a.id DESC", (req_id,)).fetchall()
    if not row:
        flash("Request not found.", "error")
        return redirect(url_for("requests_list"))
    if session["role"] == "student" and row["submitted_by"] != session["user_id"]:
        flash("You can only view your own requests.", "error")
        return redirect(url_for("requests_list"))
    return render_template("request_detail.html", row=row, logs=logs)

@app.route("/requests/<int:req_id>/review", methods=["POST"])
@roles_required("faculty","hod","admin")
def review_request(req_id):
    action = request.form.get("action")
    comment = request.form.get("comment","").strip()
    now = datetime.now().isoformat(timespec="seconds")
    with db() as con:
        row = con.execute("SELECT * FROM requests WHERE id=?", (req_id,)).fetchone()
        if not row:
            flash("Request not found.", "error")
            return redirect(url_for("requests_list"))
        if session["role"] == "faculty":
            if row["status"] not in ("Pending Faculty Review","Faculty Changes Requested"):
                flash("This request is not awaiting faculty review.", "error")
                return redirect(url_for("request_detail", req_id=req_id))
            mapping = {"forward":"Pending HOD Approval", "changes":"Faculty Changes Requested", "reject":"Rejected"}
            if action not in mapping:
                flash("Invalid review action.", "error")
                return redirect(url_for("request_detail", req_id=req_id))
            status = mapping[action]
            con.execute("UPDATE requests SET status=?,faculty_id=?,faculty_comment=?,updated_at=? WHERE id=?",
                        (status,session["user_id"],comment,now,req_id))
        else:
            if row["status"] != "Pending HOD Approval":
                flash("Only requests awaiting HOD approval can be decided here.", "error")
                return redirect(url_for("request_detail", req_id=req_id))
            mapping = {"approve":"Approved", "changes":"HOD Changes Requested", "reject":"Rejected"}
            if action not in mapping:
                flash("Invalid approval action.", "error")
                return redirect(url_for("request_detail", req_id=req_id))
            status = mapping[action]
            con.execute("UPDATE requests SET status=?,hod_comment=?,updated_at=? WHERE id=?",(status,comment,now,req_id))
        log_action(con,"request",req_id,status,comment)
    flash(f"Request updated: {status}.", "success")
    return redirect(url_for("request_detail", req_id=req_id))

@app.route("/projects")
@login_required
def projects_list():
    with db() as con:
        rows = con.execute("""SELECT p.*,u.name AS supervisor,s.name AS student_name FROM projects p
            JOIN users u ON u.id=p.supervisor_id LEFT JOIN users s ON s.id=p.allocated_to ORDER BY p.created_at DESC""").fetchall()
    return render_template("projects.html", rows=rows)

@app.route("/projects/new", methods=["GET","POST"])
@roles_required("faculty","hod","admin")
def new_project():
    if request.method == "POST":
        title=request.form.get("title","").strip()
        description=request.form.get("description","").strip()
        program=request.form.get("program","UG")
        try: seats=max(1,min(50,int(request.form.get("seats","1"))))
        except ValueError: seats=1
        if not title or not description or program not in ("UG","PG"):
            flash("Please complete all fields.", "error")
            return render_template("project_form.html")
        now=datetime.now().isoformat(timespec="seconds")
        with db() as con:
            cur=con.execute("INSERT INTO projects(title,description,program,supervisor_id,seats,status,created_at) VALUES(?,?,?,?,?,'Open',?)",
                            (title,description,program,session["user_id"],seats,now))
            log_action(con,"project",cur.lastrowid,"Created",title)
        flash("Project published.", "success")
        return redirect(url_for("projects_list"))
    return render_template("project_form.html")

@app.route("/projects/<int:project_id>/apply", methods=["POST"])
@roles_required("student")
def apply_project(project_id):
    with db() as con:
        project=con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        user=con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if not project or project["status"] != "Open":
            flash("This project is not open for allocation.", "error")
        elif project["program"] != user["program"]:
            flash("This project is for a different academic programme.", "error")
        elif project["allocated_to"] is not None:
            flash("This project has already been allocated.", "error")
        else:
            con.execute("UPDATE projects SET allocated_to=?,status='Allocated' WHERE id=?", (session["user_id"],project_id))
            log_action(con,"project",project_id,"Allocated",f"Allocated to {user['name']}")
            flash("Project allocated to your account.", "success")
    return redirect(url_for("projects_list"))

@app.route("/users", methods=["GET","POST"])
@roles_required("admin","hod")
def users_list():
    if request.method == "POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        role=request.form.get("role","student")
        program=request.form.get("program","UG")
        if not name or not email or len(password)<8 or role not in ROLES or program not in ("UG","PG"):
            flash("Enter valid details. Password must contain at least 8 characters.", "error")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password_hash,role,program,created_at) VALUES(?,?,?,?,?,?)",
                                (name,email,generate_password_hash(password),role,program,datetime.now().isoformat(timespec="seconds")))
                flash("User created successfully.", "success")
            except sqlite3.IntegrityError:
                flash("That email address is already registered.", "error")
        return redirect(url_for("users_list"))
    with db() as con:
        rows=con.execute("SELECT id,name,email,role,program,created_at FROM users ORDER BY role,name").fetchall()
    return render_template("users.html", rows=rows)

@app.route("/workflow")
@login_required
def workflow():
    return render_template("workflow.html")

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", message="The page you requested could not be found."),404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
