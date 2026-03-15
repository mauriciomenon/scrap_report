# SECURITY_MODEL

## Scope
- Project: `/Users/menon/git/scrap_report`
- Deployment shape: this project runs as a subdir inside a parent repository.
- Goal: protect credentials and output artifacts used by downstream SQL ingestion.

## Security Objectives
1. Never persist SAM credentials in plaintext.
2. Never expose secrets in logs, console output, JSON payloads, or test artifacts.
3. Fail closed when secure secret backend is unavailable.
4. Keep operational behavior auditable with minimal leak surface.

## Protected Assets
1. Username/password for SAM login.
2. Downloaded XLSX files before staging handoff.
3. Generated JSON contract artifacts.
4. Execution metadata and error traces.

## Trust Boundaries
1. CLI input boundary (`--password`, environment variables).
2. Runtime process memory boundary.
3. OS secret store boundary (Keychain/Credential Manager/Secret Service).
4. Filesystem boundary (`downloads`, `staging`, logs, docs).
5. External web target boundary (SAM website).

## Baseline Controls (Current)
1. No hardcoded credentials in current runtime modules.
2. Output contract path is explicit and versioned.
3. Retry and timeout controls exist for browser automation.

## Required Controls (Rodada 1 Baseline)
1. Secret source policy with hard-fail when secure backend is missing.
2. Global redaction policy for sensitive tokens in logs and exceptions.
3. JSON output policy forbidding sensitive fields.
4. Subdir-safe path policy to avoid accidental writes outside project root.
5. Runtime credential notice in `stderr` for auth-required commands, with setup guidance and no secret leak.

## Risk Matrix
- High:
  - Credential leakage in logs/output.
  - Plaintext credential persistence.
- Medium:
  - Selector breakage causing unsafe manual workarounds.
  - Incomplete error redaction in exception paths.
- Low:
  - Metadata-only exposure with no credential content.

## Rollback Criteria
1. If a security control breaks core CLI behavior, rollback only the failing slice commit.
2. Keep docs and runtime changes in separate slices when possible.
3. Preserve contract schema compatibility during rollback.
