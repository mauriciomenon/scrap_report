# THREAT_MODEL

## Method
- Lightweight STRIDE-oriented analysis for the current extraction scope.

## System Context
1. Operator runs CLI locally.
2. CLI authenticates to SAM and downloads XLSX.
3. XLSX moves to local staging for downstream SQL generation.
4. Optional JSON contract is produced for integration.

## Threats and Mitigations

## T1: Credential Disclosure via CLI/Env
- Category: Information Disclosure
- Vector: `--password` arg history, env var leaks, shell logs.
- Impact: High
- Mitigation target:
  1. Replace plaintext secret flow with OS vault provider.
  2. Remove direct secret echo paths.
  3. Add fail-closed policy in config validation.

## T2: Secret Leakage in Logs/Exceptions
- Category: Information Disclosure
- Vector: exception message or debug logging with raw values.
- Impact: High
- Mitigation target:
  1. Apply structured redaction layer before any output.
  2. Add tests asserting no secret tokens in logs/json.
  3. Keep security notice in `stderr` only, preserving clean JSON in `stdout`.

## T3: Insecure Local Secret Persistence
- Category: Tampering/Information Disclosure
- Vector: fallback file storage or weak local encryption.
- Impact: High
- Mitigation target:
  1. Forbid plaintext file fallback.
  2. Permit only OS-backed secure storage providers.

## T4: Selector Drift Causing Unsafe Automation
- Category: Integrity/Availability
- Vector: DOM tag/id changes break target actions.
- Impact: Medium
- Mitigation target:
  1. Multi-layer selector strategy with confidence scoring.
  2. Strict/adaptive modes and safe fail diagnostics.

## T5: Path Confusion in Subdir Deployment
- Category: Tampering
- Vector: relative path misuse writes outside intended folder.
- Impact: Medium
- Mitigation target:
  1. Anchor paths at subproject root.
  2. Validate output destinations before write/move.

## T6: Over-collection in Output Contract
- Category: Information Disclosure
- Vector: accidental inclusion of auth/session fields.
- Impact: Medium
- Mitigation target:
  1. Contract allowlist schema.
  2. Fail-fast payload validation.

## Residual Risk (Current)
1. Secret provider not yet implemented in runtime.
2. Redaction policy not yet globalized.
3. Selector hardening phase not yet implemented.
