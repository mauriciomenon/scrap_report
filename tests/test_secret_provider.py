import subprocess

import pytest

from scrap_report.secret_provider import (
    LinuxSecretServiceProvider,
    MacOSKeychainSecretProvider,
    MemorySecretProvider,
    SecretBackendUnavailableError,
    SecretNotFoundError,
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
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert provider.test_backend() is True
    assert called["exe"] == "pwsh"


def test_windows_provider_without_shell(monkeypatch: pytest.MonkeyPatch):
    provider = WindowsCredentialManagerSecretProvider()
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(SecretBackendUnavailableError):
        provider.test_backend()
