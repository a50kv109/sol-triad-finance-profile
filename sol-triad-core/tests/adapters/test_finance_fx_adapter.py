"""
Тесты продуктового адаптера Finance FX (FinanceFxAdapter).
"""

from sol_triad_core import (
    InMemoryEvidenceRegistry,
    EvidenceRecord,
    EpistemicStatus,
    CoherenceVerdict,
    DiagnosticCode,
)
from adapters.finance_fx_adapter import (
    TaskRequest,
    HostPolicy,
    FinanceFxAdapter,
)


def _setup_finance_fixture():
    now = 1740000000.0
    reg = InMemoryEvidenceRegistry()
    reg.register(EvidenceRecord(
        evidence_id="quote-eur-usd-101",
        domain="finance_fx",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=now - 30.0,
        payload_hash="sha256-ecb-quote-ok"
    ))

    policy = HostPolicy(
        authorized_account_id="ACC_EUR_001",
        authorized_loss_domain="funds_transfer",
        max_transaction_amount=10000.0,
        current_balance=50000.0,
        evaluation_time=now,
        currency="USD"
    )

    req = TaskRequest(
        request_id="pay-req-001",
        source_account_id="ACC_EUR_001",
        destination_account_id="ACC_USD_888",
        amount_source=100.0,
        currency_source="EUR",
        amount_target=108.50,
        currency_target="USD",
        quoted_rate=1.085,
        evidence_quote_id="quote-eur-usd-101",
        requested_loss_domain="funds_transfer"
    )

    return reg, policy, req, now


def test_fx_adapter_correct_conversion_pass():
    reg, policy, req, now = _setup_finance_fixture()
    adapter = FinanceFxAdapter()

    res = adapter.process_payment(req, policy, reg)

    assert res.verdict == CoherenceVerdict.PASS.value
    assert res.status == "SUCCESS"
    assert res.source_delta == -100.0
    assert res.target_delta == 108.50
    assert res.execution_permitted is False, "Adapter MUST NOT permit payment execution!"


def test_fx_adapter_unauthorized_loss_domain_rejected():
    reg, policy, req, now = _setup_finance_fixture()
    # Agent attempts spoofing loss domain to 'arbitrary_loss'
    req.requested_loss_domain = "arbitrary_loss"
    adapter = FinanceFxAdapter()

    res = adapter.process_payment(req, policy, reg)

    assert res.status == "ADAPTER_REJECTED"
    assert res.verdict == CoherenceVerdict.FAIL.value
    assert any(d["code"] == DiagnosticCode.UNAUTHORIZED_LOSS_DOMAIN.value for d in res.diagnostics)
    assert res.execution_permitted is False


def test_fx_adapter_unregistered_quote_rejected():
    reg, policy, req, now = _setup_finance_fixture()
    req.evidence_quote_id = "quote-unregistered-ghost"
    adapter = FinanceFxAdapter()

    res = adapter.process_payment(req, policy, reg)

    assert res.status == "REJECTED"
    assert res.verdict == CoherenceVerdict.FAIL.value
    assert any(d["code"] == DiagnosticCode.EVIDENCE_NOT_FOUND.value for d in res.diagnostics)


def test_fx_adapter_insufficient_funds_overdraft_fail():
    reg, policy, req, now = _setup_finance_fixture()
    # Balance is only 50.0, payment is 100.0 -> overdraft breach
    policy.current_balance = 50.0
    adapter = FinanceFxAdapter()

    res = adapter.process_payment(req, policy, reg)

    assert res.verdict == CoherenceVerdict.FAIL.value
    assert any(d["code"] == DiagnosticCode.STATE_MIN_BOUND_BREACH.value for d in res.diagnostics)
    assert res.execution_permitted is False


def test_fx_adapter_stale_quote_review():
    reg, policy, req, now = _setup_finance_fixture()
    # Quote is 500s old (max_age is 300s) -> REVIEW (TEMPORAL_STALE)
    stale_time = now - 500.0
    reg.register(EvidenceRecord(
        evidence_id=req.evidence_quote_id,
        domain="finance_fx",
        epistemic_status=EpistemicStatus.FACT,
        timestamp_sec=stale_time,
        payload_hash="sha256-ecb-quote-ok"
    ))
    adapter = FinanceFxAdapter()

    res = adapter.process_payment(req, policy, reg)

    assert res.verdict == CoherenceVerdict.REVIEW.value
    assert res.status == "REVIEW"
    assert any(d["code"] == DiagnosticCode.TEMPORAL_STALE.value for d in res.diagnostics)
    assert res.execution_permitted is False


if __name__ == "__main__":
    test_fx_adapter_correct_conversion_pass()
    test_fx_adapter_unauthorized_loss_domain_rejected()
    test_fx_adapter_unregistered_quote_rejected()
    test_fx_adapter_insufficient_funds_overdraft_fail()
    test_fx_adapter_stale_quote_review()
    print("test_finance_fx_adapter.py: ALL TESTS PASSED")
