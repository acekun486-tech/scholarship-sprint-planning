import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'counselor'))
    );
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        published_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        eligibility TEXT NOT NULL,
        deadline TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES users(id),
        project_id INTEGER NOT NULL REFERENCES projects(id),
        full_name TEXT NOT NULL,
        student_no TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '待审批'
            CHECK(status IN ('待审批', '通过', '退回补充材料', '不通过')),
        review_comment TEXT,
        reviewed_by INTEGER REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_materials_application
        ON materials(application_id);
    """)

    try:
        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_applications_student_project
            ON applications(student_id, project_id)
        """)
    except sqlite3.IntegrityError:
        db.rollback()
        current_app.logger.warning(
            "Existing duplicate applications prevent the unique index; "
            "application submission still performs an explicit duplicate check."
        )

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            [
                ("student", generate_password_hash("student123"), "student"),
                ("counselor", generate_password_hash("counselor123"), "counselor"),
            ],
        )
        db.executemany(
            "INSERT INTO notices (title, content) VALUES (?, ?)",
            [
                ("2026年度奖学金申请通知", "请符合条件的学生在截止日期前提交申请及证明材料。"),
                ("助学金材料提交提醒", "请检查材料是否清晰、完整，并确保信息真实。"),
            ],
        )
        db.executemany(
            "INSERT INTO projects (title, description, eligibility, deadline) VALUES (?, ?, ?, ?)",
            [
                (
                    "优秀学生奖学金",
                    "面向学习表现和综合表现优秀的在校学生。",
                    "在校学生；具体条件以学校正式通知为准。",
                    "2026-11-15",
                ),
                (
                    "国家助学金（示例）",
                    "面向符合学校认定条件、需要资助的学生。",
                    "需按学校规定完成家庭经济困难认定。",
                    "2026-11-20",
                ),
            ],
        )
    else:
        _hash_legacy_passwords(db)

    db.commit()


def _hash_legacy_passwords(db):
    """Upgrade plaintext demo passwords created by earlier project versions."""
    rows = db.execute("SELECT id, password FROM users").fetchall()
    for row in rows:
        password = row["password"]
        if not password.startswith(("scrypt:", "pbkdf2:")):
            db.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (generate_password_hash(password), row["id"]),
            )


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
