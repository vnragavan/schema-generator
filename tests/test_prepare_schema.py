import sys
import os
import json
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch

# Set up path to import schema_toolkit
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema_toolkit.prepare_schema import main, _merge_constraints

def test_guid_no_leak(tmp_path):
    """Bug 1 User: GUID columns silently leak identifiers."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    
    df = pd.DataFrame({
        "id": ["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"],
        "target": [0, 1]
    })
    df.to_csv(csv_file, index=False)
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--infer-categories", "--target-col", "target"]):
        main()
        
    schema = json.loads(out_file.read_text())
    assert schema["column_types"]["id"] == "categorical"
    assert "id" in schema["provenance"]["guid_like_columns"]
    # Ensure no domain leak
    assert "id" not in schema.get("public_categories", {})

def test_boolean_consistency(tmp_path):
    """Bug 2 User: Boolean columns produce inconsistent output depending on flag order."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    
    df = pd.DataFrame({
        "is_active": [True, False, True],
        "target": [0, 1, 0]
    })
    df.to_csv(csv_file, index=False)
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--target-col", "target"]):
        main()
        
    schema = json.loads(out_file.read_text())
    assert schema["column_types"]["is_active"] == "ordinal"
    # Should contain ["0", "1"] even without infer_binary_domain
    assert schema["public_categories"]["is_active"] == ["0", "1"]
    assert "is_active" not in schema.get("public_bounds", {})

def test_no_publish_label_domain(tmp_path):
    """Bug 3 User: label_domain cannot be suppressed and always leaks into public_categories."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    
    df = pd.DataFrame({
        "feature": [1, 2, 3],
        "target": ["classA", "classB", "classA"]
    })
    df.to_csv(csv_file, index=False)
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--target-col", "target", "--no-publish-label-domain"]):
        main()
        
    schema = json.loads(out_file.read_text())
    assert schema["label_domain"] == []
    assert "target" not in schema.get("public_categories", {})

def test_target_column_mutilation(tmp_path):
    """Bug 1 Me: Target Column Mutilation (target skipped causing missing numeric bounds)."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    
    df = pd.DataFrame({
        "feature": [1, 2, 3],
        "income": [50000, 60000, 75000]
    })
    df.to_csv(csv_file, index=False)
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--target-col", "income"]):
        main()
        
    schema = json.loads(out_file.read_text())
    assert schema.get("target_col") == "income"
    assert "income" in schema["public_bounds"]
    assert schema["column_types"]["income"] in ["integer", "continuous"]

def test_datetime_binary_coercion(tmp_path):
    """Bug 3 Me: Datetime Binary Coercion Conflict (Datetime integer types transformed into ordinals)."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    
    df = pd.DataFrame({
        "time": ["2023-01-01", "2023-01-02", "2023-01-01"],
        "target": [0, 1, 0]
    })
    df.to_csv(csv_file, index=False)
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--infer-datetimes", "--infer-binary-domain", "--target-col", "target"]):
        main()
        
    schema = json.loads(out_file.read_text())
    assert schema["column_types"]["time"] == "integer"
    assert "time" in schema["datetime_spec"]
    assert schema["column_types"]["time"] != "ordinal"

def test_silent_swallow_survival(tmp_path):
    """Bug 5 Me: Silent Swallow on Partial Survival Flags."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    
    df = pd.DataFrame({"event": [1, 0], "other": [1, 2]})
    df.to_csv(csv_file, index=False)
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--survival-event-col", "event"]):
        with pytest.raises(SystemExit):
            main()

def test_datetime_overrides_lose_metadata(tmp_path):
    """Bug 2 Me: Datetime Overrides Lose Metadata."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    types_file = tmp_path / "types.json"
    
    df = pd.DataFrame({
        "time": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "target": [1, 0, 1]
    })
    df.to_csv(csv_file, index=False)
    types_file.write_text(json.dumps({"time": {"type": "continuous"}}))
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--column-types", str(types_file), "--infer-datetimes", "--target-col", "target"]):
        main()
        
    schema = json.loads(out_file.read_text())
    assert schema["column_types"]["time"] == "continuous"
    assert "time" in schema["datetime_spec"]

def test_merge_constraints():
    """Bug 4 Me: Constraint Dictionary Reference Mutation."""
    base = {
        "column_constraints": {"colA": {"min": 0}},
        "cross_column_constraints": [],
        "row_group_constraints": []
    }
    user = {
        "column_constraints": {"colA": {"max": 10}},
        "cross_column_constraints": [{"type": "foo"}],
        "row_group_constraints": []
    }
    import copy
    base_copy = copy.deepcopy(base)
    merged = _merge_constraints(base, user)
    
    assert merged["column_constraints"]["colA"] == {"min": 0, "max": 10}
    assert base == base_copy # ensures base was not mutated

def test_six_class_medical_constraints(tmp_path):
    """Test standardizing the 6 core medical constraints vocabularies."""
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    constraints_file = tmp_path / "constraints.json"
    
    df = pd.DataFrame({"target": [1, 2]})
    df.to_csv(csv_file, index=False)
    
    medical_constraints = {
        "column_constraints": {
            "icd_10_code": {"constraint_class": "RegexMatch"}
        },
        "cross_column_constraints": [
            {"constraint_class": "Inequality"},
            {"constraint_class": "FixedCombinations"},
            {"constraint_class": "CompositionalSum"},
            {"constraint_class": "PiecewiseBounds"}
        ],
        "row_group_constraints": [
            {"constraint_class": "MonotonicOrdering"}
        ]
    }
    constraints_file.write_text(json.dumps(medical_constraints))
    
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--constraints-file", str(constraints_file)]):
        main()
        
    schema = json.loads(out_file.read_text())
    # Validate merging logic successfully captured all dictionaries 
    assert schema["constraints"]["column_constraints"]["icd_10_code"]["constraint_class"] == "RegexMatch"
    assert len(schema["constraints"]["cross_column_constraints"]) == 4
    assert schema["constraints"]["row_group_constraints"][0]["constraint_class"] == "MonotonicOrdering"

def test_label_domain_combinatorics(tmp_path):
    """Test downstream label_domain utility mechanics natively mapping multiple target types."""
    import json
    csv_file = tmp_path / "data.csv"
    out_file = tmp_path / "out.json"
    spec_file = tmp_path / "spec.json"
    
    # 1. Base Multi-Class Integer Dataset
    df = pd.DataFrame({
        "age": [45, 62, 33, 71, 55],
        "outcome": [0, 1, 2, 3, 0],
        "time": [100, 50, 200, 10, 80]
    })
    df.to_csv(csv_file, index=False)
    
    # Scenario A: Standard Integer Target -> Continuous Utility Metrics
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--target-col", "outcome"]):
        main()
    schema_a = json.loads(out_file.read_text())
    assert schema_a["column_types"]["outcome"] == "integer"
    assert schema_a["label_domain"] == []
    
    # Scenario B: Forced Classification Escape Hatch -> Machine Learning Efficacy
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--target-col", "outcome", "--target-is-classifier"]):
        main()
    schema_b = json.loads(out_file.read_text())
    assert schema_b["column_types"]["outcome"] == "integer"
    assert schema_b["label_domain"] == ["0", "1", "2", "3"]
    assert schema_b["public_categories"]["outcome"] == ["0", "1", "2", "3"]
    
    # Scenario C: Survival Pair Target -> Bypass Classification
    spec = {"targets": ["outcome", "time"], "kind": "survival_pair"}
    spec_file.write_text(json.dumps(spec))
    with patch("sys.argv", ["prepare_schema.py", "--data", str(csv_file), "--out", str(out_file), "--target-spec-file", str(spec_file)]):
        main()
    schema_c = json.loads(out_file.read_text())
    assert schema_c["target_spec"]["kind"] == "survival_pair"
    assert schema_c["column_types"]["outcome"] == "ordinal"
    assert schema_c["label_domain"] == [] # Downstream evaluates via C-Index
    assert schema_c["public_categories"]["outcome"] == ["0", "1"] # Bounds preserved uniquely
