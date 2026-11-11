import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from engine.checks import academic_checks
from engine.cli import load_data, validate_export, ROOT
from engine.content import apply_patches, digest, payload
from engine.models import Result
from engine.provider import Gemini
from engine.reviewed import decisions
from engine.validation import validate_proposal

QUESTIONS, REPORTS, TAXONOMY = load_data()
BY_ID = {q["_id"]: q for q in QUESTIONS}
Q_FOR_REPORT = {r["reportId"]: BY_ID[r["questionId"]] for r in REPORTS}
CATALOG = decisions(QUESTIONS)


def test_export_exact_coverage_and_mapping():
    results = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    validate_export(results, QUESTIONS, REPORTS, TAXONOMY)
    assert len(results) == 44
    assert len({r["questionId"] for r in results}) == 39
    assert {r["reportId"] for r in results} == {r["reportId"] for r in REPORTS}


def test_duplicate_expansion_has_one_shared_proposal():
    rows = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    group = [r for r in rows if r["reportId"] in ["R001", "R002", "R003"]]
    assert len(group) == 3
    assert len({json.dumps(r["edit"], sort_keys=True) for r in group}) == 1


def test_all_reviewed_patches_respect_scope_and_apply_without_mutating_input():
    for rid, decision in CATALOG.items():
        q = Q_FOR_REPORT[rid]
        before = copy.deepcopy(q)
        errors = validate_proposal(q, decision["verdict"], decision["repair"], decision["patches"], TAXONOMY)
        assert not errors, (rid, errors)
        apply_patches(q, decision["patches"])
        assert q == before


@pytest.mark.parametrize("repair", [key for key, rule in TAXONOMY["repairs"].items() if not rule["auto"]])
def test_manual_repairs_cannot_carry_machine_edits(repair):
    assert validate_proposal(Q_FOR_REPORT["R001"], "defect", repair,
        [{"field": "answer", "find": "C", "replace": "A"}], TAXONOMY)


def test_patch_rejects_ambiguous_empty_stale_and_out_of_scope_edits():
    q = Q_FOR_REPORT["R012"]
    for patch in [
        {"field": "question", "find": "", "replace": "x"},
        {"field": "question", "find": "span", "replace": "div"},
        {"field": "question", "find": "not present", "replace": "x"},
        {"field": "answer", "find": "A", "replace": "B"},
    ]:
        assert validate_proposal(q, "defect", "spelling", [patch], TAXONOMY)


def test_spelling_cannot_change_numeric_or_math_tokens():
    q = Q_FOR_REPORT["R001"]
    assert validate_proposal(q, "defect", "spelling", [{"field": "question", "find": "60 V", "replace": "90 V"}], TAXONOMY)


def test_additive_and_option_stem_guards():
    q = Q_FOR_REPORT["R011"]
    assert validate_proposal(q, "defect", "option_repair", [{"field": "question", "find": "There are two charges", "replace": "There are three charges"}], TAXONOMY)
    q = Q_FOR_REPORT["R024"]
    assert validate_proposal(q, "defect", "answer_form", [{"field": "question", "find": "frictional force", "replace": "normal force"}], TAXONOMY)


def test_rejects_executable_replacement():
    q = Q_FOR_REPORT["R012"]
    assert validate_proposal(q, "defect", "spelling", [{"field": "question", "find": "Epithellial tisue", "replace": '<script>alert(1)</script>'}], TAXONOMY)


def test_unknown_type_is_rejected():
    q = Q_FOR_REPORT["R021"]
    assert validate_proposal(q, "defect", "type_mismatch", [{"field": "questionType", "find": "mcq", "replace": "bogus"}], TAXONOMY)


def test_malformed_answer_serialization_and_atomic_type_migration():
    for rid in ["R020", "R021"]:
        q = Q_FOR_REPORT[rid]
        patched = apply_patches(q, CATALOG[rid]["patches"])
        if rid == "R020":
            assert payload(patched)["answer"] == ["A", "B", "D"]
        else:
            assert patched["questionType"] == "scq"
            assert "mcq" not in patched
            assert patched["scq"]["answer"] == "B"


def test_real_math_checks_and_traps():
    checks = academic_checks()
    assert len(checks) >= 20 and all(c["passed"] for c in checks.values())
    assert checks["gas_pressure"]["value"] == 4800
    assert checks["buoyancy"]["value"] == 20
    assert checks["sphere"]["value"] == 14
    assert checks["ydse"]["value"] == pytest.approx(8)
    assert CATALOG["R027"]["verdict"] == "no_error"
    assert CATALOG["R027"]["patches"] == []
    assert CATALOG["R017"]["verdict"] == "already_fixed"
    assert CATALOG["R034"]["repair"] == "unsound"
    assert CATALOG["R009"]["patches"] == []


def test_output_rejects_invented_fields_and_confidence_outside_range():
    row = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))[0]
    with pytest.raises(ValidationError):
        Result.model_validate({**row, "confidence": 1.01})
    with pytest.raises(ValidationError):
        Result.model_validate({**row, "made_up_ground_truth": True})


def test_repeated_application_is_stale():
    q = Q_FOR_REPORT["R001"]
    patch = CATALOG["R001"]["patches"]
    changed = apply_patches(q, patch)
    with pytest.raises(ValueError):
        apply_patches(changed, patch)


def test_source_lock_and_dataset_remain_unchanged():
    lock = json.loads((ROOT / "engine/source-lock.json").read_text())
    for name in ["questions", "reports", "taxonomy"]:
        assert digest(json.loads((ROOT / f"data/{name}.json").read_text(encoding="utf-8"))) == lock[name]


def test_export_rejects_nondefect_repair_and_defect_nochange():
    rows = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(rows)
    bad[0].update(verdict="no_error", repair="spelling", edit=None, route="no_change")
    with pytest.raises(ValueError, match="Non-defect"):
        validate_export(bad, QUESTIONS, REPORTS, TAXONOMY)
    bad = copy.deepcopy(rows)
    defect = next(r for r in bad if r["verdict"] == "defect")
    defect["route"] = "no_change"
    with pytest.raises(ValueError, match="defect requires"):
        validate_export(bad, QUESTIONS, REPORTS, TAXONOMY)


def test_provider_refuses_missing_credentials_without_replacing_results(monkeypatch, tmp_path):
    import engine.provider as module
    monkeypatch.setattr(module, "load_env", lambda: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    before = (ROOT / "results.json").read_bytes()
    with pytest.raises(ValueError, match="no live results"):
        Gemini(tmp_path)
    assert (ROOT / "results.json").read_bytes() == before


def test_blind_key_disagreement_overrides_false_no_error_claim():
    from engine.cli import reconcile_blind_key
    question = next(q for q in QUESTIONS if q["_id"] == next(r["questionId"] for r in REPORTS if r["reportId"] == "R004"))
    solves = [{"answer": "D", "sufficient_data": True}, {"answer": "(D)", "sufficient_data": True}]
    proposal = {"verdict": "no_error", "repair": None, "patches": [], "unresolved": False,
        "evidence": "Wrongly says the key matches", "student_reply": "The key is correct."}
    result = reconcile_blind_key(question, solves, proposal)
    assert result["verdict"] == "defect" and result["repair"] == "answer_key"
    assert result["patches"] == [] and result["unresolved"] is True
    assert "stored answer A" in result["evidence"] and "blind answers D" in result["evidence"]


def test_blind_key_consensus_blocks_contradictory_patch():
    from engine.cli import reconcile_blind_key
    question = next(q for q in QUESTIONS if q["_id"] == next(r["questionId"] for r in REPORTS if r["reportId"] == "R029"))
    solves = [{"answer": "(A)", "sufficient_data": True}, {"answer": "A", "sufficient_data": True}]
    proposal = {"verdict": "defect", "repair": "answer_key", "patches": [{"field": "answer", "find": "A", "replace": "C"}],
        "unresolved": False, "evidence": "Wrong edit", "student_reply": "Review pending."}
    result = reconcile_blind_key(question, solves, proposal)
    assert result["patches"] == [] and result["unresolved"] is True


def test_requested_unit_does_not_create_a_false_numeric_key_change():
    from engine.cli import reconcile_blind_key
    question = next(q for q in QUESTIONS if q["_id"] == next(r["questionId"] for r in REPORTS if r["reportId"] == "R032"))
    solves = [{"answer": "8 cm", "sufficient_data": True}, {"answer": "8 cm", "sufficient_data": True}]
    proposal = {"verdict": "defect", "repair": "answer_key", "patches": [{"field": "answer", "find": "8", "replace": "8 cm"}],
        "unresolved": False, "evidence": "Wrong unit claim", "student_reply": "Review pending."}
    result = reconcile_blind_key(question, solves, proposal)
    assert result["verdict"] == "no_error" and result["repair"] is None and result["patches"] == []


def test_already_fixed_requires_matching_history_and_current_text():
    from engine.cli import reconcile_history
    question = next(q for q in QUESTIONS if q["_id"] == next(r["questionId"] for r in REPORTS if r["reportId"] == "R017"))
    report = next(r for r in REPORTS if r["reportId"] == "R017")
    proposal = {"verdict": "defect", "repair": "spelling", "patches": [], "unresolved": True,
        "evidence": "Model copied a prior typo", "student_reply": "Review pending."}
    result = reconcile_history(question, [report], proposal)
    assert result["verdict"] == "already_fixed" and result["repair"] is None
    assert result["patches"] == [] and result["unresolved"] is False


def test_conflicting_verdict_and_content_repair_cannot_escape_export_policy():
    from engine.cli import reconcile_taxonomy
    proposal = {"verdict": "display_issue", "repair": "markup_leak", "patches": [{"field": "question", "find": "x", "replace": "y"}],
        "unresolved": False, "evidence": "Inconsistent model output", "student_reply": "Change applied."}
    result = reconcile_taxonomy(proposal, TAXONOMY)
    assert result["verdict"] == "defect" and result["repair"] == "markup_leak"
    assert result["patches"] == [] and result["unresolved"] is True
    assert "No question change has been applied" in result["student_reply"]


def test_dry_run_reply_cannot_claim_a_change_was_completed():
    from engine.cli import reconcile_reply
    proposal = {"verdict": "defect", "student_reply": "Thanks, the spelling has been corrected."}
    result = reconcile_reply(proposal)
    assert "has been corrected" not in result["student_reply"]
    assert "no new question change has been applied" in result["student_reply"]
    fixed = {"verdict": "already_fixed", "student_reply": "The spelling has been corrected."}
    assert reconcile_reply(fixed)["student_reply"] == "The spelling has been corrected."


def test_two_blind_no_option_findings_block_key_only_repair():
    from engine.cli import reconcile_unanswerable
    solves = [{"answer": None, "sufficient_data": True,
        "derivation": "The provided options do not include both statements false."},
        {"answer": None, "sufficient_data": True,
        "derivation": "None of the provided options describes the result."}]
    proposal = {"verdict": "defect", "repair": "answer_key", "patches": [{"field": "answer", "find": "D", "replace": "A"}],
        "unresolved": False, "evidence": "Key seems wrong", "student_reply": "Key changed."}
    result = reconcile_unanswerable(solves, proposal)
    assert result["repair"] == "unsound" and result["patches"] == [] and result["unresolved"] is True


def test_combined_mcq_labels_are_normalized_without_settling_answer_dispute():
    from engine.cli import reconcile_mcq_storage
    question = next(q for q in QUESTIONS if q["_id"] == next(r["questionId"] for r in REPORTS if r["reportId"] == "R020"))
    proposal = {"verdict": "not_actionable", "repair": None, "patches": [], "unresolved": True,
        "evidence": "Solvers disagree", "student_reply": "Review pending."}
    result = reconcile_mcq_storage(question, [{"answer": ["A", "B", "D"]}, {"answer": ["A", "B", "C", "D"]}], proposal)
    assert result["verdict"] == "defect" and result["repair"] == "answer_key"
    assert result["patches"][0]["replace"] == ["A", "B", "D"] and result["unresolved"] is True
    assert not validate_proposal(question, result["verdict"], result["repair"], result["patches"], TAXONOMY)


def test_type_migration_proposes_dependent_key_change_atomically():
    from engine.cli import reconcile_mcq_storage
    question = next(q for q in QUESTIONS if q["_id"] == next(r["questionId"] for r in REPORTS if r["reportId"] == "R021"))
    proposal = {"verdict": "defect", "repair": "type_mismatch", "patches": [{"field": "questionType", "find": "mcq", "replace": "scq"}],
        "unresolved": False, "evidence": "Only B solves", "student_reply": "Review pending."}
    result = reconcile_mcq_storage(question, [{"answer": "B"}, {"answer": "B"}], proposal)
    assert len(result["patches"]) == 2 and result["unresolved"] is True
    assert not validate_proposal(question, result["verdict"], result["repair"], result["patches"], TAXONOMY)
