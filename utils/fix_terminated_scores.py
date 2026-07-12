"""
One-time cleanup: zero out score/percentage on Result rows that were
terminated for misconduct but still carry a nonzero score/percentage from
before this fix existed. New terminations already save correctly (see
routes/student.py submit_exam) — this only backfills old rows.

Usage:
    python -m utils.fix_terminated_scores
"""
from app import create_app
from models import db
from models.result import Result

app = create_app()

with app.app_context():
    bad_rows = Result.query.filter(
        Result.terminated.is_(True), Result.score != 0
    ).all()

    if not bad_rows:
        print("No terminated results with a nonzero score found. Nothing to fix.")
    else:
        print(f"Found {len(bad_rows)} terminated result(s) with a nonzero score:")
        for r in bad_rows:
            print(
                f"  Result id={r.id} student_id={r.student_id} exam_id={r.exam_id} "
                f"score={r.score} -> 0, percentage={r.percentage} -> 0"
            )
            r.score = 0
            r.percentage = 0
        db.session.commit()
        print(f"Fixed {len(bad_rows)} result(s).")
