"""Secret provider abstraction with secure OS-backed implementations."""

from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast


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
    _DPAPI_STORE_FILENAME = "windows_secrets_dpapi.json"
    _DPAPI_STORE_DIRNAME = "scrap_report"

    @staticmethod
    def _ctypes_windows_bindings() -> tuple[Any, Any]:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            raise SecretBackendUnavailableError("dpapi indisponivel neste host")
        return windll.crypt32, windll.kernel32

    @staticmethod
    def _raise_ctypes_windows_error() -> None:
        import ctypes

        winerror = getattr(ctypes, "WinError", None)
        if winerror is None:
            raise SecretProviderError("falha no DPAPI do Windows")
        raise cast(Any, winerror)()

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

    def _set_secret_via_credential_manager(self, service: str, username: str, secret: str) -> None:
        service_ps = service.replace("'", "''")
        username_ps = username.replace("'", "''")
        secret_ps = secret.replace("'", "''")
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            "if (-not (Get-Command New-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            f"try {{ New-StoredCredential -Target '{service_ps}' -UserName '{username_ps}' -Password '{secret_ps}' -Type Generic -Persist Enterprise | Out-Null; exit 0 }} "
            "catch { "
            f"try {{ New-StoredCredential -Target '{service_ps}' -UserName '{username_ps}' -Password '{secret_ps}' -Type Generic -Persist LocalMachine | Out-Null; exit 0 }} "
            "catch { exit 16 } "
            "}"
        )
        results = self._run_ps_with_fallback(script)
        if any(proc.returncode == 0 for _, proc in results):
            return
        if self._all_failed_with_code(results, 11):
            raise SecretBackendUnavailableError("modulo CredentialManager ausente")
        raise SecretProviderError("falha ao gravar credencial no windows vault")

    def _get_secret_via_credential_manager(self, service: str, username: str) -> str:
        service_ps = service.replace("'", "''")
        username_ps = username.replace("'", "''")
        script = (
            "if (-not (Get-Module -ListAvailable -Name CredentialManager)) { exit 11 }; "
            "Import-Module CredentialManager -ErrorAction Stop; "
            "if (-not (Get-Command Get-StoredCredential -ErrorAction SilentlyContinue)) { exit 14 }; "
            f"$c = Get-StoredCredential -Target '{service_ps}'; "
            "if ($null -eq $c) { exit 12 }; "
            "if ($c.UserName -ne "
            f"'{username_ps}'"
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

    def _test_credential_manager_backend(self) -> bool:
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

    def _dpapi_store_path(self) -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            root = Path(appdata)
        else:
            root = Path.home() / "AppData" / "Roaming"
        path = root / self._DPAPI_STORE_DIRNAME / self._DPAPI_STORE_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _dpapi_protect(data: bytes) -> bytes:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

        crypt32, kernel32 = WindowsCredentialManagerSecretProvider._ctypes_windows_bindings()
        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPCWSTR,
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        in_buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        in_blob = DATA_BLOB(len(data), in_buffer)
        out_blob = DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
        ):
            WindowsCredentialManagerSecretProvider._raise_ctypes_windows_error()
        try:
            raw = ctypes.cast(
                out_blob.pbData, ctypes.POINTER(ctypes.c_ubyte * out_blob.cbData)
            ).contents
            return bytes(raw)
        finally:
            kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))

    @staticmethod
    def _dpapi_unprotect(data: bytes) -> bytes:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

        crypt32, kernel32 = WindowsCredentialManagerSecretProvider._ctypes_windows_bindings()
        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        in_buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        in_blob = DATA_BLOB(len(data), in_buffer)
        out_blob = DATA_BLOB()
        description = wintypes.LPWSTR()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob), ctypes.byref(description), None, None, None, 0, ctypes.byref(out_blob)
        ):
            WindowsCredentialManagerSecretProvider._raise_ctypes_windows_error()
        try:
            raw = ctypes.cast(
                out_blob.pbData, ctypes.POINTER(ctypes.c_ubyte * out_blob.cbData)
            ).contents
            return bytes(raw)
        finally:
            if description:
                kernel32.LocalFree(ctypes.cast(description, ctypes.c_void_p))
            kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))

    def _load_dpapi_store(self) -> dict[str, str]:
        path = self._dpapi_store_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SecretProviderError("falha ao ler cofre local windows") from exc

    def _save_dpapi_store(self, payload: dict[str, str]) -> None:
        path = self._dpapi_store_path()
        try:
            path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        except OSError as exc:
            raise SecretProviderError("falha ao salvar cofre local windows") from exc

    @staticmethod
    def _dpapi_key(service: str, username: str) -> str:
        return f"{service}::{username}"

    def _set_secret_via_dpapi_store(self, service: str, username: str, secret: str) -> None:
        if not secret.strip():
            raise SecretProviderError("secret vazio nao permitido")
        encrypted = self._dpapi_protect(secret.encode("utf-8"))
        payload = self._load_dpapi_store()
        payload[self._dpapi_key(service, username)] = base64.b64encode(encrypted).decode("ascii")
        self._save_dpapi_store(payload)

    def _get_secret_via_dpapi_store(self, service: str, username: str) -> str:
        payload = self._load_dpapi_store()
        key = self._dpapi_key(service, username)
        if key not in payload:
            raise SecretNotFoundError("secret nao encontrado no cofre local windows")
        try:
            encrypted = base64.b64decode(payload[key].encode("ascii"), validate=True)
            secret = self._dpapi_unprotect(encrypted).decode("utf-8")
        except Exception as exc:
            raise SecretProviderError("falha ao ler cofre local windows") from exc
        if not secret:
            raise SecretNotFoundError("secret vazio no cofre local windows")
        return secret

    def _test_dpapi_backend(self) -> bool:
        try:
            sample = b"scrap_report_healthcheck"
            return self._dpapi_unprotect(self._dpapi_protect(sample)) == sample
        except Exception:
            return False

    def set_secret(self, service: str, username: str, secret: str) -> None:
        if not secret.strip():
            raise SecretProviderError("secret vazio nao permitido")
        cm_error: SecretProviderError | None = None
        try:
            self._set_secret_via_credential_manager(service, username, secret)
            return
        except SecretProviderError as exc:
            cm_error = exc

        try:
            self._set_secret_via_dpapi_store(service, username, secret)
            return
        except SecretProviderError as exc:
            if cm_error is not None:
                raise SecretProviderError(
                    "falha ao gravar credencial no windows vault e no cofre local windows"
                ) from exc
            raise

    def get_secret(self, service: str, username: str) -> str:
        cm_error: SecretProviderError | None = None
        try:
            return self._get_secret_via_credential_manager(service, username)
        except SecretNotFoundError:
            pass
        except SecretProviderError as exc:
            cm_error = exc

        try:
            return self._get_secret_via_dpapi_store(service, username)
        except SecretNotFoundError:
            if cm_error is not None:
                raise cm_error
            raise
        except SecretProviderError as exc:
            if cm_error is not None:
                raise SecretProviderError(
                    "falha ao ler credencial no windows vault e no cofre local windows"
                ) from exc
            raise

    def test_backend(self) -> bool:
        cm_ok = False
        try:
            cm_ok = self._test_credential_manager_backend()
        except SecretProviderError:
            cm_ok = False
        return cm_ok or self._test_dpapi_backend()


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
        if not secret.strip():
            raise SecretProviderError("secret vazio nao permitido")
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
