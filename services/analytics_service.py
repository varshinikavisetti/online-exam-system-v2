"""
Aggregation queries for the admin analytics dashboard.
Kept separate from routes so the logic is reusable/testable on its own.
"""
from models import db
from models.exam import Exam
from models.result import Result
from models.question import Question
from models.student_answer import StudentAnswer


def exam_performance_summary():
    """
    Returns a list of dicts, one per exam:
    { exam_title, average_percentage, pass_count, fail_count, attempt_count }
    """
    exams = Exam.query.all()
    summary = []

    for exam in exams:
        results = Result.query.filter_by(exam_id=exam.id).all()
        attempt_count = len(results)

        if attempt_count == 0:
            avg_percentage = 0
            pass_count = 0
            fail_count = 0
        else:
            avg_percentage = round(
                sum(r.percentage for r in results) / attempt_count, 2
            )
            pass_count = sum(1 for r in results if r.passed)
            fail_count = attempt_count - pass_count

        summary.append({
            "exam_id": exam.id,
            "exam_title": exam.title,
            "average_percentage": avg_percentage,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "attempt_count": attempt_count,
        })

    return summary


def question_difficulty_report(exam_id=None):
    """
    Returns a list of dicts, one per question:
    { question_text, wrong_percentage, attempt_count }
    Optionally filtered to a single exam.
    """
    query = Question.query
    if exam_id:
        query = query.filter_by(exam_id=exam_id)
    questions = query.all()

    report = []
    for q in questions:
        answers = StudentAnswer.query.filter_by(question_id=q.id).all()
        attempt_count = len(answers)

        if attempt_count == 0:
            wrong_percentage = 0
        else:
            wrong_count = sum(
                1 for a in answers if not q.is_correct(a.selected_option)
            )
            wrong_percentage = round((wrong_count / attempt_count) * 100, 2)

        # Truncate long question text for chart labels
        label = q.question_text if len(q.question_text) <= 40 else q.question_text[:37] + "..."

        report.append({
            "question_text": label,
            "wrong_percentage": wrong_percentage,
            "attempt_count": attempt_count,
        })

    return report


def overall_pass_fail_counts(exam_id=None):
    """Returns { 'pass': int, 'fail': int }. Optionally filtered to a single exam."""
    query = Result.query
    if exam_id:
        query = query.filter_by(exam_id=exam_id)
    all_results = query.all()
    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed
    return {"pass": passed, "fail": failed}


def performance_trend(exam_id=None):
    """
    Returns a list of dicts, one per calendar day that had submissions,
    ordered oldest -> newest:
    { date, average_percentage, attempt_count }
    Used to chart how student performance is trending over time.
    Optionally filtered to a single exam.
    """
    query = Result.query
    if exam_id:
        query = query.filter_by(exam_id=exam_id)
    all_results = query.order_by(Result.submitted_at.asc()).all()

    by_day = {}
    for r in all_results:
        day_key = r.submitted_at.strftime("%Y-%m-%d")
        by_day.setdefault(day_key, []).append(r.percentage)

    trend = []
    for day_key in sorted(by_day.keys()):
        percentages = by_day[day_key]
        trend.append({
            "date": day_key,
            "average_percentage": round(sum(percentages) / len(percentages), 2),
            "attempt_count": len(percentages),
        })

    return trend
