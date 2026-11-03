import {
  SourcePrimitive,
  ConstraintPrimitive,
  DissipatePrimitive,
  SystemState,
  EvidenceRecord,
  EvaluationReport,
  CoherenceVerdict,
  CoherenceDiagnostic,
} from "../types/triad";

import { EvidenceValidator, InMemoryEvidenceRegistry, EvidenceRegistryOracle } from "./evidenceValidator";
import { ScopeValidator } from "./scopeValidator";
import { StateValidator } from "./stateValidator";

export function evaluateTriad(
  s: SourcePrimitive,
  c: ConstraintPrimitive,
  d: DissipatePrimitive,
  initialState: SystemState,
  registry: Record<string, EvidenceRecord> | EvidenceRegistryOracle | null,
  evaluationTime: number
): EvaluationReport {
  const diagnostics: CoherenceDiagnostic[] = [];
  let evVerdict: CoherenceVerdict = "PASS";
  let scVerdict: CoherenceVerdict = "PASS";
  let stVerdict: CoherenceVerdict = "PASS";

  // --- 1. Evidence Grounding (EvidenceValidator v0.4.1) ---
  const oracle =
    registry && "getRecord" in registry
      ? (registry as EvidenceRegistryOracle)
      : registry
      ? new InMemoryEvidenceRegistry(registry as Record<string, EvidenceRecord>)
      : null;
  const evidenceValidator = new EvidenceValidator(oracle, evaluationTime);
  const [, evVerdictRaw, evDiags] = evidenceValidator.validate(s);
  evVerdict = evVerdictRaw;
  diagnostics.push(...evDiags);

  // --- 2. Scope & Authority (ScopeValidator v0.4.1) ---
  const scopeValidator = new ScopeValidator();
  const [, scVerdictRaw, scDiags] = scopeValidator.validate(s, c, d);
  scVerdict = scVerdictRaw;
  diagnostics.push(...scDiags);

  // --- 3. State & Invariants Simulation (StateValidator v0.4.1) ---
  const stateValidator = new StateValidator();
  const [, stVerdictRaw, stDiags, simulatedValues, simulatedFlags] = stateValidator.validate(
    c,
    d,
    initialState
  );
  stVerdict = stVerdictRaw;
  diagnostics.push(...stDiags);

  // --- Pairwise Synthesis (Exact Parity with sol_triad/engine.py v0.4.1) ---
  // P_SC: Grounding + Domain Scope + Target Objects
  const pScDiags = [...evDiags, ...scDiags].filter(
    (diag) =>
      (diag.primitive === "SOURCE" || diag.primitive === "CONSTRAINT") &&
      [
        "evidence_id",
        "epistemic_type",
        "authority_domain",
        "granted_scope",
        "domain_scope",
        "target_objects",
        "timestamp_sec",
        "max_age_sec",
        "corroborating_evidence_ids",
      ].includes(diag.field_name || "")
  );
  const pScFail =
    evVerdict === "FAIL" ||
    scDiags.some(
      (d) =>
        d.code === "SCOPE_EXCEEDED_DOMAIN" ||
        d.code === "SCOPE_EXCEEDED_OBJECTS" ||
        d.code === "SCOPE_DEFECT_NONE"
    );
  const pScReview = evVerdict === "REVIEW";
  const pScVerdict: CoherenceVerdict = pScFail ? "FAIL" : pScReview ? "REVIEW" : "PASS";

  // P_SD: Loss Domain Authority
  const pSdDiags = scDiags.filter(
    (diag) =>
      diag.code.includes("LOSS") ||
      diag.field_name === "granted_loss_domains" ||
      diag.field_name === "loss_domain"
  );
  const pSdFail = scDiags.some(
    (d) => d.code === "SCOPE_EXCEEDED_LOSS" || d.code === "SCOPE_DEFECT_NONE"
  );
  const pSdVerdict: CoherenceVerdict = pSdFail ? "FAIL" : "PASS";

  // P_CD: State Mutation & Invariant Integrity (Pure stDiags)
  const pCdVerdict = stVerdict;
  const pCdDiags = stDiags;

  // Final Verdict Arbitration
  const verdicts = [evVerdict, scVerdict, stVerdict];
  let finalVerdict: CoherenceVerdict = "PASS";
  if (verdicts.includes("FAIL")) {
    finalVerdict = "FAIL";
  } else if (verdicts.includes("REVIEW")) {
    finalVerdict = "REVIEW";
  }

  return {
    verdict: finalVerdict,
    engine_version: "0.4.1",
    timestamp_sec: evaluationTime,
    pairwise_checks: {
      P_SC: {
        relationship: "P_SC: SOURCE <-> CONSTRAINT (Grounding & Authority)",
        is_valid: pScVerdict === "PASS",
        verdict: pScVerdict,
        diagnostics: pScDiags,
      },
      P_CD: {
        relationship: "P_CD: CONSTRAINT <-> DISSIPATE (State Invariant Integrity)",
        is_valid: pCdVerdict === "PASS",
        verdict: pCdVerdict,
        diagnostics: pCdDiags,
      },
      P_SD: {
        relationship: "P_SD: SOURCE <-> DISSIPATE (Loss Domain Authority)",
        is_valid: pSdVerdict === "PASS",
        verdict: pSdVerdict,
        diagnostics: pSdDiags,
      },
    },
    diagnostics,
    simulated_values: simulatedValues,
    simulated_flags: simulatedFlags,
    messages: diagnostics.map((d) => `[${d.code}] ${d.message}`),
  };
}
