/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * JSON Adapter and Strict Schema Validation.
 *
 * Implements exact parity with Python reference kernel:
 *   (sol_triad/adapter.py:SolTriadJsonAdapter v0.4.1 conforming to JSON protocol v0.4.0)
 *
 * Enforces:
 *   - Strict JSON Schema validation matching sol_triad_request.schema.json and sol_triad_response.schema.json
 *   - Fail-closed behavior on structural defects, malformed JSON, and unexpected types
 *   - Rejection of inline evidence_records (UNTRUSTED_EVIDENCE_SOURCE) - host oracle is external
 *   - Preservation of semantic difference between null (structural defect) and [] (zero privileges)
 *   - Pure isolation of schema errors (STRUCTURAL_DEFECT) vs runtime state failures
 */

import {
  SourcePrimitive,
  ConstraintPrimitive,
  DissipatePrimitive,
  SystemState,
  EpistemicStatus,
  DiagnosticCode,
  EvaluationReport,
  EvidenceRecord,
} from "../types/triad";
import { evaluateTriad } from "./engineService";
import { EvidenceRegistryOracle, InMemoryEvidenceRegistry } from "./evidenceValidator";

export class SolTriadJsonAdapter {
  public static readonly PROTOCOL_VERSION = "0.4.0";
  public static readonly SUPPORTED_VERSIONS = new Set(["0.4.0"]);

  private defaultRegistry: EvidenceRegistryOracle | null;

  constructor(defaultRegistry?: EvidenceRegistryOracle | null) {
    this.defaultRegistry = defaultRegistry ?? null;
  }

  public evaluateJson(
    requestInput: unknown,
    registry?: EvidenceRegistryOracle | Record<string, EvidenceRecord> | null,
    evaluationTime?: unknown
  ): Record<string, unknown> {
    let currentTs = Date.now() / 1000;

    if (evaluationTime !== undefined && evaluationTime !== null) {
      try {
        currentTs = this._number(evaluationTime, "evaluation_time");
      } catch (ex) {
        return this._createFailResponse(
          "invalid_evaluation_time",
          (ex as Error).message,
          "STRUCTURAL_DEFECT",
          null,
          "evaluation_time",
          currentTs
        );
      }
    }

    let requestId = "unknown_request";
    let data: unknown;

    // 1. Parse JSON if string
    if (typeof requestInput === "string") {
      try {
        data = JSON.parse(requestInput);
      } catch (e) {
        return this._createFailResponse(
          "malformed_json",
          `JSON decoding failure: ${(e as Error).message}`,
          "STRUCTURAL_DEFECT",
          null,
          null,
          currentTs
        );
      }
    } else if (typeof requestInput === "object" && requestInput !== null) {
      data = requestInput;
    } else {
      return this._createFailResponse(
        "invalid_input_type",
        `Expected JSON string or object, got ${typeof requestInput}`,
        "STRUCTURAL_DEFECT",
        null,
        null,
        currentTs
      );
    }

    if (typeof data !== "object" || data === null || Array.isArray(data)) {
      return this._createFailResponse(
        "invalid_request_shape",
        "The JSON request must be an object",
        "STRUCTURAL_DEFECT",
        null,
        null,
        currentTs
      );
    }

    const reqObj = data as Record<string, unknown>;

    // Security Gate: inline evidence_records are forbidden and untrusted
    if ("evidence_records" in reqObj) {
      let untrustedRequestId = reqObj["request_id"];
      if (typeof untrustedRequestId !== "string" || !untrustedRequestId.trim()) {
        untrustedRequestId = "untrusted_evidence_request";
      }
      return this._createFailResponse(
        untrustedRequestId as string,
        "Inline evidence_records are not trusted. Register evidence in a host-controlled EvidenceRegistryOracle instead.",
        "UNTRUSTED_EVIDENCE_SOURCE",
        null,
        "evidence_records",
        currentTs
      );
    }

    // 2. Extract request_id
    const rawRequestId = reqObj["request_id"];
    if (typeof rawRequestId !== "string" || !rawRequestId.trim()) {
      return this._createFailResponse(
        "missing_request_id",
        "Field 'request_id' is required and must be a non-empty string",
        "STRUCTURAL_DEFECT",
        null,
        null,
        currentTs
      );
    }
    requestId = rawRequestId;

    try {
      this._validateKeys(
        reqObj,
        new Set([
          "request_id",
          "protocol_version",
          "engine_version",
          "evaluation_context",
          "source",
          "constraint",
          "dissipate",
          "initial_state",
        ]),
        new Set(),
        "request"
      );
    } catch (ex) {
      return this._createFailResponse(
        requestId,
        (ex as Error).message,
        "STRUCTURAL_DEFECT",
        null,
        null,
        currentTs
      );
    }

    // 3. Validate Protocol Version
    const protoVer = reqObj["protocol_version"];
    if (typeof protoVer !== "string" || !SolTriadJsonAdapter.SUPPORTED_VERSIONS.has(protoVer)) {
      return this._createFailResponse(
        requestId,
        `Unsupported protocol_version '${protoVer}'. Supported: [${Array.from(SolTriadJsonAdapter.SUPPORTED_VERSIONS).sort().join(", ")}]`,
        "STRUCTURAL_DEFECT",
        null,
        null,
        currentTs
      );
    }

    if ("engine_version" in reqObj && typeof reqObj["engine_version"] !== "string") {
      return this._createFailResponse(
        requestId,
        "Field 'engine_version' must be a string",
        "STRUCTURAL_DEFECT",
        null,
        "engine_version",
        currentTs
      );
    }

    if (
      "evaluation_context" in reqObj &&
      (typeof reqObj["evaluation_context"] !== "object" ||
        reqObj["evaluation_context"] === null ||
        Array.isArray(reqObj["evaluation_context"]))
    ) {
      return this._createFailResponse(
        requestId,
        "Field 'evaluation_context' must be an object",
        "STRUCTURAL_DEFECT",
        null,
        "evaluation_context",
        currentTs
      );
    }

    // 4. Check Required Primitives
    for (const reqField of ["source", "constraint", "dissipate", "initial_state"]) {
      if (
        !(reqField in reqObj) ||
        typeof reqObj[reqField] !== "object" ||
        reqObj[reqField] === null ||
        Array.isArray(reqObj[reqField])
      ) {
        return this._createFailResponse(
          requestId,
          `Missing or invalid required section '${reqField}' in request payload`,
          "STRUCTURAL_DEFECT",
          null,
          reqField,
          currentTs
        );
      }
    }

    // 5. Parse and Build Primitives
    let source: SourcePrimitive;
    let constraint: ConstraintPrimitive;
    let dissipate: DissipatePrimitive;
    let initialState: SystemState;

    try {
      source = this._parseSource(reqObj["source"] as Record<string, unknown>);
      constraint = this._parseConstraint(reqObj["constraint"] as Record<string, unknown>);
      dissipate = this._parseDissipate(reqObj["dissipate"] as Record<string, unknown>);
      initialState = this._parseInitialState(reqObj["initial_state"] as Record<string, unknown>);
    } catch (ve) {
      return this._createFailResponse(
        requestId,
        `Validation error in request primitives: ${(ve as Error).message}`,
        "STRUCTURAL_DEFECT",
        null,
        null,
        currentTs
      );
    }

    // 6. Setup Evidence Registry
    const activeRegistry =
      registry !== undefined ? registry : this.defaultRegistry;

    // 7. Evaluate via Engine
    const report = evaluateTriad(
      source,
      constraint,
      dissipate,
      initialState,
      activeRegistry,
      currentTs
    );

    // 8. Format response according to schema
    return this._formatResponse(requestId, report);
  }

  private _number(value: unknown, path: string): number {
    if (typeof value === "boolean" || typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error(`${path} must be a finite number`);
    }
    return value;
  }

  private _validateKeys(
    value: Record<string, unknown>,
    allowed: Set<string>,
    required: Set<string>,
    path: string
  ): void {
    const keys = Object.keys(value);
    const missing: string[] = [];
    for (const req of required) {
      if (!(req in value)) {
        missing.push(req);
      }
    }
    const unknown: string[] = [];
    for (const k of keys) {
      if (!allowed.has(k)) {
        unknown.push(k);
      }
    }

    if (missing.length > 0) {
      throw new Error(`${path} is missing required field(s): ${missing.sort().join(", ")}`);
    }
    if (unknown.length > 0) {
      throw new Error(`${path} contains unsupported field(s): ${unknown.sort().join(", ")}`);
    }
  }

  private _object(value: unknown, path: string): Record<string, unknown> {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      throw new Error(`${path} must be an object`);
    }
    return value as Record<string, unknown>;
  }

  private _stringList(value: unknown, path: string, allowNone: boolean = false): string[] | null {
    if (allowNone && value === null) {
      return null;
    }
    if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
      throw new Error(`${path} must be an array of strings${allowNone ? " or null" : ""}`);
    }
    return value;
  }

  private _stringListField(
    obj: Record<string, unknown>,
    key: string,
    path: string,
    required: boolean = false,
    allowNone: boolean = false
  ): string[] | null {
    if (!(key in obj)) {
      if (required) {
        throw new Error(`${path}.${key} is required`);
      }
      return allowNone ? null : [];
    }
    return this._stringList(obj[key], `${path}.${key}`, allowNone);
  }

  private _numberMapping(
    obj: Record<string, unknown>,
    key: string,
    path: string
  ): Record<string, number> {
    if (!(key in obj)) {
      return {};
    }
    const val = this._object(obj[key], `${path}.${key}`);
    const result: Record<string, number> = {};
    for (const [k, v] of Object.entries(val)) {
      result[k] = this._number(v, `${path}.${key}.${k}`);
    }
    return result;
  }

  private _booleanMapping(
    obj: Record<string, unknown>,
    key: string,
    path: string
  ): Record<string, boolean> {
    if (!(key in obj)) {
      return {};
    }
    const val = this._object(obj[key], `${path}.${key}`);
    const result: Record<string, boolean> = {};
    for (const [k, v] of Object.entries(val)) {
      if (typeof v !== "boolean") {
        throw new Error(`${path}.${key}.${k} must be a boolean`);
      }
      result[k] = v;
    }
    return result;
  }

  private _stringMapping(
    obj: Record<string, unknown>,
    key: string,
    path: string
  ): Record<string, string> {
    if (!(key in obj)) {
      return {};
    }
    const val = this._object(obj[key], `${path}.${key}`);
    const result: Record<string, string> = {};
    for (const [k, v] of Object.entries(val)) {
      if (typeof v !== "string") {
        throw new Error(`${path}.${key}.${k} must be a string`);
      }
      result[k] = v;
    }
    return result;
  }

  private _parseSource(sDict: Record<string, unknown>): SourcePrimitive {
    this._validateKeys(
      sDict,
      new Set([
        "evidence_id",
        "authority_domain",
        "granted_scope",
        "granted_loss_domains",
        "epistemic_type",
        "timestamp_sec",
        "max_age_sec",
        "corroborating_evidence_ids",
        "payload_hash",
      ]),
      new Set([
        "evidence_id",
        "authority_domain",
        "granted_scope",
        "granted_loss_domains",
        "epistemic_type",
        "timestamp_sec",
      ]),
      "source"
    );

    if (typeof sDict["evidence_id"] !== "string" || !sDict["evidence_id"].trim()) {
      throw new Error("source.evidence_id must be a non-empty string");
    }

    const epistemicRaw = sDict["epistemic_type"];
    if (
      epistemicRaw !== "FACT" &&
      epistemicRaw !== "INFERENCE" &&
      epistemicRaw !== "UNKNOWN"
    ) {
      throw new Error(`Invalid source.epistemic_type '${epistemicRaw}'`);
    }

    // Crucial: preserve distinction between null (structural defect) and [] (zero privileges)
    const authorityDomain = this._stringListField(
      sDict,
      "authority_domain",
      "source",
      true,
      true
    );
    const grantedScope = this._stringListField(
      sDict,
      "granted_scope",
      "source",
      true,
      true
    );
    const grantedLossDomains = this._stringListField(
      sDict,
      "granted_loss_domains",
      "source",
      true,
      true
    );

    const corroborating =
      this._stringListField(sDict, "corroborating_evidence_ids", "source", false, false) ??
      [];

    const payloadHash = sDict["payload_hash"];
    if (payloadHash !== undefined && payloadHash !== null && typeof payloadHash !== "string") {
      throw new Error("source.payload_hash must be a string or null");
    }

    return {
      evidence_id: sDict["evidence_id"] as string,
      authority_domain: authorityDomain,
      granted_scope: grantedScope,
      granted_loss_domains: grantedLossDomains,
      epistemic_type: epistemicRaw as EpistemicStatus,
      timestamp_sec: this._number(sDict["timestamp_sec"], "source.timestamp_sec"),
      max_age_sec:
        "max_age_sec" in sDict
          ? this._number(sDict["max_age_sec"], "source.max_age_sec")
          : 300.0,
      corroborating_evidence_ids: corroborating,
      payload_hash: (payloadHash as string) ?? undefined,
    };
  }

  private _parseConstraint(cDict: Record<string, unknown>): ConstraintPrimitive {
    this._validateKeys(
      cDict,
      new Set([
        "domain_scope",
        "target_objects",
        "protected_set",
        "protected_values",
        "max_bounds",
        "min_bounds",
        "units",
        "protected_flags",
        "forbidden_flags",
        "required_flags",
      ]),
      new Set(["domain_scope", "target_objects", "protected_set"]),
      "constraint"
    );

    const domainScope = this._stringListField(cDict, "domain_scope", "constraint", true) ?? [];
    const targetObjects = this._stringListField(cDict, "target_objects", "constraint", true) ?? [];
    const protectedSet = this._stringListField(cDict, "protected_set", "constraint", true) ?? [];
    const protectedFlags = this._stringListField(cDict, "protected_flags", "constraint") ?? [];
    const protectedValues = this._numberMapping(cDict, "protected_values", "constraint");
    const maxBounds = this._numberMapping(cDict, "max_bounds", "constraint");
    const minBounds = this._numberMapping(cDict, "min_bounds", "constraint");
    const units = this._stringMapping(cDict, "units", "constraint");
    const forbiddenFlags = this._booleanMapping(cDict, "forbidden_flags", "constraint");
    const requiredFlags = this._booleanMapping(cDict, "required_flags", "constraint");

    return {
      domain_scope: domainScope,
      target_objects: targetObjects,
      protected_set: protectedSet,
      protected_values: protectedValues,
      max_bounds: maxBounds,
      min_bounds: minBounds,
      units,
      protected_flags: protectedFlags,
      forbidden_flags: forbiddenFlags,
      required_flags: requiredFlags,
    };
  }

  private _parseDissipate(dDict: Record<string, unknown>): DissipatePrimitive {
    this._validateKeys(
      dDict,
      new Set([
        "loss_domain",
        "target_states",
        "side_effects",
        "resource_cost",
        "state_delta",
        "flag_delta",
        "units",
      ]),
      new Set(["loss_domain", "target_states", "side_effects"]),
      "dissipate"
    );

    const lossDomain = this._stringListField(dDict, "loss_domain", "dissipate", true) ?? [];
    const targetStates = this._stringListField(dDict, "target_states", "dissipate", true) ?? [];
    const sideEffects = this._stringListField(dDict, "side_effects", "dissipate", true) ?? [];
    const resourceCost = this._numberMapping(dDict, "resource_cost", "dissipate");
    const stateDelta = this._numberMapping(dDict, "state_delta", "dissipate");
    const flagDelta = this._booleanMapping(dDict, "flag_delta", "dissipate");
    const units = this._stringMapping(dDict, "units", "dissipate");

    return {
      loss_domain: lossDomain,
      target_states: targetStates,
      side_effects: sideEffects,
      resource_cost: resourceCost,
      state_delta: stateDelta,
      flag_delta: flagDelta,
      units,
    };
  }

  private _parseInitialState(sDict: Record<string, unknown>): SystemState {
    this._validateKeys(
      sDict,
      new Set(["current_values", "active_flags", "units"]),
      new Set(["current_values"]),
      "initial_state"
    );

    const currentValues = this._numberMapping(sDict, "current_values", "initial_state");
    const activeFlags = this._booleanMapping(sDict, "active_flags", "initial_state");
    const units = this._stringMapping(sDict, "units", "initial_state");

    return {
      current_values: currentValues,
      active_flags: activeFlags,
      units,
    };
  }

  private _formatResponse(
    requestId: string,
    report: EvaluationReport
  ): Record<string, unknown> {
    const pairwiseChecks: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(report.pairwise_checks)) {
      pairwiseChecks[k] = {
        relationship: v.relationship,
        is_valid: v.is_valid,
        verdict: v.verdict,
        diagnostics: v.diagnostics.map((d) => ({
          code: d.code,
          severity: d.severity,
          message: d.message,
          primitive: d.primitive ?? null,
          field_name: d.field_name ?? null,
        })),
      };
    }

    return {
      request_id: requestId,
      protocol_version: SolTriadJsonAdapter.PROTOCOL_VERSION,
      engine_version: report.engine_version,
      verdict: report.verdict,
      pairwise_checks: pairwiseChecks,
      diagnostics: report.diagnostics.map((d) => ({
        code: d.code,
        severity: d.severity,
        message: d.message,
        primitive: d.primitive ?? null,
        field_name: d.field_name ?? null,
      })),
      simulated_values: report.simulated_values,
      simulated_flags: report.simulated_flags,
      evaluation_timestamp: report.timestamp_sec,
      messages: report.diagnostics.map((d) => `[${d.code}] ${d.message}`),
    };
  }

  private _createFailResponse(
    requestId: string,
    message: string,
    code: DiagnosticCode = "STRUCTURAL_DEFECT",
    primitive: "SOURCE" | "CONSTRAINT" | "DISSIPATE" | "STATE" | null = null,
    fieldName: string | null = null,
    timestampSec?: number
  ): Record<string, unknown> {
    const ts =
      timestampSec !== undefined && Number.isFinite(timestampSec)
        ? timestampSec
        : Date.now() / 1000;
    const cleanRequestId = typeof requestId === "string" ? requestId : "invalid_request_id";

    const diag = {
      code,
      severity: "ERROR" as const,
      message,
      primitive: primitive ?? null,
      field_name: fieldName ?? null,
    };

    const failPairwise = {
      P_SC: {
        relationship: "P_SC",
        is_valid: false,
        verdict: "FAIL",
        diagnostics: [diag],
      },
      P_CD: {
        relationship: "P_CD",
        is_valid: false,
        verdict: "FAIL",
        diagnostics: [diag],
      },
      P_SD: {
        relationship: "P_SD",
        is_valid: false,
        verdict: "FAIL",
        diagnostics: [diag],
      },
    };

    return {
      request_id: cleanRequestId,
      protocol_version: SolTriadJsonAdapter.PROTOCOL_VERSION,
      engine_version: "0.4.1",
      verdict: "FAIL",
      pairwise_checks: failPairwise,
      diagnostics: [diag],
      simulated_values: {},
      simulated_flags: {},
      evaluation_timestamp: ts,
      messages: [`[${code}] ${message}`],
    };
  }
}
