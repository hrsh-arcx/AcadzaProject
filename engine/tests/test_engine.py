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
