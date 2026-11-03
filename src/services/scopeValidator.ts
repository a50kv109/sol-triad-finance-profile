/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * Scope & Authority Validator.
 *
 * Implements exact parity with Python reference kernel (sol_triad/validators.py:ScopeValidator v0.4.1):
 *   - Explicit distinction between structural defect (null/undefined -> SCOPE_DEFECT_NONE)
 *     and legitimate zero-privilege grant (empty array [] -> valid grant of zero privileges).
 *   - Zero-privilege grant forbids any action (fails with SCOPE_EXCEEDED_*).
 *   - Strict subset containment:
 *       P_SC: domain_scope ⊆ authority_domain, target_objects ⊆ granted_scope
 *       P_SD: loss_domain ⊆ granted_loss_domains
 */

import {
  SourcePrimitive,
  ConstraintPrimitive,
  DissipatePrimitive,
  CoherenceVerdict,
  CoherenceDiagnostic,
} from "../types/triad";

export class ScopeValidator {
  public validate(
    s: SourcePrimitive,
    c: ConstraintPrimitive,
    d: DissipatePrimitive
  ): [boolean, CoherenceVerdict, CoherenceDiagnostic[]] {
    const diagnostics: CoherenceDiagnostic[] = [];

    // 1. Structural Defect vs Zero-Privilege distinction
    // null / undefined = Missing mandatory security field (structural defect)
    // [] (empty array) = Explicitly granted zero privileges
    let hasDefect = false;

    if (s.authority_domain === null || s.authority_domain === undefined) {
      diagnostics.push({
        code: "SCOPE_DEFECT_NONE",
        severity: "ERROR",
        message: "Source authority_domain is null/undefined (structural defect).",
        primitive: "SOURCE",
        field_name: "authority_domain",
      });
      hasDefect = true;
    }

    if (s.granted_scope === null || s.granted_scope === undefined) {
      diagnostics.push({
        code: "SCOPE_DEFECT_NONE",
        severity: "ERROR",
        message: "Source granted_scope is null/undefined (structural defect).",
        primitive: "SOURCE",
        field_name: "granted_scope",
      });
      hasDefect = true;
    }

    if (s.granted_loss_domains === null || s.granted_loss_domains === undefined) {
      diagnostics.push({
        code: "SCOPE_DEFECT_NONE",
        severity: "ERROR",
        message: "Source granted_loss_domains is null/undefined (structural defect).",
        primitive: "SOURCE",
        field_name: "granted_loss_domains",
      });
      hasDefect = true;
    }

    if (hasDefect) {
      return [false, "FAIL", diagnostics];
    }

    // At this point, sets are guaranteed not null/undefined (may be empty [])
    let failed = false;
    const authSet = new Set(s.authority_domain || []);
    const scopeSet = new Set(s.granted_scope || []);
    const lossSet = new Set(s.granted_loss_domains || []);

    // 2. Domain Scope Containment (P_SC)
    const domainScope = c.domain_scope || [];
    const unauthDomains = domainScope.filter((dom) => !authSet.has(dom));
    if (unauthDomains.length > 0) {
      diagnostics.push({
        code: "SCOPE_EXCEEDED_DOMAIN",
        severity: "ERROR",
        message: `Constraint domain scope [${domainScope.join(", ")}] exceeds granted authority: unauthorized [${unauthDomains.join(", ")}].`,
        primitive: "CONSTRAINT",
        field_name: "domain_scope",
      });
      failed = true;
    }

    // 3. Target Objects Containment (P_SC)
    const targetObjects = c.target_objects || [];
    const unauthObjects = targetObjects.filter((obj) => !scopeSet.has(obj));
    if (unauthObjects.length > 0) {
      diagnostics.push({
        code: "SCOPE_EXCEEDED_OBJECTS",
        severity: "ERROR",
        message: `Constraint target objects [${targetObjects.join(", ")}] exceed granted scope: unauthorized [${unauthObjects.join(", ")}].`,
        primitive: "CONSTRAINT",
        field_name: "target_objects",
      });
      failed = true;
    }

    // 4. Loss Domain Containment (P_SD)
    const lossDomain = d.loss_domain || [];
    const unauthLoss = lossDomain.filter((ld) => !lossSet.has(ld));
    if (unauthLoss.length > 0) {
      diagnostics.push({
        code: "SCOPE_EXCEEDED_LOSS",
        severity: "ERROR",
        message: `Dissipate loss domain [${lossDomain.join(", ")}] exceeds granted loss domains: unauthorized [${unauthLoss.join(", ")}].`,
        primitive: "DISSIPATE",
        field_name: "loss_domain",
      });
      failed = true;
    }

    if (failed) {
      return [false, "FAIL", diagnostics];
    }

    diagnostics.push({
      code: "SCOPE_PASS",
      severity: "INFO",
      message: "Scope and authority checks satisfied.",
      primitive: "SOURCE",
    });
    return [true, "PASS", diagnostics];
  }
}
