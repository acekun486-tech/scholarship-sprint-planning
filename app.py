from __future__ import annotations

import os
import re
import secrets
import sqlite3
import uuid
from datetime import date
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import check_password_hash

from database import close_db, get_db, init_db

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
FILE_SIGNATURES = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + (512 * 1024)
UPLOADABLE_STATUSES = {"待审批", "退回补充材料"}
REVIEW_DECISIONS = ("通过", "退回补充材料", "不通过")

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=str(BASE_DIR / "scholarship.db"),
        UPLOAD_FOLDER=str(BASE_DIR / "uploads"),
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    csrf.init_app(app)
    app.teardown_appcontext(close_db)
    _register_routes(app)

    with app.app_context():
        init_db()

    return app


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("请先登录。", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_original_name(filename):
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:180] or "未命名材料"


def file_matches_extension(extension, content):
    return content.startswith(FILE_SIGNATURES[extension])


def project_is_open(project):
    try:
        return date.fromisoformat(project["deadline"]) >= date.today()
    except (TypeError, ValueError):
        return False


def validate_application_form(full_name, student_no, reason):
    if not full_name or not student_no or not reason:
        return "姓名、学号和申请理由均为必填项。"
    if len(full_name) > 80:
        return "姓名不能超过 80 个字符。"
    if len(student_no) > 40 or any(char.isspace() for char in student_no):
        return "学号不能包含空格，且不能超过 40 个字符。"
    if len(reason) > 2000:
        return "申请理由不能超过 2000 个字符。"
    return None


def materials_by_application(db, application_ids):
    if not application_ids:
        return {}
    placeholders = ",".join("?" for _ in application_ids)
    rows = db.execute(
        f"""
        SELECT id, application_id, original_name, uploaded_at
        FROM materials
        WHERE application_id IN ({placeholders})
        ORDER BY id DESC
        """,
        tuple(application_ids),
    ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["application_id"], []).append(row)
    return grouped


def _register_routes(app):
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            if user and check_password_hash(user["password"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                flash(f"登录成功，当前角色：{user['role']}。", "success")
                return redirect(url_for("dashboard"))
            flash("用户名或密码不正确。", "danger")
        return render_template("login.html")

    @app.post("/logout")
    @login_required()
    def logout():
        session.clear()
        flash("已退出登录。", "info")
        return redirect(url_for("index"))

    @app.get("/dashboard")
    @login_required()
    def dashboard():
        db = get_db()
        if session["role"] == "counselor":
            applications = db.execute("""
                SELECT a.*, u.username, p.title AS project_title
                FROM applications a
                JOIN users u ON u.id = a.student_id
                JOIN projects p ON p.id = a.project_id
                ORDER BY a.created_at DESC
            """).fetchall()
        else:
            applications = db.execute("""
                SELECT a.*, p.title AS project_title
                FROM applications a JOIN projects p ON p.id = a.project_id
                WHERE a.student_id = ?
                ORDER BY a.created_at DESC
            """, (session["user_id"],)).fetchall()
        materials = materials_by_application(
            db, [application["id"] for application in applications]
        )
        return render_template(
            "dashboard.html", applications=applications, materials=materials
        )

    @app.get("/notices")
    def notices():
        rows = get_db().execute("SELECT * FROM notices ORDER BY id DESC").fetchall()
        return render_template("notices.html", notices=rows)

    @app.get("/projects")
    def projects():
        query = request.args.get("q", "").strip()
        db = get_db()
        if query:
            pattern = f"%{query}%"
            rows = db.execute(
                """
                SELECT * FROM projects
                WHERE title LIKE ? OR description LIKE ? OR eligibility LIKE ?
                ORDER BY id
                """,
                (pattern, pattern, pattern),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM projects ORDER BY id").fetchall()
        return render_template(
            "projects.html",
            projects=rows,
            query=query,
            project_is_open=project_is_open,
        )

    @app.get("/projects/<int:project_id>")
    def project_detail(project_id):
        project = get_db().execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not project:
            abort(404)
        return render_template(
            "project_detail.html",
            project=project,
            is_open=project_is_open(project),
        )

    @app.route("/apply/<int:project_id>", methods=["GET", "POST"])
    @login_required("student")
    def apply(project_id):
        db = get_db()
        project = db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not project:
            abort(404)
        if not project_is_open(project):
            flash("该项目已截止申请。", "warning")
            return redirect(url_for("projects"))

        existing = db.execute(
            """
            SELECT id, status FROM applications
            WHERE student_id = ? AND project_id = ?
            """,
            (session["user_id"], project_id),
        ).fetchone()
        if existing:
            flash(
                f"你已提交过该项目申请，当前状态为“{existing['status']}”。",
                "warning",
            )
            return redirect(
                url_for("upload_material", application_id=existing["id"])
            )

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            student_no = request.form.get("student_no", "").strip()
            reason = request.form.get("reason", "").strip()
            error = validate_application_form(full_name, student_no, reason)
            if error:
                flash(error, "danger")
                return render_template(
                    "apply.html", project=project, form=request.form
                )
            try:
                cursor = db.execute("""
                    INSERT INTO applications
                        (student_id, project_id, full_name, student_no, reason, status)
                    VALUES (?, ?, ?, ?, ?, '待审批')
                """, (session["user_id"], project_id, full_name, student_no, reason))
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                flash("该项目已有申请记录，请勿重复提交。", "warning")
                return redirect(url_for("dashboard"))
            flash("申请已提交。接下来可上传证明材料。", "success")
            return redirect(
                url_for("upload_material", application_id=cursor.lastrowid)
            )
        return render_template("apply.html", project=project, form={})

    @app.route(
        "/applications/<int:application_id>/upload", methods=["GET", "POST"]
    )
    @login_required("student")
    def upload_material(application_id):
        db = get_db()
        application = db.execute("""
            SELECT a.*, p.title AS project_title
            FROM applications a JOIN projects p ON p.id = a.project_id
            WHERE a.id = ? AND a.student_id = ?
        """, (application_id, session["user_id"])).fetchone()
        if not application:
            abort(404)
        allow_upload = application["status"] in UPLOADABLE_STATUSES

        if request.method == "POST":
            if not allow_upload:
                flash("当前申请状态不允许继续上传材料。", "warning")
                return redirect(url_for("dashboard"))

            material = request.files.get("material")
            if not material or not material.filename:
                flash("请选择需要上传的证明材料。", "danger")
                return redirect(request.url)

            original_name = safe_original_name(material.filename)
            if not allowed_file(original_name):
                flash("仅允许上传 PDF、PNG、JPG、JPEG 文件。", "danger")
                return redirect(request.url)

            extension = original_name.rsplit(".", 1)[1].lower()
            content = material.read(MAX_UPLOAD_BYTES + 1)
            if len(content) > MAX_UPLOAD_BYTES:
                flash("单个材料不能超过 5 MB。", "danger")
                return redirect(request.url)
            if not content:
                flash("上传文件不能为空。", "danger")
                return redirect(request.url)
            if not file_matches_extension(extension, content):
                flash("文件内容与扩展名不匹配，请上传真实的有效材料。", "danger")
                return redirect(request.url)

            stored_name = f"{uuid.uuid4().hex}.{extension}"
            target = Path(app.config["UPLOAD_FOLDER"]) / stored_name
            target.write_bytes(content)
            try:
                db.execute(
                    """
                    INSERT INTO materials
                        (application_id, original_name, stored_name)
                    VALUES (?, ?, ?)
                    """,
                    (application_id, original_name, stored_name),
                )
                if application["status"] == "退回补充材料":
                    db.execute(
                        """
                        UPDATE applications
                        SET status = '待审批', reviewed_by = NULL, reviewed_at = NULL
                        WHERE id = ?
                        """,
                        (application_id,),
                    )
                db.commit()
            except sqlite3.Error:
                db.rollback()
                target.unlink(missing_ok=True)
                raise

            flash("材料上传成功。", "success")
            return redirect(url_for("dashboard"))

        materials = db.execute(
            "SELECT * FROM materials WHERE application_id = ? ORDER BY id DESC",
            (application_id,),
        ).fetchall()
        return render_template(
            "upload.html",
            application=application,
            materials=materials,
            allow_upload=allow_upload,
        )

    @app.get("/materials/<int:material_id>")
    @login_required()
    def download_material(material_id):
        material = get_db().execute("""
            SELECT m.*, a.student_id
            FROM materials m JOIN applications a ON a.id = m.application_id
            WHERE m.id = ?
        """, (material_id,)).fetchone()
        if not material:
            abort(404)
        if session["role"] == "student" and material["student_id"] != session["user_id"]:
            abort(404)

        upload_dir = Path(app.config["UPLOAD_FOLDER"]).resolve()
        target = (upload_dir / Path(material["stored_name"]).name).resolve()
        if target.parent != upload_dir or not target.is_file():
            abort(404)
        return send_file(
            target,
            as_attachment=True,
            download_name=material["original_name"],
        )

    @app.get("/counselor/applications")
    @login_required("counselor")
    def counselor_applications():
        db = get_db()
        applications = db.execute("""
            SELECT a.*, u.username, p.title AS project_title
            FROM applications a
            JOIN users u ON u.id = a.student_id
            JOIN projects p ON p.id = a.project_id
            ORDER BY a.created_at DESC
        """).fetchall()
        materials = materials_by_application(
            db, [application["id"] for application in applications]
        )
        return render_template(
            "counselor.html",
            applications=applications,
            materials=materials,
            review_decisions=REVIEW_DECISIONS,
        )

    @app.post("/counselor/applications/<int:application_id>/review")
    @login_required("counselor")
    def review_application(application_id):
        decision = request.form.get("decision", "")
        comment = request.form.get("comment", "").strip()
        if decision not in REVIEW_DECISIONS:
            abort(400)
        if not comment:
            flash("请填写审批意见。", "danger")
            return redirect(url_for("counselor_applications"))
        if len(comment) > 1000:
            flash("审批意见不能超过 1000 个字符。", "danger")
            return redirect(url_for("counselor_applications"))

        db = get_db()
        application = db.execute(
            "SELECT id, status FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        if not application:
            abort(404)
        if application["status"] != "待审批":
            flash("该申请当前不是待审批状态，不能重复审批。", "warning")
            return redirect(url_for("counselor_applications"))

        cursor = db.execute("""
            UPDATE applications
            SET status = ?, review_comment = ?, reviewed_by = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = '待审批'
        """, (decision, comment, session["user_id"], application_id))
        db.commit()
        if cursor.rowcount == 0:
            flash("申请状态已发生变化，请刷新后重试。", "warning")
        else:
            flash("审批结果已保存。", "success")
        return redirect(url_for("counselor_applications"))

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_template(
            "error.html", code=400, message="表单已过期或安全令牌无效，请重新提交。"
        ), 400

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template(
            "error.html", code=400, message="请求参数不完整或格式不正确。"
        ), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "error.html", code=403, message="当前账号没有访问此页面的权限。"
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html",
            code=404,
            message="没有找到对应的资源，或你无权查看该申请。",
        ), 404

    @app.errorhandler(413)
    def request_too_large(_error):
        return render_template(
            "error.html", code=413, message="上传内容超过 5 MB 限制。"
        ), 413

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        )
        return response


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
