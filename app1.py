import os
import sqlite3

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-local-key")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "skillpath.db")

SKILLS = {
    "Beginner": [
        "Installation and Environment Setup",
        "Variables and Data Types",
        "Operators and Expressions",
        "Conditional Statements",
        "Loops",
        "Functions",
        "Lists, Tuples, Sets and Dictionaries",
        "File Handling",
        "Exception Handling",
        "Build a Mini Project",
    ],
    "Intermediate": [
        "Object-Oriented Programming",
        "Modules and Packages",
        "File Handling and Exceptions",
        "Working with APIs",
        "Database Integration",
        "Testing and Debugging",
        "Git and GitHub",
        "Build a Practical Project",
    ],
    "Advanced": [
        "Advanced Programming Concepts",
        "Design Patterns",
        "Performance Optimization",
        "Security Best Practices",
        "Automated Testing",
        "Deployment",
        "Build a Professional Project",
        "Create a Portfolio",
    ],
}

PROJECT_IDEAS = {
    "python": ["Expense Tracker", "Weather Dashboard", "File Organizer"],
    "web development": [
        "Personal Portfolio Website",
        "Student Management System",
        "Online Learning Platform",
    ],
    "java": [
        "Library Management System",
        "Student Management System",
        "Banking Simulation",
    ],
    "cyber security": [
        "Password Strength Checker",
        "Secure Login System",
        "File Integrity Checker",
    ],
    "c programming": [
        "Calculator",
        "Student Record System",
        "Contact Management System",
    ],
}

LEARNING_RESOURCES = {
    "python": [
        {"name": "Python Tutorial", "url": "https://docs.python.org/3/tutorial/"},
        {"name": "W3Schools Python", "url": "https://www.w3schools.com/python/"},
    ],
    "web development": [
        {"name": "MDN Web Docs", "url": "https://developer.mozilla.org/"},
        {"name": "W3Schools", "url": "https://www.w3schools.com/"},
    ],
    "java": [
        {"name": "Java Learning", "url": "https://dev.java/learn/"},
        {"name": "W3Schools Java", "url": "https://www.w3schools.com/java/"},
    ],
    "cyber security": [
        {"name": "OWASP", "url": "https://owasp.org/"},
        {
            "name": "Cisco Cybersecurity",
            "url": "https://www.cisco.com/site/us/en/learn/topics/security/what-is-cybersecurity.html",
        },
    ],
    "c programming": [
        {"name": "Programiz C", "url": "https://www.programiz.com/c-programming"},
        {"name": "W3Schools C", "url": "https://www.w3schools.com/c/"},
    ],
}


def init_db():
    """Create the learning-path table without deleting existing records."""
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                level TEXT NOT NULL,
                completed TEXT DEFAULT ''
            )
        """)

        # Add the progress column to older databases if it is missing.
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(learning_paths)")
        }
        if "completed" not in columns:
            conn.execute(
                "ALTER TABLE learning_paths ADD COLUMN completed TEXT DEFAULT ''"
            )


def get_projects(goal):
    key = goal.lower().strip()
    return PROJECT_IDEAS.get(
        key,
        [
            f"{goal.title()} Beginner Project",
            f"{goal.title()} Practice Application",
            f"{goal.title()} Portfolio Project",
        ],
    )


def get_topics(level):
    return SKILLS.get(level, SKILLS["Beginner"])


def get_completed(path):
    raw = path["completed"] or ""
    topic_count = len(get_topics(path["level"]))
    return {
        value for value in raw.split(",")
        if value.isdigit() and 0 <= int(value) < topic_count
    }


def get_resources(goal):
    return LEARNING_RESOURCES.get(goal.lower().strip(), [])


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        paths = conn.execute(
            "SELECT * FROM learning_paths ORDER BY id DESC"
        ).fetchall()

    total_topics = 0
    completed_topics = 0

    for path in paths:
        total_topics += len(get_topics(path["level"]))
        completed_topics += len(get_completed(path))

    percentage = (
        round(completed_topics * 100 / total_topics)
        if total_topics else 0
    )

    return render_template(
        "dashboard.html",
        paths=paths,
        total_paths=len(paths),
        total_topics=total_topics,
        completed_topics=completed_topics,
        percentage=percentage,
    )


@app.route("/generate", methods=["POST"])
def generate():
    goal = request.form.get("goal", "").strip()
    level = request.form.get("level", "Beginner")

    if not goal:
        flash("Please enter a learning goal.", "error")
        return redirect(url_for("home"))

    if level not in SKILLS:
        level = "Beginner"

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "INSERT INTO learning_paths (goal, level) VALUES (?, ?)",
            (goal, level),
        )
        path_id = cursor.lastrowid

    flash("Your learning path has been created.", "success")
    return redirect(url_for("view_path", path_id=path_id))


@app.route("/path/<int:path_id>")
def view_path(path_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        path = conn.execute(
            "SELECT * FROM learning_paths WHERE id = ?", (path_id,)
        ).fetchone()

    if path is None:
        abort(404)

    topics = get_topics(path["level"])
    completed = get_completed(path)
    progress = round(len(completed) * 100 / len(topics)) if topics else 0

    return render_template(
        "path.html",
        path=path,
        topics=topics,
        completed=completed,
        progress=progress,
        projects=get_projects(path["goal"]),
        resources=get_resources(path["goal"]),
    )


@app.route("/save-progress/<int:path_id>", methods=["POST"])
def save_progress(path_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        path = conn.execute(
            "SELECT * FROM learning_paths WHERE id = ?", (path_id,)
        ).fetchone()

        if path is None:
            abort(404)

        topic_count = len(get_topics(path["level"]))
        valid = set()

        for value in request.form.getlist("completed"):
            if value.isdigit() and 0 <= int(value) < topic_count:
                valid.add(value)

        saved = ",".join(sorted(valid, key=int))
        conn.execute(
            "UPDATE learning_paths SET completed = ? WHERE id = ?",
            (saved, path_id),
        )

    flash("Your progress has been saved.", "success")
    return redirect(url_for("view_path", path_id=path_id))


@app.route("/my-paths")
def my_paths():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        paths = conn.execute(
            "SELECT * FROM learning_paths ORDER BY id DESC"
        ).fetchall()

    path_items = []
    for path in paths:
        topics = get_topics(path["level"])
        completed = get_completed(path)
        progress = round(len(completed) * 100 / len(topics)) if topics else 0
        path_items.append({
            "path": path,
            "progress": progress,
            "completed_count": len(completed),
            "topic_count": len(topics),
        })

    return render_template("my_paths.html", path_items=path_items)


@app.route("/delete-path/<int:path_id>", methods=["POST"])
def delete_path(path_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "DELETE FROM learning_paths WHERE id = ?", (path_id,)
        )

    if cursor.rowcount == 0:
        abort(404)

    flash("Learning path deleted.", "success")
    return redirect(url_for("my_paths"))


@app.route("/recommendations")
def recommendations():
    return render_template(
        "recommendations.html",
        resources=LEARNING_RESOURCES,
        projects=PROJECT_IDEAS,
    )


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)