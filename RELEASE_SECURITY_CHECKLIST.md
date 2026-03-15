# RELEASE_SECURITY_CHECKLIST

## Scope
- Project: `/Users/menon/git/scrap_report`
- Status: local hardening checklist before public repo creation
- Rule: do not create remote/repo until explicit user command

## Security Gate
1. Credentials
  - [ ] No plaintext credentials in code, docs, logs, or output JSON
  - [ ] OS-backed secret provider enabled for target platform
  - [ ] Transitional plaintext mode disabled for release run
  - [ ] Runtime security notice visible in `stderr` for auth-required commands
  - [ ] Fail-closed error includes safe `secret set` guidance, with no secret material
2. Secret Handling
  - [ ] `secret set/test/get` operational on target OS
  - [ ] `scan-secrets` returns zero findings on release workspace
3. Logging and Output
  - [ ] Redaction active in error paths
  - [ ] Output payload sanitization blocks sensitive keys
4. Selector Resilience
  - [ ] `selector_mode=adaptive` validated
  - [ ] `selector_mode=strict` validated in real target page
  - [ ] DOM health-check and failure snapshot verified
5. Pipeline Reliability
  - [ ] Typed errors observed with step names on forced failures
  - [ ] Telemetry fields present in pipeline outputs
6. Supply Chain
  - [ ] Dependency/license review documented
  - [ ] No unapproved new dependency added in this cycle

## Technical Gate
1. `uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py`
2. `uv run --project . ruff check .`
3. `uv run --project . --with pytest python -m pytest -q`
4. `uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json`
5. `uv run --project . python -m scrap_report.cli scan-secrets --paths src tests README.md`

## Cross-Platform Gate
1. macOS: smoke completed and evidence recorded.
2. Debian 13: smoke completed and evidence recorded.
3. Windows 11: smoke completed, CredentialManager backend validated, evidence recorded.

## Rollback Gate
1. If security regression appears, rollback only affected slice.
2. Keep contract schema and CLI compatibility stable.
3. Re-run full technical gate after rollback.

## Release Readiness Result
- [ ] READY
- [ ] NOT READY
- Blocking notes:
  - 
