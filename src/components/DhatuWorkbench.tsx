import React, { useState, useMemo } from "react";
import {
  Layers,
  Cpu,
  ShieldCheck,
  AlertTriangle,
  GitBranch,
  FileText,
  Search,
  CheckCircle2,
  Clock,
  Sparkles,
  Lock,
  ArrowRight,
  HelpCircle,
  Database,
  Terminal,
} from "lucide-react";
import dhatuScenarios from "../data/dhatu_test_scenarios.json";

interface DhatuScenario {
  test_id: string;
  input_text: string;
  language: string;
  expected_structure: any;
  expected_dhatu: string[];
  expected_provenance: any;
  expected_status: string;
  pass_criteria: string;
}

export default function DhatuWorkbench() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("T01");
  const [customInput, setCustomInput] = useState<string>("");
  const [useCustom, setUseCustom] = useState<boolean>(false);
  const [filterLang, setFilterLang] = useState<string>("all");
  const [filterSearch, setFilterSearch] = useState<string>("");

  const scenarios: DhatuScenario[] = dhatuScenarios as DhatuScenario[];

  const currentScenario = useMemo(() => {
    return scenarios.find((s) => s.test_id === selectedScenarioId) || scenarios[0];
  }, [selectedScenarioId, scenarios]);

  const activeText = useCustom ? customInput : currentScenario.input_text;
  const activeLang = useCustom ? "custom" : currentScenario.language;

  // Filtered scenarios for selector dropdown
  const filteredScenarios = useMemo(() => {
    return scenarios.filter((s) => {
      const matchLang = filterLang === "all" || s.language === filterLang;
      const matchSearch =
        !filterSearch ||
        s.test_id.toLowerCase().includes(filterSearch.toLowerCase()) ||
        s.input_text.toLowerCase().includes(filterSearch.toLowerCase()) ||
        s.expected_status.toLowerCase().includes(filterSearch.toLowerCase());
      return matchLang && matchSearch;
    });
  }, [scenarios, filterLang, filterSearch]);

  // Determine Layer execution statuses (honestly set to NOT_EXECUTED / NOT_IMPLEMENTED)
  const linguisticStatus = "NOT_EXECUTED";
  const semanticStatus = "NOT_EXECUTED";
  const physicalValidationStatus = "NOT_IMPLEMENTED";

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PASS":
      case "COMPLETED":
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">COMPLETED / PASS</span>;
      case "NEEDS_CLARIFICATION":
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">NEEDS_CLARIFICATION</span>;
      case "CONFLICT":
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">CONFLICT DETECTED</span>;
      case "NOT_IMPLEMENTED":
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">NOT_IMPLEMENTED</span>;
      case "NOT_EXECUTED":
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">NOT_EXECUTED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-950/80 via-slate-900 to-slate-900 border border-indigo-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
          <Cpu className="w-32 h-32 text-indigo-400" />
        </div>
        <div className="max-w-3xl space-y-2 relative z-10">
          <div className="flex items-center space-x-2">
            <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 font-mono font-semibold">
              Sanskrit Dhatu Semantic Adapter v0.1.3
            </span>
            <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 font-mono">
              70 Test Scenarios Connected
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black font-mono tracking-tight text-white">
            Dhatu Semantic Adapter Workbench
          </h2>
          <p className="text-sm text-slate-300">
            Interactive test registry and semantic structure viewer for RU, UK, and EN. Displays expected Dhatu mappings, ontology categories, DAG fixtures, and provenance. Live NLP analysis and physical validation are not yet implemented.
          </p>
        </div>
      </div>

      {/* Control Scenarios Quick Bar (A, B, C) */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">Control Scenarios:</span>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => {
                setUseCustom(false);
                setSelectedScenarioId("T29"); // Уменьшить температуру двигателя
              }}
              className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-amber-300 border border-amber-500/40 rounded-xl text-xs font-mono transition-all flex items-center space-x-1"
            >
              <span>A: Engine Temp Decrease</span>
            </button>
            <button
              onClick={() => {
                setUseCustom(false);
                setSelectedScenarioId("T67"); // Отвести избыточное тепло от двигателя
              }}
              className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-amber-300 border border-amber-500/40 rounded-xl text-xs font-mono transition-all flex items-center space-x-1"
            >
              <span>B: Heat Transfer (Unknown Mech)</span>
            </button>
            <button
              onClick={() => {
                setUseCustom(false);
                setSelectedScenarioId("T70"); // Не допустить повышения температуры выше 80 °C
              }}
              className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-emerald-300 border border-emerald-500/40 rounded-xl text-xs font-mono transition-all flex items-center space-x-1"
            >
              <span>C: Max Temp Bound (80°C = 353.15K)</span>
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
          <span>Active Mode: <strong className="text-indigo-400 font-bold">{useCustom ? "CUSTOM INPUT (NOT_EXECUTED)" : `PRESET [${currentScenario.test_id}]`}</strong></span>
        </div>
      </div>

      {/* Three-Layer Architecture Status Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. Linguistic Layer */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded bg-blue-500/20 text-blue-400 font-mono text-xs flex items-center justify-center font-bold">L1</span>
              <h3 className="font-bold text-sm text-slate-200">Linguistic Layer</h3>
            </div>
            {getStatusBadge(linguisticStatus)}
          </div>
          <p className="text-xs text-slate-400">
            Parses raw string input across RU, UK, EN, maps tokens to Sanskrit Dhatu roots (e.g., √man, √tula, √sthiti, √tapa).
          </p>
          <div className="text-xs font-mono bg-slate-950 p-2.5 rounded-xl border border-slate-800 space-y-1 text-slate-300">
            <div>Execution Status: <strong className="text-amber-400">NOT_EXECUTED</strong></div>
            <div>Expected Dhatu Roots: <strong className="text-indigo-400">{useCustom ? "N/A" : currentScenario.expected_dhatu.join(", ")}</strong></div>
            <div>Language: <strong className="uppercase">{activeLang}</strong></div>
          </div>
        </div>

        {/* 2. Semantic Layer */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded bg-indigo-500/20 text-indigo-400 font-mono text-xs flex items-center justify-center font-bold">L2</span>
              <h3 className="font-bold text-sm text-slate-200">Semantic Layer</h3>
            </div>
            {getStatusBadge(semanticStatus)}
          </div>
          <p className="text-xs text-slate-400">
            Transforms Dhatu tokens into 9 ontological categories, DAG structures, structured provenance, and causal relations.
          </p>
          <div className="text-xs font-mono bg-slate-950 p-2.5 rounded-xl border border-slate-800 space-y-1 text-slate-300">
            <div>Execution Status: <strong className="text-amber-400">NOT_EXECUTED</strong></div>
            <div>Expected Test Status: <strong className="text-emerald-400">{useCustom ? "N/A" : currentScenario.expected_status}</strong></div>
            <div>Expected Provenance: <strong className="text-indigo-300">{useCustom ? "N/A" : JSON.stringify(currentScenario.expected_provenance)}</strong></div>
          </div>
        </div>

        {/* 3. Physical Validation Layer */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <span className="w-6 h-6 rounded bg-amber-500/20 text-amber-400 font-mono text-xs flex items-center justify-center font-bold">L3</span>
              <h3 className="font-bold text-sm text-slate-200">Physical Validation Layer</h3>
            </div>
            {getStatusBadge(physicalValidationStatus)}
          </div>
          <p className="text-xs text-slate-400">
            Binds parameters to physical units and checks state invariants. Strictly decoupled as NOT_IMPLEMENTED (no faked calculations).
          </p>
          <div className="text-xs font-mono bg-slate-950 p-2.5 rounded-xl border border-slate-800 space-y-1 text-slate-400 italic">
            <div>Physical Kernel: <span>NOT_IMPLEMENTED</span></div>
            <div>Execution State: <span>NOT_EXECUTED</span></div>
          </div>
        </div>
      </div>

      {/* Main Workbench Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Input Panel & Scenario Registry */}
        <div className="space-y-6">
          {/* Input & Scenario Selection Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <span>Input & Test Registry</span>
              </h3>
              <span className="text-xs font-mono text-slate-400">{scenarios.length} scenarios</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Filter by Language / Search</label>
                <div className="flex gap-2">
                  <select
                    value={filterLang}
                    onChange={(e) => setFilterLang(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                  >
                    <option value="all">All Langs</option>
                    <option value="ru">Russian (RU)</option>
                    <option value="uk">Ukrainian (UK)</option>
                    <option value="en">English (EN)</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Search test ID or text..."
                    value={filterSearch}
                    onChange={(e) => setFilterSearch(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Select Scenario from JSON Bank</label>
                <select
                  value={selectedScenarioId}
                  onChange={(e) => {
                    setUseCustom(false);
                    setSelectedScenarioId(e.target.value);
                  }}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
                >
                  {filteredScenarios.map((s) => (
                    <option key={s.test_id} value={s.test_id}>
                      [{s.test_id}] ({s.language.toUpperCase()}) {s.input_text.substring(0, 40)}...
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-slate-400">Custom Phrasing Input</label>
                  <button
                    onClick={() => {
                      setUseCustom(!useCustom);
                      if (!useCustom && !customInput) {
                        setCustomInput(currentScenario.input_text);
                      }
                    }}
                    className="text-[11px] text-indigo-400 hover:underline"
                  >
                    {useCustom ? "Use Preset Scenario" : "Edit Custom Prompt"}
                  </button>
                </div>
                {useCustom ? (
                  <textarea
                    rows={3}
                    value={customInput}
                    onChange={(e) => setCustomInput(e.target.value)}
                    placeholder="Enter custom natural language instruction..."
                    className="w-full bg-slate-950 border border-indigo-500/50 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none"
                  />
                ) : (
                  <div className="bg-slate-950 border border-slate-800 p-3 rounded-xl text-xs font-mono text-slate-200">
                    "{currentScenario.input_text}"
                  </div>
                )}
              </div>

              <div className="bg-slate-950 border border-slate-800 p-3 rounded-xl space-y-1 text-xs font-mono">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider">Pass Criteria:</div>
                <div className="text-slate-300">{useCustom ? "Custom prompt active. No preset pass criteria." : currentScenario.pass_criteria}</div>
              </div>
            </div>
          </div>

          {/* Provenance Viewer */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2 border-b border-slate-800 pb-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              <span>Provenance Viewer</span>
            </h3>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Source Category:</span>
                <span className="text-indigo-300 font-bold">
                  {useCustom ? "NOT_AVAILABLE" : currentScenario.expected_structure?.provenance || "EXPLICIT"}
                </span>
              </div>
              {!useCustom && currentScenario.expected_structure?.context_reference ? (
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-[11px]">
                  <div>Context ID: <strong className="text-indigo-400">{currentScenario.expected_structure.context_reference.context_id}</strong></div>
                  <div>Source Type: <strong className="text-slate-300">{currentScenario.expected_structure.context_reference.source_type}</strong></div>
                  <div>Fragment: <strong className="text-slate-300">{currentScenario.expected_structure.context_reference.source_fragment}</strong></div>
                  <div>Inference Basis: <span className="text-slate-400">{currentScenario.expected_structure.context_reference.inference_basis}</span></div>
                  <div>Confidence: <strong className="text-emerald-400">{currentScenario.expected_structure.context_reference.confidence_modifier}</strong></div>
                </div>
              ) : (
                <div className="text-slate-500 italic text-[11px]">
                  {useCustom ? "Analysis status: NOT_EXECUTED" : "No context reference required (EXPLICIT parameter)."}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Center & Right Column: Semantic Structure, Dhatu, DAG & Causality Viewers */}
        <div className="lg:col-span-2 space-y-6">
          {/* Expected Result vs Actual Result Box */}
          <div className="bg-slate-900 border border-indigo-500/40 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-indigo-400" />
                <span>Expected Result vs Actual Analysis Result</span>
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                {useCustom ? "Custom Mode" : `Preset Test: ${currentScenario.test_id}`}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              {/* Expected Result Panel */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="text-indigo-400 font-bold uppercase tracking-wider flex items-center justify-between">
                  <span>EXPECTED RESULT (Registry)</span>
                  <span className="text-[10px] bg-slate-900 px-2 py-0.5 rounded text-slate-300">
                    {useCustom ? "N/A" : currentScenario.expected_status}
                  </span>
                </div>
                {useCustom ? (
                  <p className="text-slate-500 italic">No preset expected result for custom phrasing.</p>
                ) : (
                  <div className="space-y-1 text-slate-300 text-[11px]">
                    <div>Expected Dhatu: <strong className="text-indigo-300">{currentScenario.expected_dhatu.join(", ")}</strong></div>
                    <pre className="bg-slate-900 p-2.5 rounded border border-slate-800 text-indigo-200 overflow-x-auto whitespace-pre-wrap mt-1">
                      {JSON.stringify(currentScenario.expected_structure, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              {/* Actual Result Panel */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="text-amber-400 font-bold uppercase tracking-wider flex items-center justify-between">
                  <span>ACTUAL RESULT (Execution Status)</span>
                  <span className="text-[10px] bg-amber-950/60 text-amber-300 border border-amber-900 px-2 py-0.5 rounded">
                    NOT_EXECUTED
                  </span>
                </div>
                <div className="space-y-1.5 text-[11px] text-slate-400">
                  <div>ANALYSIS STATUS: <strong className="text-amber-400">NOT_EXECUTED</strong></div>
                  <div>SEMANTIC RESULT: <strong className="text-slate-500">NOT_AVAILABLE</strong></div>
                  <div>PHYSICAL VALIDATION: <strong className="text-slate-500">NOT_IMPLEMENTED</strong></div>
                  <p className="text-slate-500 italic pt-1">
                    Live NLP semantic extraction engine is not executed in UI preview. Displays expected registry specifications separately without faking execution.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Semantic Structure & Dhatu Operation Viewers */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Semantic Structure (9 Categories) */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2 border-b border-slate-800 pb-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span>Semantic Structure (9 Categories)</span>
              </h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-400">Detected Operation Type:</span>
                  <span className="text-emerald-300 font-bold">
                    {useCustom
                      ? "NOT_AVAILABLE"
                      : currentScenario.expected_structure?.operation_type ||
                        currentScenario.expected_structure?.action ||
                        currentScenario.expected_structure?.goal ||
                        currentScenario.expected_structure?.constraint ||
                        "GENERAL"}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1">
                  <div className="text-[11px] text-slate-400 uppercase tracking-wider">Structure Payload:</div>
                  <pre className="text-indigo-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {useCustom ? "NOT_AVAILABLE" : JSON.stringify(currentScenario.expected_structure, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* Dhatu Operation Viewer */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2 border-b border-slate-800 pb-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>Dhatu Operation Viewer</span>
              </h3>
              <div className="space-y-3 text-xs font-mono">
                <div>
                  <span className="text-slate-400 block mb-1">Assigned Dhatu Roots:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {useCustom ? (
                      <span className="text-slate-500 italic">NOT_AVAILABLE</span>
                    ) : (
                      currentScenario.expected_dhatu.map((d) => (
                        <span key={d} className="px-2 py-1 bg-indigo-950/80 text-indigo-300 border border-indigo-800 rounded-lg font-bold">
                          {d}
                        </span>
                      ))
                    )}
                  </div>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-[11px] text-slate-300">
                  <div className="text-amber-400 font-semibold">&bull; Decoupled from SOL Roles</div>
                  <div>Dhatu roots do not automatically assign SOURCE, CONSTRAINT, or DISSIPATE roles. Formal Arbiter validates roles independently.</div>
                </div>
              </div>
            </div>
          </div>

          {/* DAG Viewer (Full Completeness) */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
                <GitBranch className="w-4 h-4 text-indigo-400" />
                <span>DAG Causal Pipeline Viewer</span>
              </h3>
              <span className="text-xs font-mono text-slate-400">
                {!useCustom && currentScenario.expected_structure?.dag ? "DAG Active" : "No DAG Structure"}
              </span>
            </div>

            {!useCustom && currentScenario.expected_structure?.dag ? (
              <div className="space-y-3 font-mono text-xs">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Nodes with full properties */}
                  <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
                    <div className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider">
                      DAG Nodes ({currentScenario.expected_structure.dag.nodes.length})
                    </div>
                    <div className="space-y-2">
                      {currentScenario.expected_structure.dag.nodes.map((node: any, idx: number) => (
                        <div key={idx} className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                          <div className="flex justify-between font-bold">
                            <span className="text-slate-200">{node.operation_id}</span>
                            <span className="text-indigo-300 bg-indigo-950 px-1.5 py-0.5 rounded">{node.dhatu_id}</span>
                          </div>
                          <div className="text-slate-400">Type: <span className="text-slate-300">{node.operation_type || "NOT_SPECIFIED"}</span></div>
                          <div>Inputs: <span className="text-slate-300">{node.inputs ? node.inputs.join(", ") : "NOT_SPECIFIED"}</span></div>
                          <div>Outputs: <span className="text-slate-300">{node.outputs ? node.outputs.join(", ") : "NOT_SPECIFIED"}</span></div>
                          <div>Parameters: <span className="text-slate-300">{node.parameters ? JSON.stringify(node.parameters) : "NOT_SPECIFIED"}</span></div>
                          <div>Units: <span className="text-slate-300">{node.units || "NOT_SPECIFIED"}</span></div>
                          <div>Provenance: <span className="text-slate-300">{node.provenance || "NOT_SPECIFIED"}</span></div>
                          <div>Preconditions: <span className="text-slate-300">{node.preconditions || "NOT_SPECIFIED"}</span></div>
                          <div>Postconditions: <span className="text-slate-300">{node.postconditions || "NOT_SPECIFIED"}</span></div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Edges with full properties */}
                  <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
                    <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
                      Directed Edges ({currentScenario.expected_structure.dag.edges.length})
                    </div>
                    <div className="space-y-2">
                      {currentScenario.expected_structure.dag.edges.map((edge: any, idx: number) => (
                        <div key={idx} className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1.5 text-[11px]">
                          <div className="flex items-center space-x-2 text-slate-200 font-bold">
                            <span>{edge.from}</span>
                            <ArrowRight className="w-3 h-3 text-indigo-400" />
                            <span>{edge.to}</span>
                          </div>
                          <div>Relation: <span className="text-emerald-300 font-bold">{edge.relation_type || "NOT_SPECIFIED"}</span></div>
                          <div>Condition: <span className="text-slate-300">{edge.condition || "NOT_SPECIFIED"}</span></div>
                          <div>Causal Basis: <span className="text-slate-300">{edge.causal_basis || "NOT_SPECIFIED"}</span></div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-slate-950 p-6 rounded-xl border border-slate-800 text-center text-slate-400 text-xs font-mono space-y-2">
                <p>No multi-node DAG sequence defined for scenario <strong className="text-indigo-400">{useCustom ? "CUSTOM" : currentScenario.test_id}</strong>.</p>
                <p className="text-[11px] text-slate-500">Single operation or parameter boundary structure.</p>
              </div>
            )}
          </div>

          {/* Causality & Physical Validation Panel */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Causality Viewer (Strict Statuses) */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2 border-b border-slate-800 pb-2">
                <CheckCircle2 className="w-4 h-4 text-indigo-400" />
                <span>Causality Viewer</span>
              </h3>
              <div className="space-y-2 text-xs font-mono text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-400">Causality Type:</span>
                  <span className="text-indigo-300 font-bold">
                    {useCustom
                      ? "NOT_AVAILABLE"
                      : currentScenario.expected_structure?.causal_type || "NO_CAUSAL_RELATION_DECLARED"}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-[11px] text-slate-400">
                  <p className="text-amber-400 font-semibold">&bull; Causality States</p>
                  <p>
                    {currentScenario.expected_structure?.causal_type
                      ? "User/Registry explicitly asserts causal relation. Physical verification status: NOT_VERIFIED."
                      : "No causal relation declared in prompt or fixture. Avoids faking ASSERTED_CAUSAL_RELATION."}
                  </p>
                </div>
              </div>
            </div>

            {/* Physical Validation Panel */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2 border-b border-slate-800 pb-2">
                <Lock className="w-4 h-4 text-indigo-400" />
                <span>Physical Validation Panel</span>
              </h3>
              <div className="space-y-2 text-xs font-mono text-slate-400">
                <div className="flex justify-between">
                  <span>Module Status:</span>
                  <span className="text-slate-400 font-bold">NOT_IMPLEMENTED</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1 text-[11px] text-slate-400">
                  <p className="text-slate-300 font-semibold">&bull; Informational Panel Only</p>
                  <p>Physical unit binding (e.g. 80°C = 353.15K) is verified declaratively. Algorithmic simulation engine is not executed in UI.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
