from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from models import db
from models.user import User
from models.exam import Exam
from models.question import Question
from models.result import Result
from services.analytics_service import (
    exam_performance_summary,
    question_difficulty_report,
    overall_pass_fail_counts,
    performance_trend,
)
from services.email_service import send_exam_notification_to_students
from utils.timezone_helper import ist_input_to_utc, utc_to_ist

admin_bp = Blueprint("admin", __name__)


def admin_only():
    if not current_user.is_admin():
        abort(403)


# Kept as an alias so nothing else needs to change: admin-entered schedule
# times are IST (this college's timezone), not literal UTC — see
# utils/timezone_helper.py for why that distinction matters.
_parse_datetime_local = ist_input_to_utc


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    admin_only()

    total_students = User.query.filter_by(role="student").count()
    total_exams = Exam.query.count()
    total_questions = Question.query.count()
    recent_results = (
        Result.query.order_by(Result.submitted_at.desc()).limit(5).all()
    )

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_exams=total_exams,
        total_questions=total_questions,
        recent_results=recent_results,
    )


@admin_bp.route("/exams")
@login_required
def manage_exams():
    admin_only()
    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    return render_template("manage_exams.html", exams=exams)


@admin_bp.route("/exams/create", methods=["GET", "POST"])
@login_required
def create_exam():
    admin_only()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        duration = request.form.get("duration", type=int)
        pass_percentage = request.form.get("pass_percentage", type=int, default=40)

        negative_marking_enabled = request.form.get("negative_marking_enabled") == "on"
        negative_marks_value = request.form.get("negative_marks_value", type=float, default=0) or 0
        shuffle_questions = request.form.get("shuffle_questions") == "on"
        shuffle_options = request.form.get("shuffle_options") == "on"
        max_attempts = request.form.get("max_attempts", type=int, default=1) or 1
        show_results = request.form.get("show_results") == "on"
        is_published = request.form.get("is_published") == "on"
        min_submit_minutes = request.form.get("min_submit_minutes", type=int, default=0) or 0
        webcam_proctoring_enabled = request.form.get("webcam_proctoring_enabled") == "on"
        scheduled_start = _parse_datetime_local(request.form.get("scheduled_start"))
        scheduled_end = _parse_datetime_local(request.form.get("scheduled_end"))

        if not title or not subject or not duration:
            flash("All fields are required.", "danger")
            return redirect(url_for("admin.create_exam"))

        if scheduled_start and scheduled_end and scheduled_end <= scheduled_start:
            flash("Scheduled end time must be after the start time.", "danger")
            return redirect(url_for("admin.create_exam"))

        # total_marks starts at 0 and is automatically kept in sync with the
        # actual sum of question marks as questions are added/edited/removed.
        exam = Exam(
            title=title,
            subject=subject,
            duration=duration,
            total_marks=0,
            pass_percentage=pass_percentage or 40,
            negative_marking_enabled=negative_marking_enabled,
            negative_marks_value=negative_marks_value,
            shuffle_questions=shuffle_questions,
            shuffle_options=shuffle_options,
            max_attempts=max(1, max_attempts),
            show_results=show_results,
            is_published=is_published,
            min_submit_minutes=max(0, min_submit_minutes),
            webcam_proctoring_enabled=webcam_proctoring_enabled,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
        )
        db.session.add(exam)
        db.session.commit()

        flash("Exam created. Now add some questions.", "success")
        return redirect(url_for("admin.manage_questions", exam_id=exam.id))

    return render_template("create_exam.html")


@admin_bp.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exam(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        duration = request.form.get("duration", type=int)
        pass_percentage = request.form.get("pass_percentage", type=int, default=40)

        if not title or not subject or not duration:
            flash("All fields are required.", "danger")
            return redirect(url_for("admin.edit_exam", exam_id=exam.id))

        exam.title = title
        exam.subject = subject
        exam.duration = duration
        exam.pass_percentage = pass_percentage or 40
        exam.negative_marking_enabled = request.form.get("negative_marking_enabled") == "on"
        exam.negative_marks_value = request.form.get("negative_marks_value", type=float, default=0) or 0
        exam.shuffle_questions = request.form.get("shuffle_questions") == "on"
        exam.shuffle_options = request.form.get("shuffle_options") == "on"
        exam.max_attempts = max(1, request.form.get("max_attempts", type=int, default=1) or 1)
        exam.show_results = request.form.get("show_results") == "on"
        exam.is_published = request.form.get("is_published") == "on"
        exam.min_submit_minutes = max(0, request.form.get("min_submit_minutes", type=int, default=0) or 0)
        exam.webcam_proctoring_enabled = request.form.get("webcam_proctoring_enabled") == "on"

        scheduled_start = _parse_datetime_local(request.form.get("scheduled_start"))
        scheduled_end = _parse_datetime_local(request.form.get("scheduled_end"))
        if scheduled_start and scheduled_end and scheduled_end <= scheduled_start:
            flash("Scheduled end time must be after the start time.", "danger")
            return redirect(url_for("admin.edit_exam", exam_id=exam.id))
        exam.scheduled_start = scheduled_start
        exam.scheduled_end = scheduled_end

        db.session.commit()
        flash("Exam settings updated.", "success")
        return redirect(url_for("admin.manage_exams"))

    return render_template("edit_exam.html", exam=exam)


@admin_bp.route("/exams/<int:exam_id>/toggle-publish", methods=["POST"])
@login_required
def toggle_publish(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)
    exam.is_published = not exam.is_published
    db.session.commit()
    flash(
        f"Exam '{exam.title}' is now {'published' if exam.is_published else 'unpublished'}.",
        "success",
    )
    return redirect(url_for("admin.manage_exams"))


@admin_bp.route("/exams/<int:exam_id>/delete", methods=["POST"])
@login_required
def delete_exam(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash("Exam deleted.", "info")
    return redirect(url_for("admin.manage_exams"))


@admin_bp.route("/exams/<int:exam_id>/questions")
@login_required
def manage_questions(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam.id).all()
    return render_template("manage_questions.html", exam=exam, questions=questions)


@admin_bp.route("/exams/<int:exam_id>/questions/add", methods=["GET", "POST"])
@login_required
def add_question(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)

    if request.method == "POST":
        question_type = request.form.get("question_type", "mcq")

        q = Question(
            exam_id=exam.id,
            question_type=question_type,
            question_text=request.form.get("question_text", "").strip(),
            marks=request.form.get("marks", type=int, default=1),
        )

        if question_type == "mcq":
            q.option_a = request.form.get("option_a", "").strip()
            q.option_b = request.form.get("option_b", "").strip()
            q.option_c = request.form.get("option_c", "").strip()
            q.option_d = request.form.get("option_d", "").strip()
            q.correct_option = request.form.get("correct_option", "A")
        elif question_type == "true_false":
            q.correct_option = request.form.get("correct_tf", "True")
        elif question_type == "fill_blank":
            q.correct_text = request.form.get("correct_text", "").strip()

        db.session.add(q)
        db.session.commit()

        exam.recalculate_total_marks()
        db.session.commit()

        flash(f"Question added. Exam total is now {exam.total_marks} marks.", "success")
        return redirect(url_for("admin.manage_questions", exam_id=exam.id))

    return render_template("add_question.html", exam=exam)


@admin_bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
@login_required
def edit_question(question_id):
    admin_only()
    question = Question.query.get_or_404(question_id)

    if request.method == "POST":
        question_type = request.form.get("question_type", "mcq")

        question.question_type = question_type
        question.question_text = request.form.get("question_text", "").strip()
        question.marks = request.form.get("marks", type=int, default=1)

        # Reset all type-specific fields, then set the ones relevant to the
        # chosen type, so switching a question's type doesn't leave stale data.
        question.option_a = question.option_b = question.option_c = question.option_d = None
        question.correct_option = None
        question.correct_text = None

        if question_type == "mcq":
            question.option_a = request.form.get("option_a", "").strip()
            question.option_b = request.form.get("option_b", "").strip()
            question.option_c = request.form.get("option_c", "").strip()
            question.option_d = request.form.get("option_d", "").strip()
            question.correct_option = request.form.get("correct_option", "A")
        elif question_type == "true_false":
            question.correct_option = request.form.get("correct_tf", "True")
        elif question_type == "fill_blank":
            question.correct_text = request.form.get("correct_text", "").strip()

        db.session.commit()

        question.exam.recalculate_total_marks()
        db.session.commit()

        flash(f"Question updated. Exam total is now {question.exam.total_marks} marks.", "success")
        return redirect(url_for("admin.manage_questions", exam_id=question.exam_id))

    return render_template("edit_question.html", question=question)


@admin_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@login_required
def delete_question(question_id):
    admin_only()
    question = Question.query.get_or_404(question_id)
    exam_id = question.exam_id
    exam = question.exam
    db.session.delete(question)
    db.session.commit()

    exam.recalculate_total_marks()
    db.session.commit()

    flash(f"Question deleted. Exam total is now {exam.total_marks} marks.", "info")
    return redirect(url_for("admin.manage_questions", exam_id=exam_id))


@admin_bp.route("/exams/<int:exam_id>/questions/import", methods=["POST"])
@login_required
def import_questions(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)

    file = request.files.get("questions_file")
    if not file or not file.filename:
        flash("Please choose an .xlsx file to import.", "danger")
        return redirect(url_for("admin.manage_questions", exam_id=exam.id))

    if not file.filename.lower().endswith(".xlsx"):
        flash("Only .xlsx files are supported for question import.", "danger")
        return redirect(url_for("admin.manage_questions", exam_id=exam.id))

    from services.excel_import_service import import_questions_into_exam

    try:
        created, errors = import_questions_into_exam(exam, file.stream)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.manage_questions", exam_id=exam.id))

    if created:
        flash(
            f"Imported {created} question(s). Exam total is now {exam.total_marks} marks.",
            "success",
        )
    if errors:
        # Cap how many we show inline so one bad file doesn't flood the page.
        shown = errors[:10]
        more = f" ({len(errors) - 10} more not shown)" if len(errors) > 10 else ""
        flash("Some rows were skipped: " + " | ".join(shown) + more, "warning")
    if not created and not errors:
        flash("No rows found in that file.", "warning")

    return redirect(url_for("admin.manage_questions", exam_id=exam.id))


@admin_bp.route("/exams/<int:exam_id>/notify-students", methods=["POST"])
@login_required
def notify_students(exam_id):
    admin_only()
    exam = Exam.query.get_or_404(exam_id)
    students = User.query.filter_by(role="student").all()

    sent, error = send_exam_notification_to_students(exam, students)
    if error:
        flash(error, "warning")
    else:
        flash(f"Notification email sent to {sent} student(s).", "success")

    return redirect(url_for("admin.manage_exams"))


@admin_bp.route("/students")
@login_required
def view_students():
    admin_only()
    students = User.query.filter_by(role="student").all()
    return render_template("view_students.html", students=students)


@admin_bp.route("/results")
@login_required
def view_results():
    admin_only()
    search = request.args.get("search", "").strip()
    # Results were previously always shown as one combined list across every
    # exam, which looked like "everything is mixed together". Default to
    # the most recently created exam so results are exam-scoped by default;
    # "All exams" is still available via exam_id=0 for a combined view.
    exam_id = request.args.get("exam_id", type=int)

    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    if exam_id is None and exams:
        exam_id = exams[0].id

    query = Result.query.join(User, Result.student_id == User.id)
    if exam_id:
        query = query.filter(Result.exam_id == exam_id)
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    results = query.order_by(Result.submitted_at.desc()).all()
    return render_template(
        "view_results.html",
        results=results,
        search=search,
        exams=exams,
        selected_exam_id=exam_id,
    )


# ---------- Analytics ----------

@admin_bp.route("/analytics")
@login_required
def analytics():
    admin_only()

    exam_id = request.args.get("exam_id", type=int)

    exam_summary = exam_performance_summary(exam_id=exam_id)
    difficulty_report = question_difficulty_report(exam_id=exam_id)
    pass_fail = overall_pass_fail_counts(exam_id=exam_id)
    trend = performance_trend(exam_id=exam_id)
    all_exams = Exam.query.order_by(Exam.created_at.desc()).all()

    selected_exam_title = None
    if exam_id:
        selected = Exam.query.get(exam_id)
        selected_exam_title = selected.title if selected else None

    return render_template(
        "analytics.html",
        exam_summary=exam_summary,
        difficulty_report=difficulty_report,
        pass_fail=pass_fail,
        trend=trend,
        all_exams=all_exams,
        selected_exam_id=exam_id,
        selected_exam_title=selected_exam_title,
    )
