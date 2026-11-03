"""
Finance Profile FX Adapter v1.
Dedicated external layer connecting currency operations with SOL-Triad Engine v0.4.0.

Core Architectural Rules:
1. Strict separation of trust boundaries:
   - TaskRequest: Untrusted user/agent intent, operation parameters, and evidence references.
   - HostPolicy: Authoritative host invariants (ledger balance, overdraft limits, host clock).
2. Deterministic arithmetic validation happens BEFORE calling SOL-Triad Engine.
3. If claimed delta does not match calculated FX conversion, the request is REJECTED
   immediately without calling the engine.
4. No Self-Minting: The adapter NEVER creates or registers evidence records in the host registry.
   Quotes must already exist in the authoritative host registry; missing quotes are rejected.
5. Account Binding: task.payer_account MUST match policy.account_id.
6. Payload Hash Semantics: SOL-Triad v0.4.0 compares opaque string hash tokens for equality;
   it does not cryptographically compute or canonically serialize payloads.
7. SOL-Triad 'PASS' verdict is strictly an epistemic and structural coherence verdict
   and NEVER grants permission or authorization to execute the payment.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Union
import math
import time
import warnings

from sol_triad import (
    SolTriadJsonAdapter,
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
)
from sol_triad.evidence import EvidenceRegistryOracle


class FxDirection(str, Enum):
    DIRECT = "DIRECT"      # base_currency is from_ccy (1 from_ccy = rate quote_ccy)
    INDIRECT = "INDIRECT"  # base_currency is to_ccy (1 to_ccy = rate from_ccy)


@dataclass(frozen=True)
class FxQuote:
    """External verifiable exchange rate quote structure."""
    quote_id: str
    base_currency: str
    quote_currency: str
    rate: float
    timestamp_sec: float
    max_age_sec: float = 300.0
    payload_hash: Optional[str] = None
    source_oracle: str = "oracle:default"


@dataclass
class FxCalculationResult:
    """Result of external FX conversion verification."""
    is_valid: bool
    expected_delta: Optional[float] = None
    direction: Optional[FxDirection] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class TaskRequest:
    """
    Untrusted task request submitted by an agent or client.
    Contains intent, operation parameters, claimed delta, and quote reference.
    CRITICAL: Does NOT contain trusted balance, limits, or host evaluation time.
    """
    request_id: str
    payer_account: str
    operation_amount: float
    operation_currency: str
    ledger_currency: str
    claimed_state_delta: float
    quote_id: str
    rounding_precision: int = 2
    tolerance: float = 1e-4
    requested_loss_domain: str = "funds_transfer"


@dataclass(frozen=True)
class HostPolicy:
    """
    Authoritative host boundary policy and trusted ledger state.
    Configured solely by the trusted host environment (banking backend / Action Gate).
    """
    account_id: str
    initial_balance: float
    min_balance_bound: float = 0.0
    host_evaluation_time: float = field(default_factory=time.time)
    authorized_quote_domain: str = "fx_rates"
    authorized_loss_domain: str = "funds_transfer"


@dataclass
class FinancePaymentRequest:
    """
    Legacy payment request contract (v0.4.0-legacy).
    Deprecated: mixes untrusted agent claims with trusted host policy.
    Maintained solely for transition; converts only untrusted parameters to TaskRequest.
    """
    request_id: str
    payer_account: str
    operation_amount: float
    operation_currency: str
    ledger_currency: str
    claimed_state_delta: float
    quote: Optional[FxQuote]
    initial_balance: float
    min_balance_bound: float = 0.0
    rounding_precision: int = 2
    tolerance: float = 1e-4
    requested_loss_domain: str = "funds_transfer"

    def __post_init__(self):
        warnings.warn(
            "FinancePaymentRequest is deprecated and will be removed in v0.5.0. "
            "Use TaskRequest instead. Note that initial_balance and min_balance_bound "
            "in FinancePaymentRequest are ignored; HostPolicy must be provided separately.",
            DeprecationWarning,
            stacklevel=2,
        )

    def to_task_request(self) -> TaskRequest:
        """
        Converts to TaskRequest extracting only untrusted agent parameters.
        CRITICAL SECURITY INVARIANT:
        initial_balance and min_balance_bound are intentionally discarded here;
        they MUST NOT be converted into trusted HostPolicy.
        """
        quote_id = self.quote.quote_id if self.quote is not None else ""
        return TaskRequest(
            request_id=self.request_id,
            payer_account=self.payer_account,
            operation_amount=self.operation_amount,
            operation_currency=self.operation_currency,
            ledger_currency=self.ledger_currency,
            claimed_state_delta=self.claimed_state_delta,
            quote_id=quote_id,
            rounding_precision=self.rounding_precision,
            tolerance=self.tolerance,
            requested_loss_domain=self.requested_loss_domain,
        )


@dataclass
class FinanceEvaluationResult:
    """Outcome of Finance Profile evaluation."""
    request_id: str
    status: str  # "ADAPTER_REJECTED" | "ENGINE_EVALUATED"
    rejection_reason: Optional[str] = None
    error_code: Optional[str] = None
    engine_verdict: Optional[str] = None
    engine_report: Optional[Dict[str, Any]] = None
    execution_permitted: bool = False  # GUARANTEE: Never True automatically!
    message: str = ""


def calculate_fx_delta(
    operation_amount: float,
    from_ccy: str,
    to_ccy: str,
    quote: Optional[FxQuote],
    rounding_precision: int = 2,
) -> FxCalculationResult:
    """
    Computes expected local balance delta from foreign currency operation.
    Enforces strict currency pair consistency and direction.
    """
    if quote is None:
        return FxCalculationResult(
            is_valid=False,
            error_code="MISSING_QUOTE",
            error_message="No FX quote provided for cross-currency operation",
        )

    if operation_amount <= 0:
        return FxCalculationResult(
            is_valid=False,
            error_code="INVALID_AMOUNT",
            error_message=f"Operation amount must be positive, got {operation_amount}",
        )

    if quote.rate <= 0 or math.isnan(quote.rate) or math.isinf(quote.rate):
        return FxCalculationResult(
            is_valid=False,
            error_code="INVALID_FX_RATE",
            error_message=f"FX rate must be positive and finite, got {quote.rate}",
        )

    norm_from = from_ccy.strip().upper()
    norm_to = to_ccy.strip().upper()
    quote_base = quote.base_currency.strip().upper()
    quote_target = quote.quote_currency.strip().upper()

    # Case 1: Same currency (no FX needed)
    if norm_from == norm_to:
        raw_delta = -operation_amount
        rounded_delta = round(raw_delta, rounding_precision)
        return FxCalculationResult(
            is_valid=True,
            expected_delta=rounded_delta,
            direction=FxDirection.DIRECT,
        )

    # Case 2: Direct quotation: from_ccy is base (e.g., EUR/UAH with rate 40.0)
    # 1 EUR = 40.0 UAH -> 100 EUR = 4000 UAH
    if quote_base == norm_from and quote_target == norm_to:
        raw_delta = -(operation_amount * quote.rate)
        rounded_delta = round(raw_delta, rounding_precision)
        return FxCalculationResult(
            is_valid=True,
            expected_delta=rounded_delta,
            direction=FxDirection.DIRECT,
        )

    # Case 3: Indirect quotation: to_ccy is base (e.g., UAH/EUR with rate 0.025)
    # 1 UAH = 0.025 EUR -> 100 EUR = 100 / 0.025 = 4000 UAH
    if quote_base == norm_to and quote_target == norm_from:
        raw_delta = -(operation_amount / quote.rate)
        rounded_delta = round(raw_delta, rounding_precision)
        return FxCalculationResult(
            is_valid=True,
            expected_delta=rounded_delta,
            direction=FxDirection.INDIRECT,
        )

    # Currency pair does not match operation
    return FxCalculationResult(
        is_valid=False,
        error_code="CURRENCY_PAIR_MISMATCH",
        error_message=(
            f"Quote pair {quote_base}/{quote_target} does not match operation pair {norm_from}/{norm_to}"
        ),
    )


class FinanceFxAdapter:
    """
    Finance Profile FX Adapter v1.
    Decoupled Action Gate between financial payment instructions and SOL-Triad Engine.
    """

    def __init__(self, adapter: Optional[SolTriadJsonAdapter] = None):
        self.engine_adapter = adapter if adapter is not None else SolTriadJsonAdapter()

    def process_payment(
        self,
        task: Union[TaskRequest, FinancePaymentRequest],
        policy: HostPolicy,
        host_registry: EvidenceRegistryOracle,
    ) -> FinanceEvaluationResult:
        """
        Validates FX arithmetic and evaluates payment through SOL-Triad Engine.

        Enforces:
        1. Explicit HostPolicy validation (rejects insecure legacy invocations without HostPolicy).
        2. Account binding check (task.payer_account == policy.account_id).
        3. Strict quote resolution from host_registry (zero self-minting).
        4. Independent arithmetic validation before calling core engine.
        5. Grounding in core SOL-Triad Engine using trusted host policy invariants.
        """
        # Ensure policy is valid HostPolicy
        if not isinstance(policy, HostPolicy):
            raise TypeError(
                "Safe evaluation requires an explicit HostPolicy provided by the host. "
                "Untrusted payment requests cannot synthesize trusted balance or limits."
            )

        # Normalize task request (discarding any untrusted policy fields if legacy request)
        if isinstance(task, FinancePaymentRequest):
            task_req = task.to_task_request()
        elif isinstance(task, TaskRequest):
            task_req = task
        else:
            raise TypeError(f"Expected TaskRequest or FinancePaymentRequest, got {type(task)}")

        # Step 1: Validate account binding
        if task_req.payer_account != policy.account_id:
            reason = (
                f"Account mismatch: task payer '{task_req.payer_account}' "
                f"does not match policy account '{policy.account_id}'"
            )
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=reason,
                error_code="ACCOUNT_MISMATCH",
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {reason}",
            )

        # Step 1b: Validate requested loss domain against policy authorized domain
        if task_req.requested_loss_domain != policy.authorized_loss_domain:
            reason = (
                f"Unauthorized loss domain: requested '{task_req.requested_loss_domain}' "
                f"is not authorized by host policy '{policy.authorized_loss_domain}'"
            )
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=reason,
                error_code="UNAUTHORIZED_LOSS_DOMAIN",
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {reason}",
            )

        # Step 2: Validate quote reference against trusted host registry (No Self-Minting!)
        if not task_req.quote_id:
            reason = "No FX quote ID provided for cross-currency operation"
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=reason,
                error_code="MISSING_QUOTE",
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {reason}",
            )

        evidence_record = host_registry.get_record(task_req.quote_id)
        if evidence_record is None:
            reason = f"Evidence quote '{task_req.quote_id}' not found in authoritative host registry"
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=reason,
                error_code="EVIDENCE_NOT_FOUND",
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {reason}",
            )

        # Step 2b: Validate evidence domain against policy authorized domain
        if evidence_record.domain != policy.authorized_quote_domain:
            reason = (
                f"Quote domain mismatch: record domain '{evidence_record.domain}' "
                f"does not match policy authorized domain '{policy.authorized_quote_domain}'"
            )
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=reason,
                error_code="EVIDENCE_DOMAIN_MISMATCH",
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {reason}",
            )

        # Resolve trusted quote parameters from record metadata
        quote_rate = float(evidence_record.metadata.get("rate", 0.0))
        quote_base = str(evidence_record.metadata.get("base_currency") or evidence_record.metadata.get("base_ccy", ""))
        quote_target = str(evidence_record.metadata.get("quote_currency") or evidence_record.metadata.get("quote_ccy", ""))
        quote_oracle = str(evidence_record.metadata.get("oracle", "oracle:default"))
        max_age_sec = float(evidence_record.metadata.get("max_age_sec", 300.0))

        trusted_quote = FxQuote(
            quote_id=evidence_record.evidence_id,
            base_currency=quote_base,
            quote_currency=quote_target,
            rate=quote_rate,
            timestamp_sec=evidence_record.timestamp_sec,
            max_age_sec=max_age_sec,
            payload_hash=evidence_record.payload_hash,
            source_oracle=quote_oracle,
        )

        # Step 3: Validate FX conversion arithmetic
        fx_calc = calculate_fx_delta(
            operation_amount=task_req.operation_amount,
            from_ccy=task_req.operation_currency,
            to_ccy=task_req.ledger_currency,
            quote=trusted_quote,
            rounding_precision=task_req.rounding_precision,
        )

        if not fx_calc.is_valid:
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=fx_calc.error_message,
                error_code=fx_calc.error_code,
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {fx_calc.error_message}",
            )

        expected_delta = fx_calc.expected_delta
        assert expected_delta is not None

        # Step 4: Compare claimed state_delta with calculated expected delta
        delta_diff = abs(task_req.claimed_state_delta - expected_delta)
        if delta_diff > task_req.tolerance:
            reason = (
                f"Arithmetic mismatch: claimed delta {task_req.claimed_state_delta} "
                f"does not match calculated FX delta {expected_delta} (diff: {delta_diff:.6f})"
            )
            return FinanceEvaluationResult(
                request_id=task_req.request_id,
                status="ADAPTER_REJECTED",
                rejection_reason=reason,
                error_code="ARITHMETIC_MISMATCH",
                execution_permitted=False,
                message=f"[ADAPTER_REJECTION] {reason}",
            )

        # Step 5: Assemble canonical SOL-Triad JSON request
        # Invariants (balance, bounds, domain authority) come strictly from HostPolicy.
        # Note: units: {} is used for compatibility with UnitRegistry scalar validation.
        # Note on payload_hash: SOL-Triad Engine compares opaque string hash tokens for equality;
        # it does not perform cryptographic hashing or canonical serialization of payloads.
        triad_request = {
            "request_id": task_req.request_id,
            "protocol_version": "0.4.0",
            "source": {
                "evidence_id": trusted_quote.quote_id,
                "authority_domain": [policy.authorized_quote_domain],
                "granted_scope": [policy.account_id],
                "granted_loss_domains": [policy.authorized_loss_domain],
                "epistemic_type": "FACT",
                "timestamp_sec": trusted_quote.timestamp_sec,
                "max_age_sec": trusted_quote.max_age_sec,
                "payload_hash": trusted_quote.payload_hash,
            },
            "constraint": {
                "domain_scope": [policy.authorized_quote_domain],
                "target_objects": [policy.account_id],
                "protected_set": [],
                "min_bounds": {policy.account_id: policy.min_balance_bound},
                "units": {},
            },
            "dissipate": {
                "loss_domain": [task_req.requested_loss_domain],
                "target_states": ["settled"],
                "side_effects": [],
                "resource_cost": {},
                "state_delta": {policy.account_id: task_req.claimed_state_delta},
                "units": {},
            },
            "initial_state": {
                "current_values": {policy.account_id: policy.initial_balance},
                "units": {},
            },
        }

        # Step 6: Invoke core SOL-Triad Engine through host boundary
        engine_response = self.engine_adapter.evaluate_json(
            request_input=triad_request,
            registry=host_registry,
            evaluation_time=policy.host_evaluation_time,
        )

        verdict = engine_response.get("verdict", "FAIL")

        return FinanceEvaluationResult(
            request_id=task_req.request_id,
            status="ENGINE_EVALUATED",
            engine_verdict=verdict,
            engine_report=engine_response,
            # CRITICAL SECURITY INVARIANT:
            # An engine PASS is NEVER an execution permit! Execution belongs to Execution Controller.
            execution_permitted=False,
            message=f"Engine evaluation completed with verdict: {verdict}",
        )
