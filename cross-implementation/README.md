# SOL-Triad Cross-Implementation Consistency Test Suite

This test suite performs an independent, head-to-head consistency audit between:
- **Reference Kernel:** Python `SOL-Triad-Engine v0.4.1` (located in `/v2-reference/sol_triad`)
- **Evaluated Implementation:** TypeScript `SOL-Triad v1` (located in `/src/services`)

## Architecture

```
cross-implementation/
    fixtures/
        fixtures.json            # 68 standardized JSON test vectors across Groups A-H
    python_runner/
        run_python.py            # Executes reference Python SolTriadJsonAdapter
    typescript_runner/
        run_typescript.ts        # Executes TypeScript SolTriadJsonAdapter
    comparison/
        comparator.ts            # Deep diff engine comparing verdicts, pairwise states, and diagnostics
    reports/
        CROSS_IMPLEMENTATION_REPORT.json
        CROSS_IMPLEMENTATION_REPORT.md
```

## Comparison Categories
- **MATCH:** 100% exact match on verdict, pairwise check verdicts (`P_SC`, `P_CD`, `P_SD`), diagnostic codes, and simulated values/flags.
- **PARTIAL_MATCH:** Matching overall verdict and key decision paths with benign differences (e.g., ordering).
- **MISMATCH:** Discrepancy in verdicts, pairwise status, or diagnostic codes.
- **NOT_COMPARABLE:** Execution could not be compared.
