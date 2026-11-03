"""Pre-SOL Engine v0.1: Main entry point for autonomous Task Framing.

Coordinates proposition extraction, dual-axis classification,
epistemic/physical diagnostics, and readiness evaluation.
"""

import hashlib
import time
from typing import Dict, Any, Optional
from .models import TaskFramingReport
from .classifier import StatementClassifier
from .diagnostics import DiagnosticAnalyzer
from .evaluator import PreSolEvaluator
from .hash_chain import DiagnosticHashChain


class PreSolEngine:
    """Autonomous Pre-SOL Task Framing Engine."""

    def __init__(
        self,
        classifier: Optional[StatementClassifier] = None,
        analyzer: Optional[DiagnosticAnalyzer] = None,
        evaluator: Optional[PreSolEvaluator] = None,
    ):
        self.classifier = classifier or StatementClassifier()
        self.analyzer = analyzer or DiagnosticAnalyzer()
        self.evaluator = evaluator or PreSolEvaluator()

    def analyze(
        self,
        raw_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskFramingReport:
        """Analyzes a raw query and generates a structured TaskFramingReport.

        Guarantees:
        - raw_query is retained byte-for-byte unmodified.
        - Safety barrier is never DISENGAGED or AUTHORIZED.
        - Dual-axis classification is applied to all propositions.
        - No mock evidence records are generated.
        - Every diagnostic stage is sealed in an immutable SHA-256 hash chain.
        """
        chain = DiagnosticHashChain()
        current_time = time.time()

        # Step 0: Ingest raw query (TSK Step 1: Observed fact)
        chain.append(
            step_name="TSK_STEP_1_RAW_QUERY_INGEST",
            payload={
                "raw_query_sha256": hashlib.sha256(raw_query.encode("utf-8")).hexdigest(),
                "byte_length": len(raw_query.encode("utf-8")),
            },
            timestamp=current_time,
        )

        # 1. Parse and classify statements (TSK Step 3: Labels and Epistemic Roles)
        statements = self.classifier.extract_and_classify(raw_query, context)
        chain.append(
            step_name="TSK_STEP_3_STATEMENT_EXTRACTION",
            payload={
                "statement_count": len(statements),
                "statements": [
                    {
                        "id": s.id,
                        "statement_type": s.statement_type.value,
                        "grounding_source": s.grounding_source.value,
                        "raw_fragment_sha256": hashlib.sha256(s.raw_fragment.encode("utf-8")).hexdigest(),
                    }
                    for s in statements
                ],
            },
            timestamp=current_time,
        )

        # 2. Run diagnostic checks (TSK Step 4: Contradiction & Interval Verification)
        findings = self.analyzer.analyze(statements, raw_query)
        chain.append(
            step_name="TSK_STEP_4_CONTRADICTION_ANALYSIS",
            payload={
                "finding_count": len(findings),
                "findings": [
                    {
                        "code": f.code.value,
                        "severity": f.severity.value,
                        "related_statement_ids": sorted(f.related_statement_ids),
                    }
                    for f in findings
                ],
            },
            timestamp=current_time,
        )

        # 3. Evaluate readiness and safety barrier (TSK Step 5 & 6: Conserved Axis & Verifiable Step)
        (
            analysis_readiness,
            formalization_readiness,
            safety_barrier_state,
            mutation_requested,
            clarification_questions,
            summary_explanation,
            provisional_flags,
        ) = self.evaluator.evaluate(raw_query, statements, findings)

        chain.append(
            step_name="TSK_STEP_5_6_READINESS_AND_BARRIER_EVALUATION",
            payload={
                "analysis_readiness": analysis_readiness.value,
                "formalization_readiness": formalization_readiness.value,
                "safety_barrier_state": safety_barrier_state.value,
                "mutation_requested": mutation_requested,
            },
            timestamp=current_time,
        )

        # 4. Clarification questions dispatch (TSK Step 7: Human/AI Role Partition)
        chain.append(
            step_name="TSK_STEP_7_CLARIFICATION_DISPATCH",
            payload={
                "questions_count": len(clarification_questions),
                "questions": [q.id for q in clarification_questions],
                "provisional_flags": sorted(provisional_flags),
            },
            timestamp=current_time,
        )

        # 5. Construct and return final report with sealed audit trail
        return TaskFramingReport(
            raw_query=raw_query,  # Exact byte preservation
            analysis_readiness=analysis_readiness,
            formalization_readiness=formalization_readiness,
            safety_barrier_state=safety_barrier_state,
            mutation_requested=mutation_requested,
            statements=statements,
            findings=findings,
            clarification_questions=clarification_questions,
            summary_explanation=summary_explanation,
            provisional_flags=provisional_flags,
            audit_trail=chain.export_audit_trail(),
            audit_trail_hash=chain.head_hash,
        )
