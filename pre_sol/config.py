"""Configuration and Heuristic Separation for Pre-SOL v0.1.

Contains explicit boundaries between:
- MANDATORY rules (core v0.4.1 invariants, safety barriers, exact text retention)
- PROVISIONAL heuristics (NLP keyword classifiers, qualitative goal indicators)
- UNVERIFIED mappings (direct translation of Pre-SOL findings into kernel diagnostic codes)
"""

from typing import Dict, Set, List
from .models import RuleMaturity

# ==============================================================================
# 1. MANDATORY RULES (Rigorous specification invariants)
# ==============================================================================

# Physical units and dimensions grounded in standard SI/engineering conventions
# (consistent with SOL-Triad v2 UnitRegistry dimensions)
STANDARD_UNIT_DIMENSIONS: Dict[str, str] = {
    # Pressure
    "bar": "pressure",
    "mbar": "pressure",
    "pa": "pressure",
    "kpa": "pressure",
    "mpa": "pressure",
    "psi": "pressure",
    # Time
    "s": "time",
    "sec": "time",
    "second": "time",
    "seconds": "time",
    "m": "time_or_length",  # Ambiguity handled in parser
    "min": "time",
    "minute": "time",
    "minutes": "time",
    "h": "time",
    "hr": "time",
    "hour": "time",
    "hours": "time",
    # Temperature
    "k": "temperature",
    "kelvin": "temperature",
    "c": "temperature",
    "degc": "temperature",
    # Length / Distance
    "meter": "length",
    "meters": "length",
    "km": "length",
    "cm": "length",
    "mm": "length",
    # Mass
    "kg": "mass",
    "g": "mass",
    "mg": "mass",
}

# Dimension conversion factors to base SI units
UNIT_CONVERSIONS: Dict[str, float] = {
    "bar": 100000.0,
    "pa": 1.0,
    "kpa": 1000.0,
    "mpa": 1000000.0,
    "mbar": 100.0,
    "psi": 6894.757,
    "s": 1.0,
    "sec": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "min": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
    "kg": 1.0,
    "g": 0.001,
    "mg": 0.000001,
}

# ==============================================================================
# 2. PROVISIONAL HEURISTICS (Subject to empirical refinement)
# ==============================================================================

# Qualitative / unquantified goal markers (Russian & English)
PROVISIONAL_QUALITATIVE_MARKERS: Set[str] = {
    "быстрее", "как можно быстрее", "максимально быстро", "ускорить",
    "дешевле", "как можно дешевле", "оптимизировать", "улучшить",
    "повысить эффективность", "сделать лучше", "снизить затраты",
    "качественно", "безопасно", "надежно", "наилучшим образом",
    "faster", "as fast as possible", "cheaper", "optimize", "improve",
    "better", "safely", "reliably", "maximize throughput", "minimize cost"
}

# Mutation / side-effect / external execution indicators
PROVISIONAL_MUTATION_VERBS: Set[str] = {
    "выполнить", "выполнять", "выполни", "выполняй",
    "применить", "применять", "примени", "применяй",
    "записать", "записывать", "запиши", "записывай",
    "перезаписать", "перезаписывать", "перезапиши", "перезаписывай",
    "изменить", "изменять", "измени", "изменяй",
    "удалить", "удалять", "удали", "удаляй",
    "сбросить", "сбрасывать", "сбрось", "сбрасывай",
    "переключить", "переключать", "переключи", "переключай",
    "активировать", "активируй", "деактивировать", "деактивируй",
    "открыть", "открывать", "открой", "открывай",
    "закрыть", "закрывать", "закрой", "закрывай",
    "запустить", "запускать", "запусти", "запускай",
    "подать", "подавать", "подай", "подавай",
    "выкатить", "выкатывать", "выкати", "выкатывай",
    "стереть", "стирать", "сотри", "стирай",
    "извлечь", "извлекать", "извлеки", "извлекай",
    "остановить", "останавливать", "останови", "останавливай",
    "execute", "executing", "apply", "applying", "mutate", "mutating", "overwrite", "overwriting",
    "modify", "modifying", "delete", "deleting", "drop", "dropping", "reset", "resetting",
    "switch", "switching", "activate", "deactivate", "trigger", "launch", "deploy", "stop"
}

# Hypothesis / conjectural framing markers
PROVISIONAL_HYPOTHESIS_MARKERS: Set[str] = {
    "предположим", "если", "допустим", "гипотеза", "что если", "возможно",
    "вероятно", "рассмотрим случай", "представим", "в предположении",
    "suppose", "assume", "hypothesis", "what if", "maybe", "perhaps",
    "let us assume", "in case of", "conjecture"
}

# Fact assertion markers (claims about actual state of the world)
PROVISIONAL_FACT_ASSERTION_MARKERS: Set[str] = {
    "известно, что", "по данным", "измерено", "факт:", "в системе сейчас",
    "текущее значение", "датчик показывает", "зафиксировано", "точно равно",
    "it is known that", "measured", "sensor shows", "current value is",
    "fact:", "recorded", "the system is currently"
}

# Circular reasoning connectors (citing the conclusion as premise or vice versa)
PROVISIONAL_CIRCULAR_PATTERNS: List[tuple] = [
    # (premise_indicator, conclusion_indicator)
    ("потому что", "следовательно"),
    ("так как", "поэтому"),
    ("поскольку", "значит"),
]

# ==============================================================================
# 3. UNVERIFIED KERNEL MAPPINGS
# ==============================================================================

# Mapping from Pre-SOL Diagnostic findings to SOL-Triad v2 DiagnosticCodes
# (Marked UNVERIFIED because kernel integration is out-of-scope for v0.1 autonomous prototype)
UNVERIFIED_KERNEL_DIAGNOSTIC_MAP = {
    "PHYSICAL_UNIT_INCOMPATIBILITY": "UNIT_INCOMPATIBLE",
    "LOGICAL_CONTRADICTION": "INSUFFICIENT_CONSTRAINT_SET",
    "MUTATION_ATTEMPT": "STATE_PROTECTED_PARAM_MUTATED",
    "CIRCULAR_REASONING": "INFERENCE_CIRCULAR_DEPENDENCY",
}
