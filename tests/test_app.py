"""
Automated smoke tests for the Online Exam System.
Runs against an in-memory SQLite database so no MySQL server is needed —
this is what the CI pipeline (.github/workflows/ci.yml) runs on every push.

Run locally with:  pytest
"""
import pytest
import config

config.Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

from app import create_app
from models import db
from models.user import User
from models.exam import Exam
from models.question import Question


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            admin = User(name="Admin", email="admin@test.com", role="admin")
            admin.set_password("adminpass")
            db.session.add(admin)
            db.session.commit()
        yield client


def register_and_login_student(client, email="alice@test.com"):
    client.post("/register", data={
        "name": "Alice", "email": email,
        "password": "pass123", "confirm_password": "pass123",
    })
    client.post("/login", data={"email": email, "password": "pass123"})


def test_landing_page_loads(client):
    r = client.get("/")
    assert r.status_code == 200


def test_student_registration_and_login(client):
    r = client.post("/register", data={
        "name": "Alice", "email": "alice@test.com",
        "password": "pass123", "confirm_password": "pass123",
    }, follow_redirects=True)
    assert r.status_code == 200

    r = client.post("/login", data={
        "email": "alice@test.com", "password": "pass123",
    }, follow_redirects=True)
    assert r.status_code == 200


def test_admin_can_create_exam_and_total_marks_auto_calculates(client):
    client.post("/login", data={"email": "admin@test.com", "password": "adminpass"})

    client.post("/admin/exams/create", data={
        "title": "Sample Exam", "subject": "CS", "duration": "10", "pass_percentage": "50",
    })

    with client.application.app_context():
        exam = Exam.query.filter_by(title="Sample Exam").first()
        assert exam.total_marks == 0  # no questions yet
        exam_id = exam.id

    client.post(f"/admin/exams/{exam_id}/questions/add", data={
        "question_text": "2+2=?", "option_a": "3", "option_b": "4",
        "option_c": "5", "option_d": "6", "correct_option": "B", "marks": "5",
    })

    with client.application.app_context():
        exam = Exam.query.get(exam_id)
        assert exam.total_marks == 5


def test_full_exam_flow_scores_correctly(client):
    client.post("/login", data={"email": "admin@test.com", "password": "adminpass"})
    client.post("/admin/exams/create", data={
        "title": "Flow Exam", "subject": "CS", "duration": "10", "pass_percentage": "50",
    })

    with client.application.app_context():
        exam = Exam.query.filter_by(title="Flow Exam").first()

    client.post(f"/admin/exams/{exam.id}/questions/add", data={
        "question_text": "2+2=?", "option_a": "3", "option_b": "4",
        "option_c": "5", "option_d": "6", "correct_option": "B", "marks": "10",
    })
    client.get("/logout")

    register_and_login_student(client)

    with client.application.app_context():
        q = Question.query.filter_by(exam_id=exam.id).first()

    r = client.post(f"/student/exam/{exam.id}/submit", data={
        f"question_{q.id}": "B",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b"100.0%" in r.data


def test_one_attempt_per_exam_enforced(client):
    client.post("/login", data={"email": "admin@test.com", "password": "adminpass"})
    client.post("/admin/exams/create", data={
        "title": "Single Attempt Exam", "subject": "CS", "duration": "10", "pass_percentage": "50",
    })
    with client.application.app_context():
        exam = Exam.query.filter_by(title="Single Attempt Exam").first()
    client.post(f"/admin/exams/{exam.id}/questions/add", data={
        "question_text": "Q1", "option_a": "a", "option_b": "b",
        "option_c": "c", "option_d": "d", "correct_option": "A", "marks": "1",
    })
    client.get("/logout")

    register_and_login_student(client, email="bob@test.com")
    with client.application.app_context():
        q = Question.query.filter_by(exam_id=exam.id).first()

    client.post(f"/student/exam/{exam.id}/submit", data={f"question_{q.id}": "A"})

    # Second attempt should be blocked
    r = client.get(f"/student/exam/{exam.id}/take", follow_redirects=True)
    assert b"already completed" in r.data
