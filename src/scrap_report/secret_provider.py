"""Secret provider abstraction with secure OS-backed implementations."""

from __future__ import annotations

import platform
import shutil
import subprocess
import os
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

    _SHELL_ORDER = ("pwsh", "powershell")

    def _resolve_powershell_executables(self) -> list[str]:
        executables: list[str] = []
        pwsh = shutil.which("pwsh")
        if pwsh:
            executables.append(pwsh)

        powershell = shutil.which("powershell")
        if powershell:
            executables.append(powershell)
        else:
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            fallback = os.path.join(
                system_root,
                "System32",
                "WindowsPowerShell",
                "v1.0",
                "powershell.exe",
            )
            if os.path.exists(fallback):
                executables.append(fallback)

        # remove duplicates preserving order
        seen: set[str] = set()
        unique_executables: list[str] = []
        for executable in executables:
            key = executable.lower()
            if key in seen:
                continue
            seen.add(key)
            unique_executables.append(executable)
        if not unique_executables:
            raise SecretBackendUnavailableError("backend windows credential indisponivel")
        return unique_executables

    def _run_ps_in_shell(self, executable: str, script: str) -> subprocess.CompletedProcess[str]:
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

    def _run_ps_with_fallback(self, script: str) -> list[tuple[str, subprocess.CompletedProcess[str]]]:
        results: list[tuple[str, subprocess.CompletedProcess[str]]] = []
        for executable in self._resolve_powershell_executables():
            proc = self._run_ps_in_shell(executable, script)
            results.append((executable, proc))
            if proc.returncode == 0:
                break
        return results

    @staticmethod
    def _all_failed_with_code(
        results: list[tuple[str, subprocess.CompletedProcess[str]]], code: int
    ) -> bool:
        return bool(results) and all(proc.returncode == code for _, proc in results)

    def set_secret(self, service: str, username: str, secret: str) -> None:
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            "if (-not (Get-Command New-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            f"try {{ New-StoredCredential -Target '{service}' -UserName '{username}' -Password '{secret}' -Type Generic -Persist Enterprise | Out-Null; exit 0 }} "
            "catch { "
            f"try {{ New-StoredCredential -Target '{service}' -UserName '{username}' -Password '{secret}' -Type Generic -Persist LocalMachine | Out-Null; exit 0 }} "
            "catch { exit 16 } "
            "}"
        )
        results = self._run_ps_with_fallback(script)
        if any(proc.returncode == 0 for _, proc in results):
            return
        if self._all_failed_with_code(results, 11):
            raise SecretBackendUnavailableError("modulo CredentialManager ausente")
        raise SecretProviderError("falha ao gravar credencial no windows vault")

    def get_secret(self, service: str, username: str) -> str:
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            "if (-not (Get-Command Get-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            f"$c = Get-StoredCredential -Target '{service}'; "
            "if ($null -eq $c) { exit 12 }; "
            "if ($c.UserName -ne "
            f"'{username}'"
            ") { exit 13 }; "
            "if ($c.Password -is [System.Security.SecureString]) { "
            "$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($c.Password); "
            "try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } "
            "finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) } "
            "} else { $c.Password }"
        )
        results = self._run_ps_with_fallback(script)
        for _, proc in results:
            if proc.returncode == 0:
                secret = proc.stdout.strip()
                if not secret:
                    raise SecretNotFoundError("secret vazio no windows vault")
                return secret
        if self._all_failed_with_code(results, 11):
            raise SecretBackendUnavailableError("modulo CredentialManager ausente")
        if any(proc.returncode in {12, 13} for _, proc in results):
            raise SecretNotFoundError("secret nao encontrado no windows vault")
        raise SecretProviderError("falha ao ler credencial no windows vault")

    def test_backend(self) -> bool:
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            "if (-not (Get-Command New-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            "if (-not (Get-Command Get-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            "if (-not (Get-Command Remove-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            "$target = 'scrap_report.healthcheck.' + [guid]::NewGuid().ToString(); "
            "try { "
            "New-StoredCredential -Target $target -UserName 'healthcheck' -Password 'healthcheck' -Type Generic -Persist Enterprise | Out-Null; "
            "$c = Get-StoredCredential -Target $target; "
            "if ($null -eq $c) { exit 15 }; "
            "Remove-StoredCredential -Target $target -ErrorAction SilentlyContinue | Out-Null; "
            "exit 0 "
            "} catch { exit 16 }"
        )
        results = self._run_ps_with_fallback(script)
        return any(proc.returncode == 0 for _, proc in results)


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
