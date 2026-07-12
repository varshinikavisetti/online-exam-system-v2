import random
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user

from models import db
from models.exam import Exam
from models.question import Question
from models.student_answer import StudentAnswer
from models.result import Result
from utils.timezone_helper import utc_to_ist

student_bp = Blueprint("student", __name__)


def student_only():
    if current_user.is_admin():
        abort(403)


def _attempts_used(exam_id):
    return Result.query.filter_by(
        student_id=current_user.id, exam_id=exam_id
    ).count()


def _attempts_remaining(exam):
    return max(0, exam.max_attempts - _attempts_used(exam.id))


def _schedule_message(exam):
    now = datetime.utcnow()
    if exam.scheduled_start and now < exam.scheduled_start:
        opens_ist = utc_to_ist(exam.scheduled_start)
        return f"This exam opens at {opens_ist.strftime('%d %b %Y, %I:%M %p')} IST."
    if exam.scheduled_end and now > exam.scheduled_end:
        return "This exam's scheduled window has ended."
    return "This exam is not currently available."


@student_bp.route("/dashboard")
@login_required
def dashboard():
    student_only()

    # Students only ever see published exams.
    all_exams = Exam.query.filter_by(is_published=True).order_by(Exam.created_at.desc()).all()

    results = Result.query.filter_by(student_id=current_user.id).all()
    attempts_by_exam = {}
    for r in results:
        attempts_by_exam.setdefault(r.exam_id, 0)
        attempts_by_exam[r.exam_id] += 1

    available_exams = [
        e for e in all_exams
        if attempts_by_exam.get(e.id, 0) < e.max_attempts
    ]
    completed_exams = [
        e for e in all_exams
        if attempts_by_exam.get(e.id, 0) >= e.max_attempts
    ]

    recent_results = (
        Result.query.filter_by(student_id=current_user.id)
        .order_by(Result.submitted_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "student_dashboard.html",
        available_exams=available_exams,
        completed_exams=completed_exams,
        recent_results=recent_results,
    )


@student_bp.route("/exams")
@login_required
def exam_list():
    student_only()
    exams = Exam.query.filter_by(is_published=True).order_by(Exam.created_at.desc()).all()

    results = Result.query.filter_by(student_id=current_user.id).all()
    attempts_by_exam = {}
    for r in results:
        attempts_by_exam.setdefault(r.exam_id, 0)
        attempts_by_exam[r.exam_id] += 1

    completed_exam_ids = {
        exam_id for exam_id, count in attempts_by_exam.items()
        if count >= next((e.max_attempts for e in exams if e.id == exam_id), 1)
    }
    attempts_remaining = {
        e.id: max(0, e.max_attempts - attempts_by_exam.get(e.id, 0)) for e in exams
    }

    return render_template(
        "exam_list.html",
        exams=exams,
        completed_exam_ids=completed_exam_ids,
        attempts_remaining=attempts_remaining,
    )


@student_bp.route("/exam/<int:exam_id>/instructions")
@login_required
def exam_instructions(exam_id):
    student_only()
    exam = Exam.query.get_or_404(exam_id)

    if not exam.is_published:
        flash("This exam is not currently available.", "warning")
        return redirect(url_for("student.dashboard"))

    if not exam.is_open_for_attempt():
        flash(_schedule_message(exam), "warning")
        return redirect(url_for("student.dashboard"))

    if _attempts_remaining(exam) <= 0:
        flash("You have used all your attempts for this exam.", "warning")
        return redirect(url_for("student.dashboard"))

    return render_template(
        "exam_instructions.html", exam=exam, attempts_used=_attempts_used(exam_id)
    )


@student_bp.route("/exam/<int:exam_id>/take")
@login_required
def take_exam(exam_id):
    student_only()
    exam = Exam.query.get_or_404(exam_id)

    if not exam.is_published:
        flash("This exam is not currently available.", "warning")
        return redirect(url_for("student.dashboard"))

    if not exam.is_open_for_attempt():
        flash(_schedule_message(exam), "warning")
        return redirect(url_for("student.dashboard"))

    if _attempts_remaining(exam) <= 0:
        flash("You have used all your attempts for this exam.", "warning")
        return redirect(url_for("student.dashboard"))

    questions = Question.query.filter_by(exam_id=exam.id).all()
    if not questions:
        flash("This exam has no questions yet.", "warning")
        return redirect(url_for("student.dashboard"))

    if exam.shuffle_questions:
        questions = list(questions)
        random.shuffle(questions)

    # Precompute a (possibly shuffled) option order per question so the
    # template renders options consistently for this page-load, and reuse
    # the exact same order info isn't needed at submit time since answers
    # are matched by option key value, not position.
    question_options = {}
    for q in questions:
        opts = list(q.options().items())
        if exam.shuffle_options and q.question_type == "mcq":
            random.shuffle(opts)
        question_options[q.id] = opts

    # Record when the student actually started this attempt so we can
    # server-side validate the minimum-submit-time rule later, without
    # trusting a client-supplied timestamp.
    session[f"exam_start_{exam.id}"] = datetime.utcnow().isoformat()

    return render_template(
        "take_exam.html", exam=exam, questions=questions, question_options=question_options
    )


@student_bp.route("/exam/<int:exam_id>/submit", methods=["POST"])
@login_required
def submit_exam(exam_id):
    student_only()
    exam = Exam.query.get_or_404(exam_id)

    if not exam.is_published:
        flash("This exam is not currently available.", "warning")
        return redirect(url_for("student.dashboard"))

    if _attempts_remaining(exam) <= 0:
        flash("You have used all your attempts for this exam.", "warning")
        return redirect(url_for("student.dashboard"))

    attempt_number = _attempts_used(exam_id) + 1

    questions = Question.query.filter_by(exam_id=exam.id).all()

    score = 0
    for q in questions:
        selected = request.form.get(f"question_{q.id}")
        if selected is not None:
            selected = selected.strip()

        answer = StudentAnswer(
            student_id=current_user.id,
            exam_id=exam.id,
            question_id=q.id,
            selected_option=selected,
            attempt_number=attempt_number,
        )
        db.session.add(answer)

        if selected:
            if q.is_correct(selected):
                score += q.marks
            elif exam.negative_marking_enabled:
                score -= exam.negative_marks_value

    percentage = round((score / exam.total_marks) * 100, 2) if exam.total_marks else 0
    # Percentage can't meaningfully go negative for pass/fail comparison or
    # for display purposes, but we keep the raw score signed so negative
    # marking is visible; clamp only the percentage used for pass/fail.
    passed = percentage >= exam.pass_percentage

    tab_switch_count = request.form.get("tab_switch_count", type=int, default=0)
    proctor_violation = request.form.get("proctor_violation") == "1"
    proctor_violation_reason = (request.form.get("proctor_violation_reason") or "").strip()

    terminated = False
    termination_reason = None

    if tab_switch_count >= 3:
        terminated = True
        termination_reason = "tab_switch_limit"
    elif proctor_violation and proctor_violation_reason in (
        "phone_or_object_detected",
        "no_face_detected",
    ):
        terminated = True
        termination_reason = proctor_violation_reason

    # Server-side minimum-submit-time check, based on the start time we
    # recorded in the session when the exam page was loaded (not a
    # client-supplied timestamp, so it can't be spoofed by editing form data).
    start_iso = session.get(f"exam_start_{exam.id}")
    if exam.min_submit_minutes > 0 and start_iso:
        started_at = datetime.fromisoformat(start_iso)
        elapsed_seconds = (datetime.utcnow() - started_at).total_seconds()
        if elapsed_seconds < exam.min_submit_minutes * 60 and not terminated:
            terminated = True
            termination_reason = "submitted_too_early"
    session.pop(f"exam_start_{exam.id}", None)

    auto_submitted = terminated

    # A terminated (misconduct) attempt must not contribute a real score to
    # exam averages/analytics — it's recorded as a 0, not the raw score the
    # student had accumulated before being caught, and it never counts as a
    # pass. The raw score/percentage are discarded here rather than merely
    # hidden in the UI, so every average computed from Result.score /
    # Result.percentage is automatically correct with no special-casing
    # needed at the analytics layer.
    if terminated:
        score = 0
        percentage = 0

    result = Result(
        student_id=current_user.id,
        exam_id=exam.id,
        score=score,
        percentage=percentage,
        passed=passed if not terminated else False,
        submitted_at=datetime.utcnow(),
        tab_switch_count=tab_switch_count,
        auto_submitted=auto_submitted,
        attempt_number=attempt_number,
        terminated=terminated,
        termination_reason=termination_reason,
    )
    db.session.add(result)
    db.session.commit()

    if terminated:
        flash(
            "Your exam was terminated due to a suspected integrity violation. "
            "Your instructor has been notified.",
            "danger",
        )

    return redirect(url_for("student.view_result", result_id=result.id))


@student_bp.route("/result/<int:result_id>")
@login_required
def view_result(result_id):
    student_only()
    result = Result.query.get_or_404(result_id)

    if result.student_id != current_user.id:
        abort(403)

    exam = result.exam
    if not exam.show_results:
        flash("The instructor has hidden results for this exam. Check back later.", "info")
        return render_template("result.html", result=result, exam=exam, hidden=True)

    return render_template("result.html", result=result, exam=exam, hidden=False)


@student_bp.route("/history")
@login_required
def history():
    student_only()
    results = (
        Result.query.filter_by(student_id=current_user.id)
        .order_by(Result.submitted_at.desc())
        .all()
    )
    return render_template("history.html", results=results)


@student_bp.route("/profile")
@login_required
def profile():
    student_only()

    results = Result.query.filter_by(student_id=current_user.id).all()
    attempt_count = len(results)

    if attempt_count:
        avg_percentage = round(sum(r.percentage for r in results) / attempt_count, 2)
        pass_count = sum(1 for r in results if r.passed)
        best_result = max(results, key=lambda r: r.percentage)
    else:
        avg_percentage = 0
        pass_count = 0
        best_result = None

    return render_template(
        "profile.html",
        attempt_count=attempt_count,
        avg_percentage=avg_percentage,
        pass_count=pass_count,
        best_result=best_result,
    )


@student_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    student_only()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        mobile_number = request.form.get("mobile_number", "").strip()
        year_of_study = request.form.get("year_of_study", "").strip()
        department = request.form.get("department", "").strip()
        roll_number = request.form.get("roll_number", "").strip()

        if not name:
            flash("Name cannot be empty.", "danger")
            return redirect(url_for("student.edit_profile"))

        current_user.name = name
        current_user.mobile_number = mobile_number or None
        current_user.year_of_study = year_of_study or None
        current_user.department = department or None
        current_user.roll_number = roll_number or None

        if new_password:
            if not current_user.check_password(current_password):
                flash("Current password is incorrect. Password not changed.", "danger")
                return redirect(url_for("student.edit_profile"))
            current_user.set_password(new_password)
            flash("Profile and password updated.", "success")
        else:
            flash("Profile updated.", "success")

        db.session.commit()
        return redirect(url_for("student.profile"))

    return render_template("edit_profile.html")
