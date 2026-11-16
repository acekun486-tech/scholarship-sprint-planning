import sqlite3
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app import (
    MAX_NAME_LENGTH,
    MAX_REASON_LENGTH,
    MAX_REVIEW_COMMENT_LENGTH,
    MAX_UPLOAD_BYTES,
    create_app,
    escape_like,
    project_is_open,
    safe_original_name,
)
from database import get_db, init_db

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture()
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.db"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "WTF_CSRF_ENABLED": False,
        }
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username="student", password="student123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def submit_application(
    client, project_id=1, full_name="测试学生", student_no="20260001"
):
    return client.post(
        f"/apply/{project_id}",
        data={
            "full_name": full_name,
            "student_no": student_no,
            "reason": "符合该奖助学金项目的申请条件",
        },
        follow_redirects=False,
    )


def get_application(app):
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM applications ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_material(app):
    with app.app_context():
        row = get_db().execute(
            "SELECT * FROM materials ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def test_public_pages_search_and_security_headers(client):
    for path in ("/", "/notices", "/projects", "/projects/1"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"

    response = client.get("/projects?q=优秀")
    assert "优秀学生奖学金".encode() in response.data
    response = client.get("/projects?q=不存在的项目")
    assert "没有找到符合条件的项目".encode() in response.data


def test_health_check(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_deployment_paths_come_from_environment(tmp_path, monkeypatch):
    database_path = tmp_path / "runtime" / "app.db"
    upload_path = tmp_path / "runtime" / "uploads"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("UPLOAD_FOLDER", str(upload_path))

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "deployment-path-test",
            "WTF_CSRF_ENABLED": False,
        }
    )

    assert application.config["DATABASE"] == str(database_path)
    assert application.config["UPLOAD_FOLDER"] == str(upload_path)
    assert database_path.is_file()
    assert upload_path.is_dir()


def test_login_uses_hashed_password(app, client):
    response = login(client)
    assert response.status_code == 200
    assert "登录成功".encode() in response.data

    with app.app_context():
        user = get_db().execute(
            "SELECT password FROM users WHERE username = 'student'"
        ).fetchone()
        assert user["password"] != "student123"
        assert check_password_hash(user["password"], "student123")


def test_invalid_login_is_rejected(client):
    response = login(client, password="wrong-password")
    assert response.status_code == 200
    assert "用户名或密码不正确".encode() in response.data


def test_student_can_submit_application(app, client):
    login(client)
    response = submit_application(client)
    assert response.status_code == 302
    assert "/upload" in response.headers["Location"]

    application = get_application(app)
    assert application["status"] == "待审批"
    assert application["student_no"] == "20260001"


def test_application_input_is_validated(app, client):
    login(client)
    response = client.post(
        "/apply/1",
        data={"full_name": "", "student_no": "2026 0001", "reason": "理由"},
    )
    assert response.status_code == 200
    assert "均为必填项".encode() in response.data

    response = client.post(
        "/apply/1",
        data={"full_name": "测试学生", "student_no": "2026 0001", "reason": "理由"},
    )
    assert response.status_code == 200
    assert "学号不能包含空格".encode() in response.data
    assert get_application(app) is None


def test_duplicate_application_is_rejected(app, client):
    login(client)
    submit_application(client)
    response = submit_application(client, full_name="重复学生")
    assert response.status_code == 302
    with app.app_context():
        count = get_db().execute(
            "SELECT COUNT(*) FROM applications WHERE project_id = 1"
        ).fetchone()[0]
    assert count == 1


def test_application_insert_integrity_error_is_rejected(app, client):
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TRIGGER fail_application_insert
            BEFORE INSERT ON applications
            BEGIN
                SELECT RAISE(ABORT, 'simulated duplicate');
            END
        """)
        db.commit()

    login(client)
    response = submit_application(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    assert count == 0


def test_expired_project_cannot_be_applied_to(app, client):
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE projects SET deadline = ? WHERE id = 1",
            ((date.today() - timedelta(days=1)).isoformat(),),
        )
        db.commit()

    login(client)
    response = submit_application(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/projects")
    assert get_application(app) is None


def test_valid_upload_can_be_downloaded_by_owner_and_counselor(app, client):
    login(client)
    submit_application(client)
    response = client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(PDF_BYTES), "证明材料.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "材料上传成功".encode() in response.data

    material = get_material(app)
    assert material["original_name"] == "证明材料.pdf"
    assert material["stored_name"].endswith(".pdf")

    response = client.get(f"/materials/{material['id']}")
    assert response.status_code == 200
    assert response.data == PDF_BYTES

    client.post("/logout")
    login(client, "counselor", "counselor123")
    response = client.get(f"/materials/{material['id']}")
    assert response.status_code == 200
    assert response.data == PDF_BYTES


@pytest.mark.parametrize(
    ("filename", "content", "expected_message"),
    [
        ("malware.exe", PDF_BYTES, "仅允许上传"),
        ("fake.pdf", b"not a real pdf", "文件内容与扩展名不匹配"),
        ("empty.pdf", b"", "上传文件不能为空"),
    ],
)
def test_upload_rejects_invalid_files(
    app, client, filename, content, expected_message
):
    login(client)
    submit_application(client)
    response = client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert expected_message.encode() in response.data
    assert get_material(app) is None


def test_upload_rejects_file_over_five_megabytes(app, client):
    login(client)
    submit_application(client)
    oversized = b"%PDF-" + (b"0" * MAX_UPLOAD_BYTES)
    response = client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(oversized), "large.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "单个材料不能超过 5 MB".encode() in response.data
    assert get_material(app) is None


def test_student_cannot_access_another_students_application(app, client):
    login(client)
    submit_application(client)
    client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(PDF_BYTES), "owner.pdf")},
        content_type="multipart/form-data",
    )
    material = get_material(app)
    client.post("/logout")

    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'student')",
            ("student2", generate_password_hash("student456")),
        )
        db.commit()

    login(client, "student2", "student456")
    assert client.get("/applications/1/upload").status_code == 404
    assert client.get(f"/materials/{material['id']}").status_code == 404


def test_counselor_role_is_required(client):
    login(client)
    assert client.get("/counselor/applications").status_code == 403


def test_counselor_review_updates_student_result(app, client):
    login(client)
    submit_application(client)
    client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(PDF_BYTES), "proof.pdf")},
        content_type="multipart/form-data",
    )
    client.post("/logout")
    login(client, "counselor", "counselor123")

    page = client.get("/counselor/applications")
    assert b"proof.pdf" in page.data
    response = client.post(
        "/counselor/applications/1/review",
        data={"decision": "通过", "comment": "材料完整，同意申请。"},
        follow_redirects=True,
    )
    assert "审批结果已保存".encode() in response.data
    assert get_application(app)["status"] == "通过"

    client.post("/logout")
    login(client)
    dashboard = client.get("/dashboard")
    assert "通过".encode() in dashboard.data
    assert "材料完整，同意申请。".encode() in dashboard.data


def test_application_cannot_be_reviewed_twice(app, client):
    login(client)
    submit_application(client)
    client.post("/logout")
    login(client, "counselor", "counselor123")
    client.post(
        "/counselor/applications/1/review",
        data={"decision": "通过", "comment": "第一次审批"},
    )
    response = client.post(
        "/counselor/applications/1/review",
        data={"decision": "不通过", "comment": "第二次审批"},
        follow_redirects=True,
    )
    assert "不能重复审批".encode() in response.data
    application = get_application(app)
    assert application["status"] == "通过"
    assert application["review_comment"] == "第一次审批"


def test_review_comment_is_required(app, client):
    login(client)
    submit_application(client)
    client.post("/logout")
    login(client, "counselor", "counselor123")
    response = client.post(
        "/counselor/applications/1/review",
        data={"decision": "通过", "comment": "   "},
        follow_redirects=True,
    )
    assert "请填写审批意见".encode() in response.data
    assert get_application(app)["status"] == "待审批"


def test_returned_application_becomes_pending_after_new_material(app, client):
    login(client)
    submit_application(client)
    client.post("/logout")
    login(client, "counselor", "counselor123")
    client.post(
        "/counselor/applications/1/review",
        data={"decision": "退回补充材料", "comment": "请补充成绩证明。"},
    )
    client.post("/logout")

    login(client)
    response = client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(PDF_BYTES), "成绩证明.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "材料上传成功".encode() in response.data
    application = get_application(app)
    assert application["status"] == "待审批"
    assert application["reviewed_at"] is None


def test_completed_application_rejects_more_material(app, client):
    login(client)
    submit_application(client)
    client.post("/logout")
    login(client, "counselor", "counselor123")
    client.post(
        "/counselor/applications/1/review",
        data={"decision": "通过", "comment": "审批通过"},
    )
    client.post("/logout")

    login(client)
    response = client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(PDF_BYTES), "late.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "不允许继续上传材料".encode() in response.data
    assert get_material(app) is None


def test_csrf_is_enforced_when_enabled(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-test-secret",
            "DATABASE": str(tmp_path / "csrf.db"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "WTF_CSRF_ENABLED": True,
        }
    )
    with application.test_client() as client:
        response = client.post(
            "/login",
            data={"username": "student", "password": "student123"},
        )
    assert response.status_code == 400
    assert "安全令牌无效".encode() in response.data


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert "请先登录".encode() in response.data


def test_login_with_unknown_username_is_rejected(client):
    response = login(client, username="nobody", password="whatever")
    assert response.status_code == 200
    assert "用户名或密码不正确".encode() in response.data


def test_unknown_project_pages_return_404(app, client):
    assert client.get("/projects/999").status_code == 404

    login(client)
    assert client.get("/apply/999").status_code == 404


def test_apply_get_renders_form_and_length_limits(app, client):
    login(client)
    page = client.get("/apply/1")
    assert page.status_code == 200
    assert "申请理由".encode() in page.data

    response = client.post(
        "/apply/1",
        data={
            "full_name": "x" * (MAX_NAME_LENGTH + 1),
            "student_no": "20260001",
            "reason": "理由",
        },
    )
    assert f"姓名不能超过 {MAX_NAME_LENGTH} 个字符".encode() in response.data

    response = client.post(
        "/apply/1",
        data={
            "full_name": "测试学生",
            "student_no": "1" * 41,
            "reason": "理由",
        },
    )
    assert "学号不能包含空格，且不能超过 40 个字符".encode() in response.data

    response = client.post(
        "/apply/1",
        data={
            "full_name": "测试学生",
            "student_no": "20260001",
            "reason": "x" * (MAX_REASON_LENGTH + 1),
        },
    )
    assert f"申请理由不能超过 {MAX_REASON_LENGTH} 个字符".encode() in response.data
    assert get_application(app) is None


def test_project_with_invalid_deadline_is_closed():
    assert project_is_open({"deadline": "not-a-date"}) is False
    assert project_is_open({"deadline": None}) is False
    assert project_is_open({"deadline": date.today().isoformat()}) is True


def test_seeded_projects_have_open_deadlines(app):
    with app.app_context():
        projects = get_db().execute("SELECT deadline FROM projects").fetchall()
    assert projects
    assert all(project_is_open(project) for project in projects)


def test_search_wildcards_are_escaped(client):
    for wildcard in ("%", "_"):
        response = client.get(f"/projects?q={wildcard}")
        assert "没有找到符合条件的项目".encode() in response.data

    assert escape_like("100%_\\") == "100\\%\\_\\\\"


def test_safe_original_name_strips_paths_and_control_chars():
    assert safe_original_name("C:\\temp\\proof.pdf") == "proof.pdf"
    assert safe_original_name("../proof.pdf") == "proof.pdf"
    assert safe_original_name("\x00\x1f") == "未命名材料"
    assert len(safe_original_name("x" * 300 + ".pdf")) == 180


def test_upload_without_file_is_rejected(app, client):
    login(client)
    submit_application(client)

    response = client.post(
        "/applications/1/upload",
        data={},
        follow_redirects=True,
    )
    assert "请选择需要上传的证明材料".encode() in response.data
    assert get_material(app) is None


def test_upload_rolls_back_file_when_database_insert_fails(app, client):
    login(client)
    submit_application(client)
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TRIGGER fail_material_insert
            BEFORE INSERT ON materials
            BEGIN
                SELECT RAISE(ABORT, 'simulated failure');
            END
        """)
        db.commit()

    with pytest.raises(sqlite3.IntegrityError):
        client.post(
            "/applications/1/upload",
            data={"material": (BytesIO(PDF_BYTES), "proof.pdf")},
            content_type="multipart/form-data",
        )

    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    assert list(upload_dir.iterdir()) == []


def test_missing_material_and_stored_file_return_404(app, client):
    login(client)
    assert client.get("/materials/999").status_code == 404

    submit_application(client)
    client.post(
        "/applications/1/upload",
        data={"material": (BytesIO(PDF_BYTES), "proof.pdf")},
        content_type="multipart/form-data",
    )
    material = get_material(app)
    stored_file = Path(app.config["UPLOAD_FOLDER"]) / material["stored_name"]
    stored_file.unlink()

    assert client.get(f"/materials/{material['id']}").status_code == 404


def test_material_with_path_like_stored_name_returns_404(app, client):
    login(client)
    submit_application(client)
    with app.app_context():
        db = get_db()
        db.execute(
            """
            INSERT INTO materials (application_id, original_name, stored_name)
            VALUES (1, 'x.pdf', '../secret.pdf')
            """
        )
        db.commit()
        material_id = db.execute(
            "SELECT id FROM materials ORDER BY id DESC LIMIT 1"
        ).fetchone()["id"]

    assert client.get(f"/materials/{material_id}").status_code == 404


def test_review_rejects_invalid_decision(app, client):
    login(client, "counselor", "counselor123")

    response = client.post(
        "/counselor/applications/1/review",
        data={"decision": "maybe", "comment": "无效决定"},
    )
    assert response.status_code == 400
    assert "请求参数不完整或格式不正确".encode() in response.data


def test_review_comment_length_and_missing_application(app, client):
    login(client, "counselor", "counselor123")

    response = client.post(
        "/counselor/applications/1/review",
        data={
            "decision": "通过",
            "comment": "x" * (MAX_REVIEW_COMMENT_LENGTH + 1),
        },
        follow_redirects=True,
    )
    assert (
        f"审批意见不能超过 {MAX_REVIEW_COMMENT_LENGTH} 个字符".encode()
        in response.data
    )

    response = client.post(
        "/counselor/applications/999/review",
        data={"decision": "通过", "comment": "申请不存在"},
        follow_redirects=True,
    )
    assert response.status_code == 404


def test_review_reports_status_changed_when_update_is_skipped(app, client):
    login(client)
    submit_application(client)
    client.post("/logout")
    login(client, "counselor", "counselor123")

    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TRIGGER skip_approval
            BEFORE UPDATE ON applications
            WHEN NEW.status = '通过'
            BEGIN
                SELECT RAISE(IGNORE);
            END
        """)
        db.commit()

    response = client.post(
        "/counselor/applications/1/review",
        data={"decision": "通过", "comment": "并发状态已变化"},
        follow_redirects=True,
    )
    assert "申请状态已发生变化".encode() in response.data
    assert get_application(app)["status"] == "待审批"


def test_oversized_request_returns_413(client):
    response = client.post(
        "/login",
        data={
            "username": "x" * (MAX_UPLOAD_BYTES + 1024 * 1024),
            "password": "x",
        },
    )
    assert response.status_code == 413
    assert "上传内容超过 5 MB 限制".encode() in response.data


def test_database_helpers_and_migrations(app):
    with app.app_context():
        db = get_db()
        assert get_db() is db

        db.execute("DROP INDEX uq_applications_student_project")
        db.execute("DELETE FROM applications")
        db.executemany(
            """
            INSERT INTO applications
                (student_id, project_id, full_name, student_no, reason)
            VALUES (1, 1, ?, ?, 'reason')
            """,
            [("A", "1"), ("B", "2")],
        )
        db.execute("UPDATE users SET password = 'plain-demo' WHERE username = 'student'")
        db.commit()

        init_db()

        indexes = {row["name"] for row in db.execute("PRAGMA index_list('applications')")}
        assert "uq_applications_student_project" not in indexes

        user = db.execute(
            "SELECT password FROM users WHERE username = 'student'"
        ).fetchone()
        assert user["password"] != "plain-demo"
        assert check_password_hash(user["password"], "plain-demo")
