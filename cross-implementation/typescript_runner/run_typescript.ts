/**
 * TypeScript Runner for Cross-Implementation Consistency Test.
 * Runs evaluated TypeScript SOL-Triad v1 against all fixtures.
 * Outputs: cross-implementation/typescript_runner/typescript_results.json
 */

import * as fs from "fs";
import * as path from "path";
import { SolTriadJsonAdapter } from "../../src/services/jsonAdapter";
import { InMemoryEvidenceRegistry } from "../../src/services/evidenceValidator";
import { EvidenceRecord, EpistemicStatus } from "../../src/types/triad";

function runFixtures() {
  const fixturesPath = path.resolve("cross-implementation/fixtures/fixtures.json");
  const rawData = fs.readFileSync(fixturesPath, "utf-8");
  const fixtures = JSON.parse(rawData);

  const results: any[] = [];

  for (const f of fixtures) {
    const fid = f.id;
    const group = f.group;
    const name = f.name;
    const evalTime = f.evaluation_time;
    const rawRecords = f.registry_records || [];

    // Build Host Registry Oracle
    const registry = new InMemoryEvidenceRegistry();
    for (const rec of rawRecords) {
      const record: EvidenceRecord = {
        evidence_id: rec.evidence_id,
        domain: rec.domain,
        epistemic_status: rec.epistemic_status as EpistemicStatus,
        timestamp_sec: rec.timestamp_sec,
        payload_hash: rec.payload_hash ?? undefined,
        corroborating_evidence_ids: rec.corroborating_evidence_ids || undefined,
      };
      registry.register(record);
    }

    const adapter = new SolTriadJsonAdapter(registry);
    const reqPayload = f.request;

    let resp: any;
    try {
      resp = adapter.evaluateJson(reqPayload, undefined, evalTime);
    } catch (ex) {
      resp = {
        error: "EXECUTION_EXCEPTION",
        message: (ex as Error).message,
        type: (ex as Error).name,
      };
    }

    results.append ? results.append(resp) : results.push({
      id: fid,
      group,
      name,
      response: resp,
    });
  }

  const outDir = path.resolve("cross-implementation/typescript_runner");
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }
  const outPath = path.join(outDir, "typescript_results.json");
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2), "utf-8");

  console.log(`TypeScript runner completed ${results.length} fixtures -> ${outPath}`);
}

runFixtures();
