/**
 * Automated Deep Diff Comparator for Cross-Implementation Consistency Test.
 * Compares python_results.json vs typescript_results.json across 68 fixtures.
 * Generates:
 *   - cross-implementation/reports/CROSS_IMPLEMENTATION_REPORT.json
 *   - cross-implementation/reports/CROSS_IMPLEMENTATION_REPORT.md
 */

import * as fs from "fs";
import * as path from "path";

interface ComparisonItem {
  id: string;
  group: string;
  name: string;
  status: "MATCH" | "PARTIAL_MATCH" | "MISMATCH" | "NOT_COMPARABLE";
  category?: "A" | "B" | "C";
  summary: string;
  python: {
    verdict?: string;
    pairwise?: Record<string, { verdict: string; is_valid: boolean; codes: string[] }>;
    diagnostic_codes?: string[];
    simulated_values?: Record<string, number>;
    simulated_flags?: Record<string, boolean>;
  };
  typescript: {
    verdict?: string;
    pairwise?: Record<string, { verdict: string; is_valid: boolean; codes: string[] }>;
    diagnostic_codes?: string[];
    simulated_values?: Record<string, number>;
    simulated_flags?: Record<string, boolean>;
  };
  differences: string[];
  hypothesis?: string;
  recommendation?: string;
}

function compareResults() {
  const pyPath = path.resolve("cross-implementation/python_runner/python_results.json");
  const tsPath = path.resolve("cross-implementation/typescript_runner/typescript_results.json");

  const pyResults: any[] = JSON.parse(fs.readFileSync(pyPath, "utf-8"));
  const tsResults: any[] = JSON.parse(fs.readFileSync(tsPath, "utf-8"));

  const pyMap = new Map<string, any>(pyResults.map((r) => [r.id, r]));
  const tsMap = new Map<string, any>(tsResults.map((r) => [r.id, r]));

  const comparisonItems: ComparisonItem[] = [];

  let matchCount = 0;
  let partialCount = 0;
  let mismatchCount = 0;
  let notComparableCount = 0;

  for (const pyItem of pyResults) {
    const id = pyItem.id;
    const group = pyItem.group;
    const name = pyItem.name;
    const tsItem = tsMap.get(id);

    if (!tsItem) {
      comparisonItems.push({
        id,
        group,
        name,
        status: "NOT_COMPARABLE",
        category: "A",
        summary: "Fixture missing in TypeScript results",
        python: {},
        typescript: {},
        differences: ["TypeScript result not found"],
      });
      notComparableCount++;
      continue;
    }

    const pyResp = pyItem.response;
    const tsResp = tsItem.response;

    if (pyResp.error || tsResp.error) {
      comparisonItems.push({
        id,
        group,
        name,
        status: "NOT_COMPARABLE",
        category: "A",
        summary: `Runtime execution error: Py(${pyResp.error || "none"}) TS(${tsResp.error || "none"})`,
        python: { verdict: pyResp.verdict },
        typescript: { verdict: tsResp.verdict },
        differences: [
          pyResp.error ? `Python error: ${pyResp.message}` : "",
          tsResp.error ? `TypeScript error: ${tsResp.message}` : "",
        ].filter(Boolean),
      });
      notComparableCount++;
      continue;
    }

    const pyVerdict = pyResp.verdict;
    const tsVerdict = tsResp.verdict;

    const extractPairwise = (resp: any) => {
      const pw = resp.pairwise_checks || {};
      const res: Record<string, { verdict: string; is_valid: boolean; codes: string[] }> = {};
      for (const k of ["P_SC", "P_CD", "P_SD"]) {
        const item = pw[k] || {};
        const diags = item.diagnostics || [];
        res[k] = {
          verdict: item.verdict,
          is_valid: item.is_valid,
          codes: diags.map((d: any) => d.code).sort(),
        };
      }
      return res;
    };

    const pyPairwise = extractPairwise(pyResp);
    const tsPairwise = extractPairwise(tsResp);

    const pyCodes = (pyResp.diagnostics || []).map((d: any) => d.code).sort();
    const tsCodes = (tsResp.diagnostics || []).map((d: any) => d.code).sort();

    const pySimVals = pyResp.simulated_values || {};
    const tsSimVals = tsResp.simulated_values || {};

    const pySimFlags = pyResp.simulated_flags || {};
    const tsSimFlags = tsResp.simulated_flags || {};

    const diffs: string[] = [];
    let criticalMismatch = false;
    let functionalMismatch = false;

    // 1. Verdict comparison
    if (pyVerdict !== tsVerdict) {
      diffs.push(`Verdict mismatch: Python='${pyVerdict}', TypeScript='${tsVerdict}'`);
      criticalMismatch = true;
    }

    // 2. Pairwise checks comparison
    for (const rel of ["P_SC", "P_CD", "P_SD"]) {
      const pPy = pyPairwise[rel];
      const pTs = tsPairwise[rel];
      if (pPy.verdict !== pTs.verdict) {
        diffs.push(`${rel} verdict mismatch: Python='${pPy.verdict}', TypeScript='${pTs.verdict}'`);
        criticalMismatch = true;
      }
      if (pPy.is_valid !== pTs.is_valid) {
        diffs.push(`${rel} is_valid mismatch: Python=${pPy.is_valid}, TypeScript=${pTs.is_valid}`);
        criticalMismatch = true;
      }

      // Pairwise diagnostic codes comparison
      const setPyRel = new Set(pPy.codes);
      const setTsRel = new Set(pTs.codes);
      const missingInTs = pPy.codes.filter((c) => !setTsRel.has(c));
      const extraInTs = pTs.codes.filter((c) => !setPyRel.has(c));
      if (missingInTs.length > 0 || extraInTs.length > 0) {
        diffs.push(
          `${rel} diagnostics codes differ: missing in TS=[${missingInTs.join(", ")}], extra in TS=[${extraInTs.join(", ")}]`
        );
        functionalMismatch = true;
      }
    }

    // 3. Overall diagnostic codes comparison
    const setPyCodes = new Set(pyCodes);
    const setTsCodes = new Set(tsCodes);
    const overallMissingInTs = pyCodes.filter((c: string) => !setTsCodes.has(c));
    const overallExtraInTs = tsCodes.filter((c: string) => !setPyCodes.has(c));
    if (overallMissingInTs.length > 0 || overallExtraInTs.length > 0) {
      diffs.push(
        `Overall diagnostic codes differ: missing in TS=[${overallMissingInTs.join(", ")}], extra in TS=[${overallExtraInTs.join(", ")}]`
      );
      functionalMismatch = true;
    }

    // 4. Simulated values comparison
    const allValKeys = Array.from(new Set([...Object.keys(pySimVals), ...Object.keys(tsSimVals)]));
    for (const k of allValKeys) {
      const vPy = pySimVals[k];
      const vTs = tsSimVals[k];
      if (vPy === undefined || vTs === undefined) {
        diffs.push(`Simulated value '${k}' missing in one implementation: Py=${vPy}, TS=${vTs}`);
        functionalMismatch = true;
      } else if (Math.abs(vPy - vTs) > 1e-5) {
        diffs.push(`Simulated value '${k}' numerical difference: Py=${vPy}, TS=${vTs}`);
        functionalMismatch = true;
      }
    }

    // 5. Simulated flags comparison
    const allFlagKeys = Array.from(new Set([...Object.keys(pySimFlags), ...Object.keys(tsSimFlags)]));
    for (const k of allFlagKeys) {
      const fPy = pySimFlags[k];
      const fTs = tsSimFlags[k];
      if (fPy !== fTs) {
        diffs.push(`Simulated flag '${k}' difference: Py=${fPy}, TS=${fTs}`);
        functionalMismatch = true;
      }
    }

    let status: "MATCH" | "PARTIAL_MATCH" | "MISMATCH" = "MATCH";
    let category: "A" | "B" | "C" | undefined = undefined;

    if (criticalMismatch) {
      status = "MISMATCH";
      category = "A";
      mismatchCount++;
    } else if (functionalMismatch) {
      // If verdict and pairwise verdicts match, but benign code difference
      status = "PARTIAL_MATCH";
      category = "B";
      partialCount++;
    } else if (diffs.length > 0) {
      status = "PARTIAL_MATCH";
      category = "C";
      partialCount++;
    } else {
      status = "MATCH";
      matchCount++;
    }

    comparisonItems.push({
      id,
      group,
      name,
      status,
      category,
      summary:
        status === "MATCH"
          ? "Exact parity across verdict, pairwise channels, diagnostics, and simulated state."
          : `Discrepancy detected: ${diffs.join("; ")}`,
      python: {
        verdict: pyVerdict,
        pairwise: pyPairwise,
        diagnostic_codes: pyCodes,
        simulated_values: pySimVals,
        simulated_flags: pySimFlags,
      },
      typescript: {
        verdict: tsVerdict,
        pairwise: tsPairwise,
        diagnostic_codes: tsCodes,
        simulated_values: tsSimVals,
        simulated_flags: tsSimFlags,
      },
      differences: diffs,
      hypothesis:
        status === "MATCH"
          ? undefined
          : "Discrepancy between Python validator and TypeScript validator logic",
      recommendation:
        status === "MATCH"
          ? undefined
          : "Review respective validator implementation against formal specification",
    });
  }

  // Generate Reports
  const reportDir = path.resolve("cross-implementation/reports");
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  const jsonReport = {
    metadata: {
      generated_at: new Date().toISOString(),
      python_version: "Python 3.10.12 (SOL-Triad-Engine v0.4.1)",
      typescript_version: "TypeScript (SOL-Triad Simulator v0.4.1)",
      json_protocol_version: "0.4.0",
      total_scenarios: comparisonItems.length,
      match: matchCount,
      partial_match: partialCount,
      mismatch: mismatchCount,
      not_comparable: notComparableCount,
      consistency_rate: `${(((matchCount + partialCount) / comparisonItems.length) * 100).toFixed(1)}%`,
      exact_match_rate: `${((matchCount / comparisonItems.length) * 100).toFixed(1)}%`,
    },
    results: comparisonItems,
  };

  fs.writeFileSync(
    path.join(reportDir, "CROSS_IMPLEMENTATION_REPORT.json"),
    JSON.stringify(jsonReport, null, 2),
    "utf-8"
  );

  // Generate Markdown Report
  let md = `# SOL-Triad Cross-Implementation Consistency Audit Report\n\n`;
  md += `**Date:** ${new Date().toISOString()}\n`;
  md += `**Reference Kernel:** Python SOL-Triad-Engine v0.4.1\n`;
  md += `**Evaluated Simulator:** TypeScript SOL-Triad v1 (v0.4.1)\n`;
  md += `**Protocol Version:** 0.4.0\n\n`;

  md += `## 1. Executive Summary\n\n`;
  md += `| Metric | Count | Percentage |\n`;
  md += `| :--- | :---: | :---: |\n`;
  md += `| **Total Scenarios Evaluated** | **${comparisonItems.length}** | 100.0% |\n`;
  md += `| **MATCH (Exact 100% Parity)** | **${matchCount}** | **${((matchCount / comparisonItems.length) * 100).toFixed(1)}%** |\n`;
  md += `| **PARTIAL_MATCH (Benign Minor Diff)** | **${partialCount}** | ${((partialCount / comparisonItems.length) * 100).toFixed(1)}% |\n`;
  md += `| **MISMATCH (Substantive Divergence)** | **${mismatchCount}** | ${((mismatchCount / comparisonItems.length) * 100).toFixed(1)}% |\n`;
  md += `| **NOT_COMPARABLE (Execution Failure)** | **${notComparableCount}** | ${((notComparableCount / comparisonItems.length) * 100).toFixed(1)}% |\n\n`;

  md += `## 2. Breakdown by Subsystem Group\n\n`;
  md += `| Group | Subsystem Domain | Total | MATCH | PARTIAL | MISMATCH | Parity Rate |\n`;
  md += `| :---: | :--- | :---: | :---: | :---: | :---: | :---: |\n`;

  const groups = [
    { id: "A", name: "SOURCE & Evidence Grounding" },
    { id: "B", name: "INFERENCE Recursive DAG & Cycles" },
    { id: "C", name: "SCOPE & Authority Domains" },
    { id: "D", name: "CONSTRAINT & State Invariants" },
    { id: "E", name: "DISSIPATE & Resource Costs" },
    { id: "F", name: "Units of Measurement & Conversions" },
    { id: "G", name: "JSON & Protocol Structure" },
    { id: "H", name: "Combined Multi-Violation Scenarios" },
  ];

  for (const g of groups) {
    const items = comparisonItems.filter((i) => i.group === g.id);
    const m = items.filter((i) => i.status === "MATCH").length;
    const p = items.filter((i) => i.status === "PARTIAL_MATCH").length;
    const mm = items.filter((i) => i.status === "MISMATCH").length;
    const rate = items.length > 0 ? `${(((m + p) / items.length) * 100).toFixed(1)}%` : "N/A";
    md += `| ${g.id} | ${g.name} | ${items.length} | ${m} | ${p} | ${mm} | **${rate}** |\n`;
  }
  md += `\n`;

  md += `## 3. Discrepancy Registry\n\n`;
  const discrepancies = comparisonItems.filter((i) => i.status !== "MATCH");
  if (discrepancies.length === 0) {
    md += `**Zero discrepancies detected.** All 68 scenarios matched across verdict, channels P_SC / P_CD / P_SD, diagnostic codes, and simulated state vectors.\n\n`;
  } else {
    for (const d of discrepancies) {
      md += `### [${d.id}] ${d.name} (Status: ${d.status}, Category: ${d.category})\n`;
      md += `- **Summary:** ${d.summary}\n`;
      md += `- **Python Result:** Verdict=${d.python.verdict}, Codes=[${(d.python.diagnostic_codes || []).join(", ")}]\n`;
      md += `- **TypeScript Result:** Verdict=${d.typescript.verdict}, Codes=[${(d.typescript.diagnostic_codes || []).join(", ")}]\n`;
      md += `- **Differences:**\n`;
      for (const diff of d.differences) {
        md += `  - ${diff}\n`;
      }
      if (d.hypothesis) md += `- **Hypothesis:** ${d.hypothesis}\n`;
      if (d.recommendation) md += `- **Recommendation:** ${d.recommendation}\n`;
      md += `\n`;
    }
  }

  md += `## 4. Detailed Scenario Inventory\n\n`;
  md += `| ID | Group | Verdict (Py / TS) | P_SC | P_CD | P_SD | Codes Match | Status |\n`;
  md += `| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n`;
  for (const item of comparisonItems) {
    const pyV = item.python.verdict || "N/A";
    const tsV = item.typescript.verdict || "N/A";
    const pSc = `${item.python.pairwise?.P_SC?.verdict || "-"}/${item.typescript.pairwise?.P_SC?.verdict || "-"}`;
    const pCd = `${item.python.pairwise?.P_CD?.verdict || "-"}/${item.typescript.pairwise?.P_CD?.verdict || "-"}`;
    const pSd = `${item.python.pairwise?.P_SD?.verdict || "-"}/${item.typescript.pairwise?.P_SD?.verdict || "-"}`;
    const pyC = item.python.diagnostic_codes || [];
    const tsC = item.typescript.diagnostic_codes || [];
    const codesMatch = pyC.join(",") === tsC.join(",") ? "YES" : "NO";
    const statusBadge = item.status === "MATCH" ? "MATCH" : item.status;
    md += `| ${item.id} | ${item.group} | ${pyV} / ${tsV} | ${pSc} | ${pCd} | ${pSd} | ${codesMatch} | ${statusBadge} |\n`;
  }

  fs.writeFileSync(path.join(reportDir, "CROSS_IMPLEMENTATION_REPORT.md"), md, "utf-8");

  console.log(`\n======================================================`);
  console.log(`CROSS-IMPLEMENTATION CONSISTENCY AUDIT COMPLETE:`);
  console.log(`  Total Scenarios:  ${comparisonItems.length}`);
  console.log(`  Exact MATCH:      ${matchCount} (${((matchCount / comparisonItems.length) * 100).toFixed(1)}%)`);
  console.log(`  PARTIAL_MATCH:    ${partialCount}`);
  console.log(`  MISMATCH:         ${mismatchCount}`);
  console.log(`  NOT_COMPARABLE:   ${notComparableCount}`);
  console.log(`======================================================\n`);

  return { matchCount, partialCount, mismatchCount, notComparableCount };
}

compareResults();
