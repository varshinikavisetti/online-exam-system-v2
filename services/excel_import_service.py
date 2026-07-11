"""
Bulk question import from an uploaded .xlsx file.

Expected columns (header row, case-insensitive, order doesn't matter):
  question_type   -> "mcq" | "true_false" | "fill_blank"  (defaults to "mcq")
  question_text    -> required
  option_a, option_b, option_c, option_d  -> required for mcq
  correct_option    -> "A"/"B"/"C"/"D" for mcq, "True"/"False" for true_false
  correct_text       -> required for fill_blank
  marks              -> integer, defaults to 1

Kept as a standalone service (not inline in the route) so the parsing logic
is testable on its own and the route stays thin.
"""
import openpyxl
from models import db
from models.question import Question

REQUIRED_COLUMNS = {"question_text"}
KNOWN_COLUMNS = {
    "question_type", "question_text", "option_a", "option_b", "option_c",
    "option_d", "correct_option", "correct_text", "marks",
}


def _normalize_header(cell_value):
    return str(cell_value).strip().lower().replace(" ", "_") if cell_value else ""


def parse_questions_workbook(file_stream):
    """
    Reads an uploaded .xlsx file and returns (rows, errors):
      rows   -> list of dicts, one per valid question row, ready to build
                Question objects from
      errors -> list of human-readable strings describing any rows that
                were skipped and why (1-indexed against the spreadsheet,
                accounting for the header row)
    Raises ValueError if the file isn't a readable .xlsx or has no header
    row matching the expected columns at all.
    """
    try:
        wb = openpyxl.load_workbook(file_stream, read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError(f"Couldn't read this file as an Excel (.xlsx) workbook: {exc}")

    sheet = wb.active
    rows_iter = sheet.iter_rows(values_only=True)

    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise ValueError("The spreadsheet is empty.")

    headers = [_normalize_header(c) for c in header_row]
    if "question_text" not in headers:
        raise ValueError(
            "No 'question_text' column found. Expected headers: "
            "question_type, question_text, option_a, option_b, option_c, "
            "option_d, correct_option, correct_text, marks."
        )

    col_index = {h: i for i, h in enumerate(headers) if h}

    def get(row, name):
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return None
        val = row[idx]
        return str(val).strip() if val is not None else None

    valid_rows = []
    errors = []

    for line_num, row in enumerate(rows_iter, start=2):  # start=2: header was row 1
        if row is None or all(c is None for c in row):
            continue  # skip fully blank rows silently

        question_text = get(row, "question_text")
        if not question_text:
            errors.append(f"Row {line_num}: missing question_text — skipped.")
            continue

        q_type = (get(row, "question_type") or "mcq").lower()
        if q_type not in ("mcq", "true_false", "fill_blank"):
            errors.append(
                f"Row {line_num}: unknown question_type '{q_type}' — skipped "
                "(must be mcq, true_false, or fill_blank)."
            )
            continue

        marks_raw = get(row, "marks")
        try:
            marks = int(float(marks_raw)) if marks_raw else 1
        except ValueError:
            marks = 1
        marks = max(1, marks)

        entry = {
            "question_type": q_type,
            "question_text": question_text,
            "marks": marks,
            "option_a": None, "option_b": None, "option_c": None, "option_d": None,
            "correct_option": None, "correct_text": None,
        }

        if q_type == "mcq":
            opts = {k: get(row, k) for k in ("option_a", "option_b", "option_c", "option_d")}
            if not all(opts.values()):
                errors.append(f"Row {line_num}: MCQ is missing one or more options — skipped.")
                continue
            correct = (get(row, "correct_option") or "").upper()
            if correct not in ("A", "B", "C", "D"):
                errors.append(
                    f"Row {line_num}: correct_option must be A/B/C/D for MCQ — skipped."
                )
                continue
            entry.update(opts)
            entry["correct_option"] = correct

        elif q_type == "true_false":
            correct = (get(row, "correct_option") or "").strip().capitalize()
            if correct not in ("True", "False"):
                errors.append(
                    f"Row {line_num}: correct_option must be True/False — skipped."
                )
                continue
            entry["correct_option"] = correct

        elif q_type == "fill_blank":
            correct_text = get(row, "correct_text")
            if not correct_text:
                errors.append(f"Row {line_num}: fill_blank needs correct_text — skipped.")
                continue
            entry["correct_text"] = correct_text

        valid_rows.append(entry)

    return valid_rows, errors


def import_questions_into_exam(exam, file_stream):
    """Parses the workbook and commits valid rows as Question rows on the
    given exam. Returns (created_count, errors)."""
    rows, errors = parse_questions_workbook(file_stream)

    for entry in rows:
        db.session.add(Question(exam_id=exam.id, **entry))

    if rows:
        db.session.commit()
        exam.recalculate_total_marks()
        db.session.commit()

    return len(rows), errors
