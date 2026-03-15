# DEPENDENCY_LICENSE_REVIEW

## Scope
- Baseline source: `pyproject.toml`
- Package manager: `uv`
- Review date: 2026-03-15

## Runtime Dependencies
1. `playwright>=1.45.0`
2. `pandas>=2.2.0`
3. `openpyxl>=3.1.0`

## License Baseline (to confirm in target release run)
1. `playwright`: Apache-2.0 (expected, confirm in final release machine)
2. `pandas`: BSD-3-Clause (expected, confirm in final release machine)
3. `openpyxl`: MIT (expected, confirm in final release machine)

## Security Notes
1. No new runtime dependency added during security hardening slices.
2. Secret backends currently rely on OS-native tooling:
  - macOS: `security`
  - Linux: `secret-tool`
  - Windows: PowerShell + `CredentialManager` module
3. For Windows release, verify trusted source/install method for `CredentialManager`.

## Final Verification Commands (release cycle)
1. `uv sync`
2. `uv run --project . python -m pip show playwright pandas openpyxl`
3. `uv run --project . python -m pip licenses --from=mixed` (if available)
4. Record exact versions and license output into release evidence.

## Result
- [ ] Approved for release
- [ ] Blocked pending verification
- Notes:
  - 

