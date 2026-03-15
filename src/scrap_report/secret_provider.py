"""Secret provider abstraction with secure OS-backed implementations."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field


class SecretProviderError(RuntimeError):
    """Generic provider failure."""


class SecretNotFoundError(SecretProviderError):
    """Secret does not exist in provider backend."""


class SecretBackendUnavailableError(SecretProviderError):
    """Provider backend is unavailable on this host."""


class SecretProvider:
    """Contract for secure secret access."""

    def set_secret(self, service: str, username: str, secret: str) -> None:
        raise NotImplementedError

    def get_secret(self, service: str, username: str) -> str:
        raise NotImplementedError

    def test_backend(self) -> bool:
        raise NotImplementedError


@dataclass(slots=True)
class MemorySecretProvider(SecretProvider):
    """In-memory provider for tests only."""

    _store: dict[tuple[str, str], str] = field(default_factory=dict)

    def set_secret(self, service: str, username: str, secret: str) -> None:
        self._store[(service, username)] = secret

    def get_secret(self, service: str, username: str) -> str:
        key = (service, username)
        if key not in self._store:
            raise SecretNotFoundError("secret nao encontrado")
        return self._store[key]

    def test_backend(self) -> bool:
        return True


class MacOSKeychainSecretProvider(SecretProvider):
    """macOS Keychain provider using `security` command."""

    def _run(self, args: list[str], input_secret: str | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(  # noqa: S603
                ["security", *args],
                capture_output=True,
                text=True,
                check=False,
                input=input_secret,
            )
        except FileNotFoundError as exc:
            raise SecretBackendUnavailableError("backend keychain indisponivel") from exc

    def set_secret(self, service: str, username: str, secret: str) -> None:
        if not secret.strip():
            raise SecretProviderError("secret vazio nao permitido")
        proc = self._run(
            [
                "add-generic-password",
                "-a",
                username,
                "-s",
                service,
                "-w",
                secret,
                "-U",
            ]
        )
        if proc.returncode != 0:
            raise SecretProviderError("falha ao gravar secret no keychain")

    def get_secret(self, service: str, username: str) -> str:
        proc = self._run(
            ["find-generic-password", "-a", username, "-s", service, "-w"]
        )
        if proc.returncode != 0:
            raise SecretNotFoundError("secret nao encontrado no keychain")
        secret = proc.stdout.strip()
        if not secret:
            raise SecretNotFoundError("secret vazio no keychain")
        return secret

    def test_backend(self) -> bool:
        proc = self._run(["show-keychain"])
        return proc.returncode == 0


class WindowsCredentialManagerSecretProvider(SecretProvider):
    """Windows credential backend using PowerShell CredentialManager module."""

    def _resolve_powershell_executable(self) -> str:
        for executable in ("pwsh", "powershell"):
            if shutil.which(executable):
                return executable
        raise SecretBackendUnavailableError("backend windows credential indisponivel")

    def _run_ps(self, script: str) -> subprocess.CompletedProcess[str]:
        executable = self._resolve_powershell_executable()
        try:
            return subprocess.run(  # noqa: S603
                [
                    executable,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise SecretBackendUnavailableError("backend windows credential indisponivel") from exc

    def set_secret(self, service: str, username: str, secret: str) -> None:
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            f"$pass = ConvertTo-SecureString '{secret}' -AsPlainText -Force; "
            f"$cred = New-Object System.Management.Automation.PSCredential('{username}', $pass); "
            f"New-StoredCredential -Target '{service}' -Credential $cred -Type Generic -Persist LocalMachine | Out-Null"
        )
        proc = self._run_ps(script)
        if proc.returncode != 0:
            if proc.returncode == 11:
                raise SecretBackendUnavailableError("modulo CredentialManager ausente")
            raise SecretProviderError("falha ao gravar credencial no windows vault")

    def get_secret(self, service: str, username: str) -> str:
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            f"$c = Get-StoredCredential -Target '{service}'; "
            "if ($null -eq $c) { exit 12 }; "
            "if ($c.UserName -ne "
            f"'{username}'"
            ") { exit 13 }; "
            "$c.Password"
        )
        proc = self._run_ps(script)
        if proc.returncode == 11:
            raise SecretBackendUnavailableError("modulo CredentialManager ausente")
        if proc.returncode in {12, 13}:
            raise SecretNotFoundError("secret nao encontrado no windows vault")
        if proc.returncode != 0:
            raise SecretProviderError("falha ao ler credencial no windows vault")
        secret = proc.stdout.strip()
        if not secret:
            raise SecretNotFoundError("secret vazio no windows vault")
        return secret

    def test_backend(self) -> bool:
        proc = self._run_ps(
            "if (Get-Module -ListAvailable -Name CredentialManager) { exit 0 } else { exit 11 }"
        )
        return proc.returncode == 0


class LinuxSecretServiceProvider(SecretProvider):
    """Linux Secret Service backend using secret-tool."""

    def _run(self, args: list[str], input_secret: str | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(  # noqa: S603
                ["secret-tool", *args],
                capture_output=True,
                text=True,
                check=False,
                input=input_secret,
            )
        except FileNotFoundError as exc:
            raise SecretBackendUnavailableError("backend secret-service indisponivel") from exc

    def set_secret(self, service: str, username: str, secret: str) -> None:
        proc = self._run(
            ["store", "--label", service, "service", service, "username", username],
            input_secret=secret,
        )
        if proc.returncode != 0:
            raise SecretProviderError("falha ao gravar secret no secret-service")

    def get_secret(self, service: str, username: str) -> str:
        proc = self._run(["lookup", "service", service, "username", username])
        if proc.returncode != 0:
            raise SecretNotFoundError("secret nao encontrado no secret-service")
        secret = proc.stdout.strip()
        if not secret:
            raise SecretNotFoundError("secret vazio no secret-service")
        return secret

    def test_backend(self) -> bool:
        proc = self._run(["search", "service", "scrap_report.healthcheck"])
        return proc.returncode in {0, 1}


def build_secret_provider() -> SecretProvider:
    system = platform.system().lower()
    if system == "darwin":
        return MacOSKeychainSecretProvider()
    if system == "windows":
        return WindowsCredentialManagerSecretProvider()
    if system == "linux":
        return LinuxSecretServiceProvider()
    raise SecretBackendUnavailableError("nenhum backend seguro suportado para este sistema")
