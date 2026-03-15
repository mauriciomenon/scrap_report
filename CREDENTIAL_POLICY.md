# CREDENTIAL_POLICY

## Policy Goal
- Enforce robust credential handling for SAM access with fail-closed behavior.

## Hard Rules
1. No plaintext credentials in repository files, runtime logs, JSON outputs, or test snapshots.
2. No weak local encryption fallback.
3. No silent fallback to insecure source when secure backend is unavailable.
4. No secret value display in CLI output.

## Approved Secret Sources (Target State)
1. Windows 11: Credential Manager / DPAPI-backed provider.
2. macOS: Keychain provider.
3. Linux: Secret Service provider.

## Temporary Transitional State (Current)
1. CLI argument and environment variable inputs still exist.
2. This state is transitional only and must be replaced by vault providers.
3. Any run in transitional mode must be explicitly marked in control docs.

## Hard-Fail Definition
1. If secure provider is required and unavailable, execution must stop before login attempt.
2. Error message must be operator-safe and must not include credential material.
3. No automatic downgrade to plaintext storage is allowed.

## Runtime Notice Policy
1. For `scrape`, `pipeline` (without `--report-only`), and `ingest-latest`, CLI must emit a security notice in `stderr` before credential resolution.
2. Notice must state resolution order and fail-closed conditions.
3. Notice must include safe setup guidance pointing to `secret set` command and must never include secret values.
4. `stdout` must remain JSON-only for machine integration.

## Logging and Redaction Rules
1. Redact sensitive key names and values (`password`, `token`, `api_key`, `authorization`).
2. Redaction must apply to:
  - runtime logger messages
  - raised error messages surfaced to operator
  - JSON output writer path

## Test Requirements
1. Unit tests for provider fail-closed behavior.
2. Tests ensuring no secret appears in logs.
3. Tests ensuring JSON output excludes sensitive fields.
4. Cross-platform provider mocking tests for Windows/macOS/Linux.

## Rollback Policy
1. If credential hardening slice causes regression, rollback only that slice.
2. Keep schema and non-security pipeline behavior stable during rollback.
