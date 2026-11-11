import re
from engine.content import apply_patches, math_errors, payload, read_field, text


def validate_proposal(question, verdict, repair, patches, taxonomy):
    errors = []
    if verdict not in taxonomy["verdicts"]:
        errors.append("Unknown verdict")
    if verdict != "defect" and (repair or patches):
        errors.append("Non-defect cannot carry a repair")
    if verdict == "defect" and repair not in taxonomy["repairs"]:
        errors.append("Defect must have a known repair")
    rule = taxonomy["repairs"].get(repair, {"fields": [], "auto": False})
    if not rule["fields"] and patches:
        errors.append("Faculty-only repair cannot carry machine patches")
    for patch in patches:
        field, find, replace = patch["field"], patch["find"], patch["replace"]
        if field not in rule["fields"]:
            errors.append("Field outside repair scope: " + field)
            continue
        old = read_field(question, field)
        if find == replace:
            errors.append("No-op patch")
        if field in ("answer", "questionType"):
            if find != old:
                errors.append("Stale field value")
        elif not isinstance(find, str) or not isinstance(replace, str) or not find or old.count(find) != 1:
            errors.append("Find must be a unique nonempty source span")
        else:
            if re.search(r"<\s*(script|iframe|object|embed|svg)|\bon\w+\s*=|javascript:", replace, re.I):
                errors.append("Unsafe replacement markup")
            if repair == "spelling":
                # Words may change; numbers, operators and tags must not.
                protected = lambda s: re.findall(r"<[^>]+>|\d+(?:\.\d+)?|[^\w\s]", s)
                if protected(find) != protected(replace):
                    errors.append("Spelling edit changes protected tokens")
            if repair == "answer_form" and find not in replace:
                errors.append("Answer-form edit must be additive")
            if repair == "option_repair":
                option_at = re.search(r"\(A\)", old)
                if not option_at or old.index(find) < option_at.start():
                    errors.append("Option repair changes stem")
            if repair not in ("solution_missing",) and len(find) > max(160, len(old) * .65):
                errors.append("Replacement is too broad; review required")
            new = old.replace(find, replace, 1)
            if math_errors(new) > math_errors(old):
                errors.append("Replacement damages MathML nesting")
    if errors:
        return sorted(set(errors))
    try:
        changed = apply_patches(question, patches)
        answer = payload(changed)["answer"]
        kind = changed["questionType"]
        if kind not in ("scq", "mcq", "integerQuestion"):
            errors.append("Unknown question type")
        if kind == "scq" and not (isinstance(answer, str) and re.fullmatch("[A-D]", answer)):
            errors.append("SCQ key must be one option label")
        if kind == "mcq" and (not isinstance(answer, list) or not answer or
                any(not re.fullmatch("[A-D]", a) for a in answer) or len(set(answer)) != len(answer)):
            # Pre-existing malformed keys only block actual content patches.
            if patches:
                errors.append("MCQ key must contain distinct individual option labels")
        if kind == "integerQuestion" and not (isinstance(answer, str) and re.fullmatch(r"-?\d+", answer)):
            errors.append("Integer key must be an integer string")
    except (ValueError, KeyError, TypeError) as error:
        errors.append(str(error))
    return errors
