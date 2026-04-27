import subprocess

import pytest

from scrap_report.secret_provider import (
    LinuxSecretServiceProvider,
    MacOSKeychainSecretProvider,
    MemorySecretProvider,
    SecretBackendUnavailableError,
    SecretNotFoundError,
    SecretProviderError,
    WindowsCredentialManagerSecretProvider,
    build_secret_provider,
)


def test_memory_provider_roundtrip():
    provider = MemorySecretProvider()
    provider.set_secret("svc", "user", "pass")
    assert provider.get_secret("svc", "user") == "pass"


def test_memory_provider_not_found():
    provider = MemorySecretProvider()
    with pytest.raises(SecretNotFoundError):
        provider.get_secret("svc", "missing")


def test_macos_provider_get_secret(monkeypatch: pytest.MonkeyPatch):
    provider = MacOSKeychainSecretProvider()

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="abc\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert provider.get_secret("svc", "user") == "abc"


def test_macos_provider_backend_unavailable(monkeypatch: pytest.MonkeyPatch):
    provider = MacOSKeychainSecretProvider()

    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError("security")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SecretBackendUnavailableError):
        provider.test_backend()


def test_build_secret_provider_non_darwin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    assert isinstance(build_secret_provider(), LinuxSecretServiceProvider)


def test_build_secret_provider_windows(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    assert isinstance(build_secret_provider(), WindowsCredentialManagerSecretProvider)


def test_windows_provider_presence_only(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="secret123\n", stderr=""
        )

    monkeypatch.setattr(provider, "_resolve_powershell_executables", lambda: ["powershell"])
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert provider.get_secret("svc", "user1") == "secret123"


def test_windows_provider_fallback_to_pwsh(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()
    called: dict[str, str] = {}

    def fake_which(name: str) -> str | None:
        if name == "powershell":
            return None
        if name == "pwsh":
            return "C:\\Program Files\\PowerShell\\7\\pwsh.exe"
        return None

    def fake_run(args, **_kwargs):
        called["exe"] = args[0]
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("os.path.exists", lambda _path: False)
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert provider.test_backend() is True
    assert called["exe"].lower().endswith("pwsh.exe")


def test_windows_provider_fallback_pwsh_fail_then_powershell_ok(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()
    call_order: list[str] = []

    def fake_which(name: str) -> str | None:
        if name == "pwsh":
            return "C:\\Program Files\\PowerShell\\7\\pwsh.exe"
        if name == "powershell":
            return None
        return None

    def fake_run(args, **_kwargs):
        exe = args[0]
        call_order.append(exe)
        if exe.lower().endswith("pwsh.exe"):
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="bad pwsh")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="secret123\n", stderr="")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr(
        "os.path.exists",
        lambda path: str(path).replace("/", "\\").lower().endswith(
            "\\windowspowershell\\v1.0\\powershell.exe"
        ),
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert provider.get_secret("svc", "user1") == "secret123"
    assert call_order[0].lower().endswith("pwsh.exe")
    assert call_order[1].lower().endswith("powershell.exe")


def test_windows_provider_set_secret_module_missing(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()

    called = {"dpapi": False}

    def fake_set_cm(*_args, **_kwargs):
        raise SecretBackendUnavailableError("modulo CredentialManager ausente")

    def fake_set_dpapi(*_args, **_kwargs):
        called["dpapi"] = True

    monkeypatch.setattr(provider, "_set_secret_via_credential_manager", fake_set_cm)
    monkeypatch.setattr(provider, "_set_secret_via_dpapi_store", fake_set_dpapi)
    provider.set_secret("svc", "user1", "secret123")
    assert called["dpapi"] is True


def test_windows_provider_set_secret_escapes_single_quotes(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()
    captured: dict[str, str] = {}

    def fake_run(script: str):
        captured["script"] = script
        return [("pwsh", subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""))]

    monkeypatch.setattr(provider, "_run_ps_with_fallback", fake_run)
    provider._set_secret_via_credential_manager("svc'o", "user'o", "pa'ss")
    assert "-Target 'svc''o'" in captured["script"]
    assert "-UserName 'user''o'" in captured["script"]
    assert "-Password 'pa''ss'" in captured["script"]


def test_windows_provider_get_secret_escapes_single_quotes(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()
    captured: dict[str, str] = {}

    def fake_run(script: str):
        captured["script"] = script
        return [
            (
                "pwsh",
                subprocess.CompletedProcess(args=[], returncode=0, stdout="secret123\n", stderr=""),
            )
        ]

    monkeypatch.setattr(provider, "_run_ps_with_fallback", fake_run)
    assert provider._get_secret_via_credential_manager("svc'o", "user'o") == "secret123"
    assert "-Target 'svc''o'" in captured["script"]
    assert "$c.UserName -ne 'user''o'" in captured["script"]


def test_windows_provider_set_secret_rejects_blank():
    provider = WindowsCredentialManagerSecretProvider()
    with pytest.raises(SecretProviderError, match="secret vazio nao permitido"):
        provider.set_secret("svc", "user1", "   ")


def test_windows_provider_get_secret_fallback_to_dpapi(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()

    def fake_get_cm(*_args, **_kwargs):
        raise SecretBackendUnavailableError("modulo CredentialManager ausente")

    monkeypatch.setattr(provider, "_get_secret_via_credential_manager", fake_get_cm)
    monkeypatch.setattr(provider, "_get_secret_via_dpapi_store", lambda *_args, **_kwargs: "secret123")
    assert provider.get_secret("svc", "user1") == "secret123"


def test_windows_provider_without_shell(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()
    monkeypatch.setattr(provider, "_test_credential_manager_backend", lambda: False)
    monkeypatch.setattr(provider, "_test_dpapi_backend", lambda: True)
    assert provider.test_backend() is True


def test_linux_provider_set_secret_rejects_blank(monkeypatch: pytest.MonkeyPatch):
    provider = LinuxSecretServiceProvider()

    def fail_run(*_args, **_kwargs):
        raise AssertionError("nao deve executar secret-tool para secret vazio")

    monkeypatch.setattr(subprocess, "run", fail_run)
    with pytest.raises(SecretProviderError, match="secret vazio nao permitido"):
        provider.set_secret("svc", "user1", "   ")
