/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * Evidence Validator with Recursive INFERENCE DAG Traversal.
 *
 * Implements exact parity with Python reference kernel (sol_triad/validators.py:EvidenceValidator v0.4.1):
 *   - Temporal checks (evaluation time, future timestamps, staleness).
 *   - Primary evidence record lookup and cryptographic hash matching.
 *   - Recursive DFS traversal for INFERENCE chains.
 *   - Disjoint tracking of `visiting` (cycle detection) and `visited` (DAG memoization).
 *   - Enforcement of MAX_INFERENCE_DEPTH (64) and MAX_INFERENCE_NODES (1024).
 *   - Semantics: cycles -> FAIL, missing premise -> FAIL, limits/incomplete -> REVIEW.
 */

import {
  SourcePrimitive,
  EvidenceRecord,
  CoherenceVerdict,
  CoherenceDiagnostic,
  DiagnosticCode,
} from "../types/triad";

export interface EvidenceRegistryOracle {
  isAvailable(): boolean;
  getRecord(evidenceId: string): EvidenceRecord | null;
}

export class InMemoryEvidenceRegistry implements EvidenceRegistryOracle {
  private records: Map<string, EvidenceRecord> = new Map();
  private available: boolean = true;

  constructor(initialRecords?: Record<string, EvidenceRecord> | null) {
    if (initialRecords) {
      for (const [id, rec] of Object.entries(initialRecords)) {
        this.records.set(id, rec);
      }
    }
  }

  public register(record: EvidenceRecord): void {
    this.records.set(record.evidence_id, record);
  }

  public setAvailable(available: boolean): void {
    this.available = available;
  }

  public isAvailable(): boolean {
    return this.available;
  }

  public getRecord(evidenceId: string): EvidenceRecord | null {
    if (!this.available) return null;
    return this.records.get(evidenceId) ?? null;
  }
}

export class EvidenceValidator {
  public static readonly MAX_INFERENCE_DEPTH = 64;
  public static readonly MAX_INFERENCE_NODES = 1024;

  private registry: EvidenceRegistryOracle | null;
  private currentTimeSec: number;

  constructor(registry: EvidenceRegistryOracle | null, currentTimeSec: number) {
    this.registry = registry;
    this.currentTimeSec = currentTimeSec;
  }

  public validate(s: SourcePrimitive): [boolean, CoherenceVerdict, CoherenceDiagnostic[]] {
    const diagnostics: CoherenceDiagnostic[] = [];

    // 1. Temporal Bounds & Sanity
    if (isNaN(this.currentTimeSec) || !isFinite(this.currentTimeSec)) {
      diagnostics.push({
        code: "STATE_INVALID_NUMERIC",
        severity: "ERROR",
        message: `Evaluation time is non-finite: ${this.currentTimeSec}`,
        primitive: "SOURCE",
        field_name: "evaluation_time",
      });
      return [false, "FAIL", diagnostics];
    }

    if (isNaN(s.timestamp_sec) || !isFinite(s.timestamp_sec)) {
      diagnostics.push({
        code: "STATE_INVALID_NUMERIC",
        severity: "ERROR",
        message: `Source timestamp is non-finite: ${s.timestamp_sec}`,
        primitive: "SOURCE",
        field_name: "timestamp_sec",
      });
      return [false, "FAIL", diagnostics];
    }

    if (s.max_age_sec <= 0 || isNaN(s.max_age_sec) || !isFinite(s.max_age_sec)) {
      diagnostics.push({
        code: "TEMPORAL_INVALID_LIMIT",
        severity: "ERROR",
        message: `Source max_age_sec must be positive and finite: ${s.max_age_sec}`,
        primitive: "SOURCE",
        field_name: "max_age_sec",
      });
      return [false, "FAIL", diagnostics];
    }

    if (s.timestamp_sec > this.currentTimeSec) {
      diagnostics.push({
        code: "TEMPORAL_FUTURE",
        severity: "ERROR",
        message: `Source timestamp is in the future (${s.timestamp_sec.toFixed(2)} > current ${this.currentTimeSec.toFixed(2)})`,
        primitive: "SOURCE",
        field_name: "timestamp_sec",
      });
      return [false, "FAIL", diagnostics];
    }

    const age = this.currentTimeSec - s.timestamp_sec;
    if (age > s.max_age_sec) {
      diagnostics.push({
        code: "TEMPORAL_STALE",
        severity: "WARNING",
        message: `Evidence is stale: age ${age.toFixed(2)}s exceeds max_age_sec (${s.max_age_sec.toFixed(2)}s)`,
        primitive: "SOURCE",
        field_name: "timestamp_sec",
      });
      return [false, "REVIEW", diagnostics];
    }

    // 2. Registry Availability
    if (!this.registry || !this.registry.isAvailable()) {
      diagnostics.push({
        code: "REGISTRY_OFFLINE",
        severity: "WARNING",
        message: "Evidence registry is offline; cannot verify claim.",
        primitive: "SOURCE",
        field_name: "epistemic_type",
      });
      return [false, "REVIEW", diagnostics];
    }

    // 3. Primary Evidence Record Lookup
    const record = this.registry.getRecord(s.evidence_id);
    if (!record) {
      if (!this.registry.isAvailable()) {
        diagnostics.push({
          code: "REGISTRY_OFFLINE",
          severity: "WARNING",
          message: "Evidence registry became unavailable while looking up primary evidence.",
          primitive: "SOURCE",
          field_name: "evidence_id",
        });
        return [false, "REVIEW", diagnostics];
      }
      diagnostics.push({
        code: "EVIDENCE_NOT_FOUND",
        severity: "ERROR",
        message: `Primary evidence ID '${s.evidence_id}' not found in registry.`,
        primitive: "SOURCE",
        field_name: "evidence_id",
      });
      return [false, "FAIL", diagnostics];
    }

    if (record.evidence_id !== s.evidence_id) {
      diagnostics.push({
        code: "EVIDENCE_MISMATCH",
        severity: "ERROR",
        message: `Registry returned evidence ID '${record.evidence_id}' for requested ID '${s.evidence_id}'.`,
        primitive: "SOURCE",
        field_name: "evidence_id",
      });
      return [false, "FAIL", diagnostics];
    }

    if (isNaN(record.timestamp_sec) || !isFinite(record.timestamp_sec)) {
      diagnostics.push({
        code: "STATE_INVALID_NUMERIC",
        severity: "ERROR",
        message: `Registry record '${record.evidence_id}' has non-finite timestamp.`,
        primitive: "SOURCE",
        field_name: "timestamp_sec",
      });
      return [false, "FAIL", diagnostics];
    }

    if (record.timestamp_sec > this.currentTimeSec) {
      diagnostics.push({
        code: "TEMPORAL_FUTURE",
        severity: "ERROR",
        message: `Registry record '${record.evidence_id}' has future timestamp (${record.timestamp_sec.toFixed(2)} > ${this.currentTimeSec.toFixed(2)})`,
        primitive: "SOURCE",
        field_name: "evidence_id",
      });
      return [false, "FAIL", diagnostics];
    }

    if (Math.abs(record.timestamp_sec - s.timestamp_sec) > 1e-6) {
      diagnostics.push({
        code: "EVIDENCE_TIMESTAMP_MISMATCH",
        severity: "ERROR",
        message: `Source timestamp ${s.timestamp_sec.toFixed(2)} does not match registry timestamp ${record.timestamp_sec.toFixed(2)} for evidence '${s.evidence_id}'.`,
        primitive: "SOURCE",
        field_name: "timestamp_sec",
      });
      return [false, "FAIL", diagnostics];
    }

    // 4. Epistemic Alignment
    if (record.epistemic_status !== s.epistemic_type) {
      diagnostics.push({
        code: "EVIDENCE_MISMATCH",
        severity: "ERROR",
        message: `Source claims ${s.epistemic_type}, but registry records status as ${record.epistemic_status}.`,
        primitive: "SOURCE",
        field_name: "epistemic_type",
      });
      return [false, "FAIL", diagnostics];
    }

    // 5. Domain Applicability
    if (s.authority_domain && !s.authority_domain.includes(record.domain)) {
      diagnostics.push({
        code: "EVIDENCE_DOMAIN_MISMATCH",
        severity: "ERROR",
        message: `Evidence domain '${record.domain}' is not within claimed authority [${s.authority_domain.join(", ")}].`,
        primitive: "SOURCE",
        field_name: "authority_domain",
      });
      return [false, "FAIL", diagnostics];
    }

    // 6. Explicit Cryptographic Payload Hash Verification (Symmetric)
    if (s.payload_hash && !record.payload_hash) {
      diagnostics.push({
        code: "EVIDENCE_HASH_MISSING_IN_REGISTRY",
        severity: "ERROR",
        message: `Source supplied payload_hash '${s.payload_hash}', but registry record '${s.evidence_id}' lacks a payload_hash for verification.`,
        primitive: "SOURCE",
        field_name: "payload_hash",
      });
      return [false, "FAIL", diagnostics];
    }

    if (record.payload_hash && !s.payload_hash) {
      diagnostics.push({
        code: "EVIDENCE_HASH_REQUIRED_BY_REGISTRY",
        severity: "ERROR",
        message: `Registry record '${s.evidence_id}' requires payload_hash verification, but Source omitted payload_hash.`,
        primitive: "SOURCE",
        field_name: "payload_hash",
      });
      return [false, "FAIL", diagnostics];
    }

    if (s.payload_hash && record.payload_hash && s.payload_hash !== record.payload_hash) {
      diagnostics.push({
        code: "EVIDENCE_PAYLOAD_MISMATCH",
        severity: "ERROR",
        message: `Payload hash mismatch for evidence '${s.evidence_id}': '${s.payload_hash}' != '${record.payload_hash}'.`,
        primitive: "SOURCE",
        field_name: "payload_hash",
      });
      return [false, "FAIL", diagnostics];
    }

    // 7. INFERENCE provenance verification with Recursive DFS
    if (s.epistemic_type === "INFERENCE") {
      const chainVerdict = this.validateInferenceChain(s, record, diagnostics);
      if (chainVerdict !== null) {
        return [chainVerdict === "PASS", chainVerdict, diagnostics];
      }
    }

    diagnostics.push({
      code: "EVIDENCE_PASS",
      severity: "INFO",
      message: "Evidence verified against authoritative registry.",
      primitive: "SOURCE",
    });
    return [true, "PASS", diagnostics];
  }

  /**
   * Recursively validates the provenance DAG of an INFERENCE claim.
   * Mirrors sol_triad/validators.py:_validate_inference_chain v0.4.1
   */
  private validateInferenceChain(
    source: SourcePrimitive,
    rootRecord: EvidenceRecord,
    diagnostics: CoherenceDiagnostic[]
  ): CoherenceVerdict | null {
    const registeredRootPremises = rootRecord.corroborating_evidence_ids;
    const sourcePremises = source.corroborating_evidence_ids;

    // Must have registered premises
    if (!registeredRootPremises || !Array.isArray(registeredRootPremises)) {
      diagnostics.push({
        code: "INFERENCE_CHAIN_INCOMPLETE",
        severity: "WARNING",
        message: `Inference record '${rootRecord.evidence_id}' has no registered premise list.`,
        primitive: "SOURCE",
        field_name: "corroborating_evidence_ids",
      });
      return "REVIEW";
    }

    // Source must supply valid premise array
    if (!sourcePremises || !Array.isArray(sourcePremises) || sourcePremises.some((p) => typeof p !== "string" || !p)) {
      diagnostics.push({
        code: "EVIDENCE_MISMATCH",
        severity: "ERROR",
        message: "SOURCE inference premises must be a list of non-empty evidence IDs.",
        primitive: "SOURCE",
        field_name: "corroborating_evidence_ids",
      });
      return "FAIL";
    }

    // Check set equality between source premises and registry root premises
    const sourceSet = new Set(sourcePremises);
    const regSet = new Set(registeredRootPremises);
    if (sourceSet.size !== regSet.size || ![...sourceSet].every((id) => regSet.has(id))) {
      diagnostics.push({
        code: "EVIDENCE_MISMATCH",
        severity: "ERROR",
        message: `SOURCE premises for '${source.evidence_id}' do not match the registry record.`,
        primitive: "SOURCE",
        field_name: "corroborating_evidence_ids",
      });
      return "FAIL";
    }

    if (registeredRootPremises.length === 0) {
      diagnostics.push({
        code: "INFERENCE_UNSUPPORTED",
        severity: "WARNING",
        message: "Inference record has no corroborating premises; requires epistemic review.",
        primitive: "SOURCE",
        field_name: "corroborating_evidence_ids",
      });
      return "REVIEW";
    }

    // DFS Traversal State
    const visiting = new Set<string>([rootRecord.evidence_id]);
    const visited = new Set<string>();
    let nodeCount = 1;

    const report = (
      code: DiagnosticCode,
      severity: "ERROR" | "WARNING",
      message: string,
      verdict: CoherenceVerdict
    ): CoherenceVerdict => {
      diagnostics.push({
        code,
        severity,
        message,
        primitive: "SOURCE",
        field_name: "corroborating_evidence_ids",
      });
      return verdict;
    };

    const visit = (evidenceId: string, depth: number): CoherenceVerdict | null => {
      // 1. Cycle detection in current path
      if (visiting.has(evidenceId)) {
        return report(
          "INFERENCE_CIRCULAR_DEPENDENCY",
          "ERROR",
          `Circular inference dependency detected at evidence '${evidenceId}'.`,
          "FAIL"
        );
      }

      // 2. Depth limit check
      if (depth > EvidenceValidator.MAX_INFERENCE_DEPTH) {
        return report(
          "INFERENCE_TRAVERSAL_LIMIT_EXCEEDED",
          "WARNING",
          `Inference graph exceeds maximum depth of ${EvidenceValidator.MAX_INFERENCE_DEPTH}.`,
          "REVIEW"
        );
      }

      // 3. Skip already fully validated subtrees (memoized DAG join)
      if (visited.has(evidenceId)) {
        return null;
      }

      // 4. Node count limit check
      if (nodeCount >= EvidenceValidator.MAX_INFERENCE_NODES) {
        return report(
          "INFERENCE_TRAVERSAL_LIMIT_EXCEEDED",
          "WARNING",
          `Inference graph exceeds maximum of ${EvidenceValidator.MAX_INFERENCE_NODES} records.`,
          "REVIEW"
        );
      }

      if (!this.registry || !this.registry.isAvailable()) {
        return report(
          "REGISTRY_OFFLINE",
          "WARNING",
          "Evidence registry became unavailable while validating inference premises.",
          "REVIEW"
        );
      }

      const rec = this.registry.getRecord(evidenceId);
      if (!rec) {
        if (!this.registry.isAvailable()) {
          return report(
            "REGISTRY_OFFLINE",
            "WARNING",
            "Evidence registry became unavailable while validating inference premises.",
            "REVIEW"
          );
        }
        return report(
          "EVIDENCE_NOT_FOUND",
          "ERROR",
          `Corroborating evidence ID '${evidenceId}' not found in registry.`,
          "FAIL"
        );
      }

      if (rec.evidence_id !== evidenceId) {
        return report(
          "EVIDENCE_MISMATCH",
          "ERROR",
          `Registry returned evidence ID '${rec.evidence_id}' for requested premise '${evidenceId}'.`,
          "FAIL"
        );
      }

      if (rec.epistemic_status !== "FACT" && rec.epistemic_status !== "INFERENCE") {
        return report(
          "INFERENCE_PREMISE_INVALID_STATUS",
          "ERROR",
          `Premise '${evidenceId}' has invalid epistemic status '${rec.epistemic_status}'; must be FACT or verified INFERENCE.`,
          "FAIL"
        );
      }

      if (isNaN(rec.timestamp_sec) || !isFinite(rec.timestamp_sec)) {
        return report(
          "STATE_INVALID_NUMERIC",
          "ERROR",
          `Premise '${evidenceId}' has a non-finite timestamp.`,
          "FAIL"
        );
      }

      if (rec.timestamp_sec > this.currentTimeSec) {
        return report(
          "TEMPORAL_FUTURE",
          "ERROR",
          `Premise '${evidenceId}' has a future timestamp (${rec.timestamp_sec.toFixed(2)} > ${this.currentTimeSec.toFixed(2)}).`,
          "FAIL"
        );
      }

      if (this.currentTimeSec - rec.timestamp_sec > source.max_age_sec) {
        return report(
          "TEMPORAL_STALE",
          "WARNING",
          `Premise '${evidenceId}' is stale; age exceeds max_age_sec (${source.max_age_sec.toFixed(2)}s).`,
          "REVIEW"
        );
      }

      if (source.authority_domain && !source.authority_domain.includes(rec.domain)) {
        return report(
          "EVIDENCE_DOMAIN_MISMATCH",
          "ERROR",
          `Premise '${evidenceId}' domain '${rec.domain}' is outside SOURCE authority.`,
          "FAIL"
        );
      }

      nodeCount++;
      visiting.add(evidenceId);

      if (rec.epistemic_status === "INFERENCE") {
        const premises = rec.corroborating_evidence_ids;
        if (!premises || !Array.isArray(premises) || premises.length === 0) {
          return report(
            "INFERENCE_CHAIN_INCOMPLETE",
            "WARNING",
            `Inference record '${evidenceId}' has no registered premise list.`,
            "REVIEW"
          );
        }

        for (const premiseId of [...premises].sort()) {
          const res = visit(premiseId, depth + 1);
          if (res !== null) {
            return res;
          }
        }
      }

      visiting.delete(evidenceId);
      visited.add(evidenceId);
      return null;
    };

    for (const premiseId of [...registeredRootPremises].sort()) {
      const res = visit(premiseId, 1);
      if (res !== null) {
        return res;
      }
    }

    return null;
  }
}
