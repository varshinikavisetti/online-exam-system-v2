"""
Read-only diagnostic: prints every Result row with all its integrity-related
fields, so we can see what's actually stored vs. what was expected.

Usage:
    python -m utils.inspect_results
    python -m utils.inspect_results "Java"   (filter by exam title substring)
"""
import sys
from app import create_app
from models.exam import Exam
from models.result import Result
from models.user import User

app = create_app()

with app.app_context():
    filter_text = sys.argv[1].lower() if len(sys.argv) > 1 else None

    query = Result.query.join(Exam, Result.exam_id == Exam.id)
    if filter_text:
        query = query.filter(Exam.title.ilike(f"%{filter_text}%"))

    results = query.order_by(Result.exam_id, Result.submitted_at).all()

    if not results:
        print("No results found.")
    for r in results:
        exam = Exam.query.get(r.exam_id)
        student = User.query.get(r.student_id)
        print(
            f"Result id={r.id} | exam='{exam.title if exam else '?'}' "
            f"(exam_id={r.exam_id}) | student={student.name if student else '?'} "
            f"| score={r.score} | percentage={r.percentage} | passed={r.passed} "
            f"| terminated={r.terminated} | termination_reason={r.termination_reason} "
            f"| tab_switch_count={r.tab_switch_count} | auto_submitted={r.auto_submitted} "
            f"| submitted_at={r.submitted_at}"
        )
