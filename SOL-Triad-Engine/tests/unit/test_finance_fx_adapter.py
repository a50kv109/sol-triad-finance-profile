"""
Unit Tests for Finance Profile FX Adapter v1.
Verifies arithmetic validation, boundary enforcement, and integration with SOL-Triad Engine.
Compatible with standard python runner and pytest.
"""

import time

from finance_profile import (
    FinanceFxAdapter,
    TaskRequest,
    HostPolicy,
    FinancePaymentRequest,
    FxQuote,
    calculate_fx_delta,
    FxDirection,
)
from sol_triad import (
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
)


def get_current_time():
    # Unix timestamp corresponding to 2025-02-19T21:21:40 UTC
    return 1740000100.0


def register_direct_quote(registry: InMemoryEvidenceRegistry, current_time: float) -> str:
    # 1 EUR = 40.0 UAH
    quote_id = "quote-eur-uah-001"
    registry.register(EvidenceRecord(
        evidence_id=quote_id,
        domain="fx_rates",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
        payload_hash="opaque-token-eur-uah-01",
        metadata={
            "base_currency": "EUR",
            "quote_currency": "UAH",
            "rate": 40.0,
            "max_age_sec": 300.0,
            "oracle": "oracle:ecb",
        }
    ))
    return quote_id


def register_indirect_quote(registry: InMemoryEvidenceRegistry, current_time: float) -> str:
    # 1 UAH = 0.025 EUR (inverse of 40.0)
    quote_id = "quote-uah-eur-002"
    registry.register(EvidenceRecord(
        evidence_id=quote_id,
        domain="fx_rates",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
        payload_hash="opaque-token-uah-eur-02",
        metadata={
            "base_currency": "UAH",
            "quote_currency": "EUR",
            "rate": 0.025,
            "max_age_sec": 300.0,
            "oracle": "oracle:ecb",
        }
    ))
    return quote_id


def get_host_registry():
    return InMemoryEvidenceRegistry()


# --- TEST 1: Корректная конвертация (Direct) ---
def test_fx_adapter_correct_conversion_pass(host_registry, current_time):
    """Test 1: 100 EUR * 40.0 UAH/EUR = -4000.0 UAH. Engine returns PASS."""
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-001",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        min_balance_bound=0.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "PASS"
    assert res.rejection_reason is None
    # Crucial security invariant: PASS does NOT grant execution permit
    assert res.execution_permitted is False
    assert res.engine_report is not None
    assert res.engine_report["simulated_values"]["acc_uah_main"] == 6000.0


# --- TEST 2: Неверная дельта при достаточном балансе (Mismatch Attack / Bug) ---
def test_fx_adapter_mismatch_rejected_without_engine(host_registry, current_time):
    """
    Test 2: 100 EUR * 40 UAH/EUR = 4000 UAH.
    Agent claims delta = -4500.0 UAH. Account balance is 10000 UAH.
    Adapter MUST reject before calling SOL-Triad engine!
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-002-mismatch",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4500.0,  # INCORRECT DELTA!
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        min_balance_bound=0.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "ARITHMETIC_MISMATCH"
    assert "Arithmetic mismatch" in res.rejection_reason
    assert res.engine_report is None  # SOL-Triad was NOT called!
    assert res.execution_permitted is False


# --- TEST 3: Обратное направление котировки (Indirect) ---
def test_fx_adapter_indirect_quotation(host_registry, current_time):
    """
    Test 3: Indirect quote: 1 UAH = 0.025 EUR.
    Operation is 100 EUR. Expected delta: -(100 / 0.025) = -4000.0 UAH.
    """
    quote_id = register_indirect_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-003-indirect",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        min_balance_bound=0.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "PASS"
    assert res.engine_report["simulated_values"]["acc_uah_main"] == 6000.0


# --- TEST 4: Неправильная валютная пара ---
def test_fx_adapter_currency_pair_mismatch(current_time, host_registry):
    """
    Test 4: Operation is EUR -> UAH, but quote provided is USD / GBP.
    Adapter must reject with CURRENCY_PAIR_MISMATCH.
    """
    quote_id = "quote-usd-gbp-999"
    host_registry.register(EvidenceRecord(
        evidence_id=quote_id,
        domain="fx_rates",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
        metadata={
            "base_currency": "USD",
            "quote_currency": "GBP",
            "rate": 0.79,
        }
    ))
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-004-pair-mismatch",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-79.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "CURRENCY_PAIR_MISMATCH"
    assert "does not match operation pair" in res.rejection_reason


# --- TEST 5: Округление на границе допустимой точности ---
def test_fx_adapter_rounding_precision():
    """
    Test 5: Operation: 123.456 EUR * 41.2345 UAH/EUR = 5090.643692...
    Rounded to 2 decimals = -5090.65 UAH.
    """
    quote = FxQuote(
        quote_id="quote-precision-01",
        base_currency="EUR",
        quote_currency="UAH",
        rate=41.2345,
        timestamp_sec=1740000000.0,
    )
    calc = calculate_fx_delta(
        operation_amount=123.456,
        from_ccy="EUR",
        to_ccy="UAH",
        quote=quote,
        rounding_precision=2,
    )
    assert calc.is_valid is True
    expected = round(-(123.456 * 41.2345), 2)
    assert calc.expected_delta == expected


# --- TEST 6: Отсутствующая котировка (quote_id пустой) ---
def test_fx_adapter_missing_quote(host_registry, current_time):
    """Test 6: Quote is empty -> rejected with MISSING_QUOTE."""
    adapter = FinanceFxAdapter()
    task = TaskRequest(
        request_id="req-fx-006-no-quote",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id="",
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "MISSING_QUOTE"


# --- TEST 7: Устаревшая котировка (Проверка через EvidenceValidator) ---
def test_fx_adapter_stale_quote_review(host_registry, current_time):
    """
    Test 7: Quote is 350s old (max_age is 300s).
    Adapter arithmetic passes (-4000.0 UAH), but SOL-Triad Engine EvidenceValidator
    returns REVIEW with TEMPORAL_STALE.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    eval_time = current_time + 350.0  # Host evaluation time is 350s after current_time

    task = TaskRequest(
        request_id="req-fx-007-stale",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        min_balance_bound=0.0,
        host_evaluation_time=eval_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "REVIEW"
    assert any(d["code"] == "TEMPORAL_STALE" for d in res.engine_report["diagnostics"])
    assert res.execution_permitted is False


# --- TEST 8: Недостаточный остаток на счёте (min_bounds breach) ---
def test_fx_adapter_insufficient_funds_fail(host_registry, current_time):
    """
    Test 8: Arithmetic is valid (-4000 UAH), but host policy initial balance is only 3000 UAH.
    Simulated balance = -1000 UAH < min_bound (0.0). Engine returns FAIL.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-008-insufficient",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=3000.0,  # 3000 - 4000 = -1000 < 0
        min_balance_bound=0.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "FAIL"
    assert any(d["code"] == "STATE_MIN_BOUND_BREACH" for d in res.engine_report["diagnostics"])
    assert res.execution_permitted is False


# --- TEST 9: Устранение Self-Minting и отсутствие мутации реестра ---
def test_no_self_minting_unregistered_quote_rejected(current_time):
    """
    Test 9: Agent requests an unregistered quote_id.
    Host registry is completely empty (count = 0).
    Adapter MUST reject with EVIDENCE_NOT_FOUND and MUST NOT register anything in the host registry!
    """
    empty_registry = InMemoryEvidenceRegistry()
    assert empty_registry.count() == 0

    adapter = FinanceFxAdapter()
    task = TaskRequest(
        request_id="req-fx-009-unregistered",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id="quote-nonexistent-999",
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, empty_registry)

    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "EVIDENCE_NOT_FOUND"
    assert "not found in authoritative host registry" in res.rejection_reason
    # CRITICAL INVARIANT: The registry was NOT mutated! Self-minting is blocked.
    assert empty_registry.count() == 0


# --- TEST 10: Отказ при несовпадении аккаунта (Account Mismatch) ---
def test_account_mismatch_rejected(host_registry, current_time):
    """
    Test 10: Task payer_account ('acc_attacker') does not match policy account ('acc_victim').
    Adapter MUST reject immediately with ACCOUNT_MISMATCH without invoking the engine.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-010-account-spoof",
        payer_account="acc_attacker",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_victim",
        initial_balance=10000.0,
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "ACCOUNT_MISMATCH"
    assert "Account mismatch" in res.rejection_reason
    assert res.engine_report is None


# --- TEST 11: Невозможность переопределения баланса и лимитов из запроса ---
def test_policy_balance_and_limit_cannot_be_overridden_by_request(host_registry, current_time):
    """
    Test 11: Agent sends legacy FinancePaymentRequest claiming initial_balance=1,000,000 UAH
    and min_balance_bound=-500,000 UAH.
    However, the authoritative HostPolicy has initial_balance=100 UAH and min_balance_bound=0.0 UAH.
    Adapter MUST use HostPolicy values. Engine must FAIL with STATE_MIN_BOUND_BREACH.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    legacy_request = FinancePaymentRequest(
        request_id="req-fx-011-override-attempt",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote=FxQuote(
            quote_id=quote_id,
            base_currency="EUR",
            quote_currency="UAH",
            rate=40.0,
            timestamp_sec=current_time - 10.0,
        ),
        # Agent attempts to declare immense balance and negative floor
        initial_balance=1_000_000.0,
        min_balance_bound=-500_000.0,
    )

    trusted_policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=100.0,       # Real ledger balance is only 100 UAH
        min_balance_bound=0.0,       # Strict zero-overdraft
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(legacy_request, trusted_policy, host_registry)

    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "FAIL"
    # Proves the engine evaluated against 100 UAH, NOT 1,000,000 UAH!
    assert any(d["code"] == "STATE_MIN_BOUND_BREACH" for d in res.engine_report["diagnostics"])
    assert res.engine_report["simulated_values"]["acc_uah_main"] == -3900.0


# --- TEST 12: Время оценки строго контролируется хостом ---
def test_host_evaluation_time_strictly_enforced(host_registry, current_time):
    """
    Test 12: Quote was created at current_time - 10s.
    Host sets policy.host_evaluation_time to current_time + 400s.
    Engine evaluates temporal difference against policy.host_evaluation_time,
    returning TEMPORAL_STALE (REVIEW).
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-012-time-test",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        host_evaluation_time=current_time + 400.0,  # 410s after quote creation
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "REVIEW"
    assert any(d["code"] == "TEMPORAL_STALE" for d in res.engine_report["diagnostics"])


# --- TEST 13: Безопасность обратной совместимости (Insecure Legacy Invocation Rejected) ---
def test_legacy_request_requires_explicit_host_policy(host_registry, current_time):
    """
    Test 13: Invoking process_payment without a valid HostPolicy raises TypeError.
    This guarantees that callers cannot bypass host policy injection.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    legacy_req = FinancePaymentRequest(
        request_id="req-fx-013-legacy-type-check",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote=FxQuote(
            quote_id=quote_id,
            base_currency="EUR",
            quote_currency="UAH",
            rate=40.0,
            timestamp_sec=current_time - 10.0,
        ),
        initial_balance=5000.0,
    )

    # Calling with invalid policy type must raise TypeError
    try:
        adapter.process_payment(legacy_req, None, host_registry)  # type: ignore
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "Safe evaluation requires an explicit HostPolicy" in str(e)


# --- TEST 14: Отказ по несовпадению домена котировки на уровне адаптера ---
def test_quote_domain_mismatch_rejected(host_registry, current_time):
    """
    Test 14: Evidence record domain in registry is 'market_data_equities',
    while policy requires 'fx_rates'.
    Adapter MUST reject with EVIDENCE_DOMAIN_MISMATCH before calling engine.
    """
    quote_id = "quote-equity-wrong-domain"
    host_registry.register(EvidenceRecord(
        evidence_id=quote_id,
        domain="market_data_equities",  # Wrong domain!
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
        metadata={
            "base_currency": "EUR",
            "quote_currency": "UAH",
            "rate": 40.0,
        }
    ))
    adapter = FinanceFxAdapter()
    task = TaskRequest(
        request_id="req-fx-014-domain-mismatch",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        authorized_quote_domain="fx_rates",
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)

    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "EVIDENCE_DOMAIN_MISMATCH"
    assert "Quote domain mismatch" in res.rejection_reason
    assert res.engine_report is None


# --- TEST 15: Проверка DeprecationWarning для FinancePaymentRequest ---
def test_legacy_request_triggers_deprecation_warning(current_time):
    """
    Test 15: Creating FinancePaymentRequest triggers a DeprecationWarning,
    informing developer that TaskRequest and HostPolicy must be used.
    """
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        req = FinancePaymentRequest(
            request_id="req-depr-check",
            payer_account="acc_uah_main",
            operation_amount=100.0,
            operation_currency="EUR",
            ledger_currency="UAH",
            claimed_state_delta=-4000.0,
            quote=None,
            initial_balance=1000.0,
        )
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert "FinancePaymentRequest is deprecated" in str(w[-1].message)


# --- TEST 16: Блокировка инъекции evaluation_time через прямой JSON ---
def test_direct_json_evaluation_time_injection_rejected():
    """
    Test 16: An untrusted client submits raw JSON directly to SolTriadJsonAdapter
    containing 'evaluation_time'. The adapter MUST unconditionally reject with
    STRUCTURAL_DEFECT and FAIL, even if host arguments are also supplied.
    """
    from sol_triad import SolTriadJsonAdapter
    adapter = SolTriadJsonAdapter()
    malicious_json = {
        "request_id": "malicious-time-spoof",
        "protocol_version": "0.4.0",
        "evaluation_time": 9999999999.0,  # Smuggled future timestamp!
        "source": {
            "evidence_id": "ev-01",
            "authority_domain": ["fx_rates"],
            "granted_scope": ["acc_01"],
            "granted_loss_domains": ["funds_transfer"],
            "epistemic_type": "FACT",
            "timestamp_sec": 1740000000.0,
        },
        "constraint": {
            "domain_scope": ["fx_rates"],
            "target_objects": ["acc_01"],
            "protected_set": [],
            "units": {},
        },
        "dissipate": {
            "loss_domain": ["funds_transfer"],
            "target_states": ["settled"],
            "side_effects": [],
            "resource_cost": {},
            "state_delta": {"acc_01": -100.0},
            "units": {},
        },
        "initial_state": {
            "current_values": {"acc_01": 1000.0},
            "units": {},
        },
    }

    # Calling evaluate_json with injected evaluation_time in JSON must fail unconditionally
    res = adapter.evaluate_json(malicious_json)
    assert res["verdict"] == "FAIL"
    assert any("Direct injection of trusted fields" in d["message"] for d in res["diagnostics"])
    assert any(d["code"] == "STRUCTURAL_DEFECT" for d in res["diagnostics"])

    # Even if host parameters are passed, inline injection is strictly rejected
    res2 = adapter.evaluate_json(malicious_json, evaluation_time=1740000000.0)
    assert res2["verdict"] == "FAIL"
    assert any(d["code"] == "STRUCTURAL_DEFECT" for d in res2["diagnostics"])


# --- TEST 17: Блокировка инъекции evidence_records через прямой JSON ---
def test_direct_json_evidence_records_injection_rejected():
    """
    Test 17: An untrusted client submits raw JSON containing inline 'evidence_records'.
    The adapter MUST unconditionally reject with STRUCTURAL_DEFECT and FAIL.
    """
    from sol_triad import SolTriadJsonAdapter
    adapter = SolTriadJsonAdapter()
    malicious_json = {
        "request_id": "malicious-evidence-spoof",
        "protocol_version": "0.4.0",
        "evidence_records": [  # Self-minting attempt via raw JSON!
            {
                "evidence_id": "fake-quote-01",
                "domain": "fx_rates",
                "epistemic_status": "FACT",
                "timestamp_sec": 1740000000.0,
            }
        ],
        "source": {
            "evidence_id": "fake-quote-01",
            "authority_domain": ["fx_rates"],
            "granted_scope": ["acc_01"],
            "granted_loss_domains": ["funds_transfer"],
            "epistemic_type": "FACT",
            "timestamp_sec": 1740000000.0,
        },
        "constraint": {
            "domain_scope": ["fx_rates"],
            "target_objects": ["acc_01"],
            "protected_set": [],
            "units": {},
        },
        "dissipate": {
            "loss_domain": ["funds_transfer"],
            "target_states": ["settled"],
            "side_effects": [],
            "resource_cost": {},
            "state_delta": {"acc_01": -100.0},
            "units": {},
        },
        "initial_state": {
            "current_values": {"acc_01": 1000.0},
            "units": {},
        },
    }

    res = adapter.evaluate_json(malicious_json)
    assert res["verdict"] == "FAIL"
    assert any("Direct injection of trusted fields" in d["message"] for d in res["diagnostics"])
    assert any(d["code"] == "STRUCTURAL_DEFECT" for d in res["diagnostics"])


# --- TEST 18: Прямой JSON-вызов без inline-полей работает с хост-параметрами ---
def test_direct_json_safe_payload_with_host_parameters(current_time):
    """
    Test 18: Client passes clean JSON without evaluation_time or evidence_records.
    Host parameters evaluation_time and registry are passed explicitly to evaluate_json.
    Request succeeds.
    """
    from sol_triad import SolTriadJsonAdapter
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="ev-valid-01",
        domain="fx_rates",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=current_time - 10.0,
    ))
    adapter = SolTriadJsonAdapter(default_registry=reg)

    clean_json = {
        "request_id": "clean-host-json-req",
        "protocol_version": "0.4.0",
        "source": {
            "evidence_id": "ev-valid-01",
            "authority_domain": ["fx_rates"],
            "granted_scope": ["acc_01"],
            "granted_loss_domains": ["funds_transfer"],
            "epistemic_type": "FACT",
            "timestamp_sec": current_time - 10.0,
        },
        "constraint": {
            "domain_scope": ["fx_rates"],
            "target_objects": ["acc_01"],
            "protected_set": [],
            "units": {},
        },
        "dissipate": {
            "loss_domain": ["funds_transfer"],
            "target_states": ["settled"],
            "side_effects": [],
            "resource_cost": {},
            "state_delta": {"acc_01": -100.0},
            "units": {},
        },
        "initial_state": {
            "current_values": {"acc_01": 1000.0},
            "units": {},
        },
    }

    res = adapter.evaluate_json(clean_json, evaluation_time=current_time, registry=reg)
    assert res["verdict"] == "PASS"


# --- TEST 19: Устранение тавтологии: Разрешённый loss_domain (Pass) ---
def test_fx_adapter_authorized_loss_domain_pass(host_registry, current_time):
    """
    Test 19: Task requests requested_loss_domain='funds_transfer'.
    Policy authorizes authorized_loss_domain='funds_transfer'.
    Adapter validates and passes to engine. Engine evaluates to PASS.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-019-loss-pass",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
        requested_loss_domain="funds_transfer",
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        authorized_loss_domain="funds_transfer",
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)
    assert res.status == "ENGINE_EVALUATED"
    assert res.engine_verdict == "PASS"


# --- TEST 20: Устранение тавтологии: Запрещённый loss_domain в политике хоста ---
def test_fx_adapter_unauthorized_loss_domain_rejected_by_policy(host_registry, current_time):
    """
    Test 20: Task requests 'funds_transfer', but policy only authorizes
    'restricted_securities_settlement'.
    Adapter MUST reject before calling engine with UNAUTHORIZED_LOSS_DOMAIN.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-020-loss-denied",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
        requested_loss_domain="funds_transfer",
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        authorized_loss_domain="restricted_securities_settlement",  # Does not authorize funds_transfer
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)
    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "UNAUTHORIZED_LOSS_DOMAIN"
    assert "Unauthorized loss domain" in res.rejection_reason
    assert res.engine_report is None


# --- TEST 21: Устранение тавтологии: Попытка агента подменить loss_domain ---
def test_fx_adapter_agent_loss_domain_spoof_attempt_rejected(host_registry, current_time):
    """
    Test 21: Agent attempts to request unauthorized loss domain 'administrative_root_drain',
    while policy only authorizes 'funds_transfer'.
    Adapter MUST reject before calling engine with UNAUTHORIZED_LOSS_DOMAIN.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    task = TaskRequest(
        request_id="req-fx-021-spoof-loss",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
        requested_loss_domain="administrative_root_drain",  # Malicious/unauthorized domain
    )
    policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        authorized_loss_domain="funds_transfer",
        host_evaluation_time=current_time,
    )

    res = adapter.process_payment(task, policy, host_registry)
    assert res.status == "ADAPTER_REJECTED"
    assert res.error_code == "UNAUTHORIZED_LOSS_DOMAIN"
    assert "Unauthorized loss domain" in res.rejection_reason
    assert res.engine_report is None


# --- TEST 22: Невозможность обойти запрет через аргументы вызова (trusted_host_context отсутствует) ---
def test_direct_json_no_trusted_host_context_parameter():
    """
    Test 22: Verifies that evaluate_json does NOT have any 'trusted_host_context' parameter.
    Passing trusted_host_context=True must raise a TypeError (unexpected keyword argument),
    guaranteeing no caller can toggle trust via a boolean flag.
    """
    from sol_triad import SolTriadJsonAdapter
    adapter = SolTriadJsonAdapter()
    dummy_json = {
        "request_id": "test-call",
        "protocol_version": "0.4.0",
        "source": {"evidence_id": "e", "authority_domain": ["d"], "granted_scope": ["o"], "granted_loss_domains": ["l"], "epistemic_type": "FACT", "timestamp_sec": 1740000000.0},
        "constraint": {"domain_scope": ["d"], "target_objects": ["o"], "protected_set": [], "units": {}},
        "dissipate": {"loss_domain": ["l"], "target_states": ["s"], "side_effects": [], "resource_cost": {}, "state_delta": {"o": 0.0}, "units": {}},
        "initial_state": {"current_values": {"o": 0.0}, "units": {}},
    }

    try:
        adapter.evaluate_json(dummy_json, trusted_host_context=True)  # type: ignore
        assert False, "Should have raised TypeError because trusted_host_context was completely removed!"
    except TypeError as e:
        assert "unexpected keyword argument 'trusted_host_context'" in str(e)


# --- TEST 23: Регрессия Finance FX: Доказательства только из host_registry, время только из HostPolicy ---
def test_finance_fx_regression_host_time_and_registry_enforced(host_registry, current_time):
    """
    Test 23: Confirms that Finance FX route strictly derives evaluation time from
    HostPolicy and evidence records strictly from host_registry.
    """
    quote_id = register_direct_quote(host_registry, current_time)
    adapter = FinanceFxAdapter()

    # Part A: Stale quote check using HostPolicy time
    task = TaskRequest(
        request_id="req-fx-023-stale-check",
        payer_account="acc_uah_main",
        operation_amount=100.0,
        operation_currency="EUR",
        ledger_currency="UAH",
        claimed_state_delta=-4000.0,
        quote_id=quote_id,
    )
    stale_policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        host_evaluation_time=current_time + 400.0,  # 410s after quote timestamp (max 300s)
    )
    res_stale = adapter.process_payment(task, stale_policy, host_registry)
    assert res_stale.engine_verdict == "REVIEW"
    assert any(d["code"] == "TEMPORAL_STALE" for d in res_stale.engine_report["diagnostics"])

    # Part B: Missing quote in registry is strictly rejected
    empty_registry = InMemoryEvidenceRegistry()
    fresh_policy = HostPolicy(
        account_id="acc_uah_main",
        initial_balance=10000.0,
        host_evaluation_time=current_time,
    )
    res_missing = adapter.process_payment(task, fresh_policy, empty_registry)
    assert res_missing.status == "ADAPTER_REJECTED"
    assert res_missing.error_code == "EVIDENCE_NOT_FOUND"


if __name__ == "__main__":
    t_now = get_current_time()

    test_fx_adapter_correct_conversion_pass(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_correct_conversion_pass")

    test_fx_adapter_mismatch_rejected_without_engine(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_mismatch_rejected_without_engine")

    test_fx_adapter_indirect_quotation(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_indirect_quotation")

    test_fx_adapter_currency_pair_mismatch(t_now, get_host_registry())
    print("PASS: test_fx_adapter_currency_pair_mismatch")

    test_fx_adapter_rounding_precision()
    print("PASS: test_fx_adapter_rounding_precision")

    test_fx_adapter_missing_quote(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_missing_quote")

    test_fx_adapter_stale_quote_review(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_stale_quote_review")

    test_fx_adapter_insufficient_funds_fail(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_insufficient_funds_fail")

    test_no_self_minting_unregistered_quote_rejected(t_now)
    print("PASS: test_no_self_minting_unregistered_quote_rejected")

    test_account_mismatch_rejected(get_host_registry(), t_now)
    print("PASS: test_account_mismatch_rejected")

    test_policy_balance_and_limit_cannot_be_overridden_by_request(get_host_registry(), t_now)
    print("PASS: test_policy_balance_and_limit_cannot_be_overridden_by_request")

    test_host_evaluation_time_strictly_enforced(get_host_registry(), t_now)
    print("PASS: test_host_evaluation_time_strictly_enforced")

    test_legacy_request_requires_explicit_host_policy(get_host_registry(), t_now)
    print("PASS: test_legacy_request_requires_explicit_host_policy")

    test_quote_domain_mismatch_rejected(get_host_registry(), t_now)
    print("PASS: test_quote_domain_mismatch_rejected")

    test_legacy_request_triggers_deprecation_warning(t_now)
    print("PASS: test_legacy_request_triggers_deprecation_warning")

    test_direct_json_evaluation_time_injection_rejected()
    print("PASS: test_direct_json_evaluation_time_injection_rejected")

    test_direct_json_evidence_records_injection_rejected()
    print("PASS: test_direct_json_evidence_records_injection_rejected")

    test_direct_json_safe_payload_with_host_parameters(t_now)
    print("PASS: test_direct_json_safe_payload_with_host_parameters")

    test_fx_adapter_authorized_loss_domain_pass(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_authorized_loss_domain_pass")

    test_fx_adapter_unauthorized_loss_domain_rejected_by_policy(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_unauthorized_loss_domain_rejected_by_policy")

    test_fx_adapter_agent_loss_domain_spoof_attempt_rejected(get_host_registry(), t_now)
    print("PASS: test_fx_adapter_agent_loss_domain_spoof_attempt_rejected")

    test_direct_json_no_trusted_host_context_parameter()
    print("PASS: test_direct_json_no_trusted_host_context_parameter")

    test_finance_fx_regression_host_time_and_registry_enforced(get_host_registry(), t_now)
    print("PASS: test_finance_fx_regression_host_time_and_registry_enforced")

    print("\nALL 23 TESTS PASSED SUCCESSFULLY!")
