"""
Python Runner for Cross-Implementation Consistency Test.
Runs reference kernel SOL-Triad-Engine v0.4.1 against all fixtures.
Outputs: cross-implementation/python_runner/python_results.json
"""

import json
import os
import sys

# Ensure v2-reference is in sys.path
sys.path.insert(0, os.path.abspath("v2-reference"))

from sol_triad.adapter import SolTriadJsonAdapter
from sol_triad.evidence import InMemoryEvidenceRegistry
from sol_triad.models import EvidenceRecord, EpistemicStatus


def run_fixtures():
    fixtures_path = os.path.abspath("cross-implementation/fixtures/fixtures.json")
    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    results = []

    for f in fixtures:
        fid = f["id"]
        group = f["group"]
        name = f["name"]
        eval_time = f.get("evaluation_time")
        raw_records = f.get("registry_records", [])

        # Build Host Registry Oracle
        registry = InMemoryEvidenceRegistry()
        for rec in raw_records:
            corrob = set(rec["corroborating_evidence_ids"]) if "corroborating_evidence_ids" in rec and rec["corroborating_evidence_ids"] is not None else None
            registry.register(EvidenceRecord(
                evidence_id=rec["evidence_id"],
                domain=rec["domain"],
                epistemic_status=EpistemicStatus(rec["epistemic_status"]),
                timestamp_sec=rec["timestamp_sec"],
                payload_hash=rec.get("payload_hash"),
                corroborating_evidence_ids=corrob
            ))

        adapter = SolTriadJsonAdapter(default_registry=registry)
        req_payload = f["request"]

        try:
            resp = adapter.evaluate_json(req_payload, evaluation_time=eval_time)
        except Exception as ex:
            resp = {
                "error": "EXECUTION_EXCEPTION",
                "message": str(ex),
                "type": type(ex).__name__
            }

        results.append({
            "id": fid,
            "group": group,
            "name": name,
            "response": resp
        })

    out_dir = os.path.abspath("cross-implementation/python_runner")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "python_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Python runner completed {len(results)} fixtures -> {out_path}")


if __name__ == "__main__":
    run_fixtures()
