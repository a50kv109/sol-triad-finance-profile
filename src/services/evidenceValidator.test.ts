/**
 * Evidence Validator & INFERENCE DAG Test Suite (Step 2)
 * Validates exact parity between evidenceValidator.ts and Python reference
 * (sol_triad/validators.py:EvidenceValidator and tests/unit/test_evidence_graph.py).
 */

import {
  EvidenceValidator,
  InMemoryEvidenceRegistry,
} from "./evidenceValidator";
import { SourcePrimitive, EvidenceRecord, CoherenceVerdict } from "../types/triad";

const NOW = 1000.0;
const DOMAIN = "telemetry";

function record(
  evidenceId: string,
  status: "FACT" | "INFERENCE" | "UNKNOWN",
  premises?: string[] | null,
  timestamp: number = NOW,
  domain: string = DOMAIN
): EvidenceRecord {
  return {
    evidence_id: evidenceId,
    domain,
    epistemic_status: status,
    timestamp_sec: timestamp,
    corroborating_evidence_ids: premises ?? undefined,
  };
}

function validateSource(
  registry: InMemoryEvidenceRegistry,
  rootId: string,
  premises: string[],
  maxAgeSec: number = 300.0,
  domain: string = DOMAIN
): [boolean, CoherenceVerdict, string[]] {
  const source: SourcePrimitive = {
    evidence_id: rootId,
    authority_domain: [domain],
    granted_scope: ["sensor_1"],
    granted_loss_domains: ["power"],
    epistemic_type: "INFERENCE",
    timestamp_sec: NOW,
    max_age_sec: maxAgeSec,
    corroborating_evidence_ids: premises,
  };
  const validator = new EvidenceValidator(registry, NOW);
  const [valid, verdict, diags] = validator.validate(source);
  return [valid, verdict, diags.map((d) => d.code)];
}

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

export function runStep2Tests() {
  console.log("=================================================================");
  console.log("RUNNING STEP 2 EVIDENCE VALIDATOR & INFERENCE DAG TESTS (TypeScript)");
  console.log("=================================================================\n");

  let passed = 0;
  let failed = 0;

  function test(name: string, fn: () => void) {
    try {
      fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (e) {
      console.error(`  [FAIL] ${name}: ${(e as Error).message}`);
      failed++;
    }
  }

  // --- 1. Linear & Nested Chains ---
  test("1.1 Linear chain: A -> B -> C -> FACT passes with PASS", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["level1"]));
    reg.register(record("level1", "INFERENCE", ["level2"]));
    reg.register(record("level2", "INFERENCE", ["fact1"]));
    reg.register(record("fact1", "FACT"));

    const [valid, verdict, codes] = validateSource(reg, "root", ["level1"]);
    assert(valid === true, "Must be valid");
    assert(verdict === "PASS", `Expected PASS, got ${verdict}`);
    assert(!codes.includes("INFERENCE_CHAIN_INCOMPLETE"), "No incomplete diagnostics");
  });

  test("1.2 Deep nested chain (depth 10) passes with PASS", () => {
    const reg = new InMemoryEvidenceRegistry();
    for (let i = 0; i < 10; i++) {
      const next = i === 9 ? "fact_terminal" : `node_${i + 1}`;
      reg.register(record(`node_${i}`, "INFERENCE", [next]));
    }
    reg.register(record("fact_terminal", "FACT"));

    const [valid, verdict] = validateSource(reg, "node_0", ["node_1"]);
    assert(valid === true, "Must be valid");
    assert(verdict === "PASS", `Expected PASS, got ${verdict}`);
  });

  // --- 2. Diamond DAG (Shared Premise without Cycle) ---
  test("2.1 Diamond DAG: A -> (B, C) -> D -> FACT passes without false cycle detection", () => {
    // A cites B and C
    // Both B and C cite D
    // D cites FACT
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("A", "INFERENCE", ["B", "C"]));
    reg.register(record("B", "INFERENCE", ["D"]));
    reg.register(record("C", "INFERENCE", ["D"]));
    reg.register(record("D", "INFERENCE", ["fact"]));
    reg.register(record("fact", "FACT"));

    const [valid, verdict, codes] = validateSource(reg, "A", ["B", "C"]);
    assert(valid === true, `Must be valid for valid diamond DAG`);
    assert(verdict === "PASS", `Expected PASS, got ${verdict}`);
    assert(!codes.includes("INFERENCE_CIRCULAR_DEPENDENCY"), "Shared premise must not be flagged as cycle");
  });

  // --- 3. Cycle Detection of Arbitrary Length ---
  test("3.1 2-node cycle: A -> B -> A detected as FAIL (INFERENCE_CIRCULAR_DEPENDENCY)", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("A", "INFERENCE", ["B"]));
    reg.register(record("B", "INFERENCE", ["A"]));

    const [valid, verdict, codes] = validateSource(reg, "A", ["B"]);
    assert(valid === false, "Cycle must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("INFERENCE_CIRCULAR_DEPENDENCY"), "Must flag INFERENCE_CIRCULAR_DEPENDENCY");
  });

  test("3.2 3-node cycle: A -> B -> C -> A detected as FAIL", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("A", "INFERENCE", ["B"]));
    reg.register(record("B", "INFERENCE", ["C"]));
    reg.register(record("C", "INFERENCE", ["A"]));

    const [valid, verdict, codes] = validateSource(reg, "A", ["B"]);
    assert(valid === false, "3-node cycle must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("INFERENCE_CIRCULAR_DEPENDENCY"), "Must flag circular dependency on A");
  });

  test("3.3 Multi-node cycle deep in graph: A -> B -> (C -> D -> E -> C) fails", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("A", "INFERENCE", ["B"]));
    reg.register(record("B", "INFERENCE", ["C"]));
    reg.register(record("C", "INFERENCE", ["D"]));
    reg.register(record("D", "INFERENCE", ["E"]));
    reg.register(record("E", "INFERENCE", ["C"])); // Sub-cycle C -> D -> E -> C

    const [valid, verdict, codes] = validateSource(reg, "A", ["B"]);
    assert(valid === false, "Deep cycle must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("INFERENCE_CIRCULAR_DEPENDENCY"), "Must flag circular dependency on C");
  });

  // --- 4. Source vs Registry Premise Integrity ---
  test("4.1 Source premise mismatch: agent claims different premises than registered fails", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["registered_premise"]));
    reg.register(record("registered_premise", "FACT"));
    reg.register(record("agent_spoofed_premise", "FACT"));

    // Agent tries to claim 'agent_spoofed_premise'
    const [valid, verdict, codes] = validateSource(reg, "root", ["agent_spoofed_premise"]);
    assert(valid === false, "Mismatched premises must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("EVIDENCE_MISMATCH"), "Must flag EVIDENCE_MISMATCH");
  });

  test("4.2 Source empty premises when registry has premises fails", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["registered_premise"]));
    reg.register(record("registered_premise", "FACT"));

    const [valid, verdict, codes] = validateSource(reg, "root", []);
    assert(valid === false, "Empty source premises must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("EVIDENCE_MISMATCH"), "Must flag EVIDENCE_MISMATCH");
  });

  // --- 5. Missing Evidence Record in Registry ---
  test("5.1 Missing corroborating evidence in registry fails strictly with EVIDENCE_NOT_FOUND", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["missing_premise"]));

    const [valid, verdict, codes] = validateSource(reg, "root", ["missing_premise"]);
    assert(valid === false, "Missing premise must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("EVIDENCE_NOT_FOUND"), "Must flag EVIDENCE_NOT_FOUND");
  });

  // --- 6. Traversal Depth & Node Count Limits ---
  test("6.1 Exceeding MAX_INFERENCE_DEPTH (64) returns REVIEW with INFERENCE_TRAVERSAL_LIMIT_EXCEEDED", () => {
    const reg = new InMemoryEvidenceRegistry();
    // Build chain of depth 66: node_0 -> node_1 -> ... -> node_65 -> fact
    for (let i = 0; i < 66; i++) {
      const next = i === 65 ? "fact_terminal" : `node_${i + 1}`;
      reg.register(record(`node_${i}`, "INFERENCE", [next]));
    }
    reg.register(record("fact_terminal", "FACT"));

    const [valid, verdict, codes] = validateSource(reg, "node_0", ["node_1"]);
    assert(valid === false, "Depth limit exceeded must not pass");
    assert(verdict === "REVIEW", `Expected REVIEW, got ${verdict}`);
    assert(codes.includes("INFERENCE_TRAVERSAL_LIMIT_EXCEEDED"), "Must flag traversal limit exceeded");
  });

  test("6.2 Exceeding MAX_INFERENCE_NODES (1024) returns REVIEW with INFERENCE_TRAVERSAL_LIMIT_EXCEEDED", () => {
    const reg = new InMemoryEvidenceRegistry();
    // Build wide tree: root cites 1030 premises, each premise is a valid FACT
    const premises: string[] = [];
    for (let i = 0; i < 1030; i++) {
      const pid = `fact_premise_${i}`;
      premises.push(pid);
      reg.register(record(pid, "FACT"));
    }
    reg.register(record("root_wide", "INFERENCE", premises));

    const [valid, verdict, codes] = validateSource(reg, "root_wide", premises);
    assert(valid === false, "Node limit exceeded must not pass");
    assert(verdict === "REVIEW", `Expected REVIEW, got ${verdict}`);
    assert(codes.includes("INFERENCE_TRAVERSAL_LIMIT_EXCEEDED"), "Must flag node traversal limit exceeded");
  });

  // --- 7. Premise Epistemic Status & Temporal Sanity ---
  test("7.1 Premise with UNKNOWN status fails strictly with INFERENCE_PREMISE_INVALID_STATUS", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["unverified_premise"]));
    reg.register(record("unverified_premise", "UNKNOWN"));

    const [valid, verdict, codes] = validateSource(reg, "root", ["unverified_premise"]);
    assert(valid === false, "UNKNOWN premise must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("INFERENCE_PREMISE_INVALID_STATUS"), "Must flag INFERENCE_PREMISE_INVALID_STATUS");
  });

  test("7.2 Premise with future timestamp fails strictly with TEMPORAL_FUTURE", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["future_premise"]));
    reg.register(record("future_premise", "FACT", null, NOW + 100.0));

    const [valid, verdict, codes] = validateSource(reg, "root", ["future_premise"]);
    assert(valid === false, "Future premise must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("TEMPORAL_FUTURE"), "Must flag TEMPORAL_FUTURE");
  });

  test("7.3 Premise that is stale returns REVIEW with TEMPORAL_STALE", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["stale_premise"]));
    reg.register(record("stale_premise", "FACT", null, NOW - 500.0)); // 500s old vs max_age 300s

    const [valid, verdict, codes] = validateSource(reg, "root", ["stale_premise"], 300.0);
    assert(valid === false, "Stale premise cannot pass");
    assert(verdict === "REVIEW", `Expected REVIEW, got ${verdict}`);
    assert(codes.includes("TEMPORAL_STALE"), "Must flag TEMPORAL_STALE");
  });

  test("7.4 Premise outside authority domain fails with EVIDENCE_DOMAIN_MISMATCH", () => {
    const reg = new InMemoryEvidenceRegistry();
    reg.register(record("root", "INFERENCE", ["unauth_domain_premise"]));
    reg.register(record("unauth_domain_premise", "FACT", null, NOW, "unauthorized_military_domain"));

    const [valid, verdict, codes] = validateSource(reg, "root", ["unauth_domain_premise"], 300.0, "telemetry");
    assert(valid === false, "Premise outside authority domain must fail");
    assert(verdict === "FAIL", `Expected FAIL, got ${verdict}`);
    assert(codes.includes("EVIDENCE_DOMAIN_MISMATCH"), "Must flag EVIDENCE_DOMAIN_MISMATCH");
  });

  console.log("\n=================================================================");
  console.log(`SUMMARY: ${passed} PASSED, ${failed} FAILED`);
  console.log("=================================================================\n");

  if (failed > 0) {
    throw new Error(`${failed} tests failed!`);
  }
}

// Auto-run if executed directly
if (typeof process !== "undefined" && process.argv[1]?.includes("evidenceValidator.test")) {
  runStep2Tests();
}
