#!/usr/bin/env python3
"""Verify the exact five published v1.3.7 platform patcher assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
from typing import Callable
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.v137_release_assets import (  # noqa: E402
    LINUX_PATCHER_ASSETS,
    MACOS_PATCHER_ASSETS,
    PATCHER_ASSET_FILENAMES,
    RELEASE_TAG,
    WINDOWS_PATCHER_ASSET,
)


REPOSITORY = "hsp1324/lang2_md"
RELEASE_API_URL = (
    f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{RELEASE_TAG}"
)
DEFAULT_OUTPUT = ROOT / "tmp/v137-release-assets-verification.json"
MAX_ASSET_SIZE = 256 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_SIZE = 512 * 1024 * 1024
PE_MACHINE_AMD64 = 0x8664
ELF_MACHINE_X86_64 = 62
ELF_MACHINE_AARCH64 = 183
MACH_CPU_X86_64 = 0x01000007
MACH_CPU_ARM64 = 0x0100000C
USER_AGENT = "lang2-md-v1.3.7-release-verifier"

ASSET_SPECS = {
    WINDOWS_PATCHER_ASSET: {
        "platform": "windows",
        "architecture": "x86_64",
        "container": "pe",
    },
    LINUX_PATCHER_ASSETS["x86_64"]: {
        "platform": "linux",
        "architecture": "x86_64",
        "container": "tar.gz",
    },
    LINUX_PATCHER_ASSETS["arm64"]: {
        "platform": "linux",
        "architecture": "arm64",
        "container": "tar.gz",
    },
    MACOS_PATCHER_ASSETS["arm64"]: {
        "platform": "macos",
        "architecture": "arm64",
        "container": "app.zip",
    },
    MACOS_PATCHER_ASSETS["x86_64"]: {
        "platform": "macos",
        "architecture": "x86_64",
        "container": "app.zip",
    },
}


class VerificationError(ValueError):
    """A release or downloaded asset violates the v1.3.7 contract."""


def asset_url(filename: str) -> str:
    return (
        f"https://github.com/{REPOSITORY}/releases/download/"
        f"{RELEASE_TAG}/{filename}"
    )


def _request(url: str, *, method: str = "GET") -> Request:
    return Request(
        url,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )


def probe_asset(
    filename: str,
    *,
    opener: Callable[..., object] = urlopen,
    timeout: float = 30.0,
) -> dict[str, object]:
    """Retain the small HEAD probe used by pending-release diagnostics."""
    url = asset_url(filename)
    try:
        with opener(_request(url, method="HEAD"), timeout=timeout) as response:
            status = int(response.status)
            length_header = response.headers.get("Content-Length")
            size = int(length_header) if length_header is not None else 0
            final_url = str(response.geturl())
    except Exception as exc:
        return {
            "filename": filename,
            "url": url,
            "status": "fail",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    passed = status == 200 and size > 0
    return {
        "filename": filename,
        "url": url,
        "status": "pass" if passed else "fail",
        "http_status": status,
        "content_length": size,
        "final_url": final_url,
    }


def _response_bytes(response: object) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _fetch_release(
    *,
    opener: Callable[..., object],
    timeout: float,
) -> dict[str, object]:
    try:
        with opener(_request(RELEASE_API_URL), timeout=timeout) as response:
            status_code = int(response.status)
            payload = _response_bytes(response)
    except Exception as exc:
        raise VerificationError(
            f"GitHub Release API request failed: {type(exc).__name__}: {exc}"
        ) from exc
    if status_code != 200:
        raise VerificationError(
            f"GitHub Release API returned HTTP {status_code}, expected 200"
        )
    try:
        release = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("GitHub Release API returned invalid JSON") from exc
    if not isinstance(release, dict):
        raise VerificationError("GitHub Release API payload is not an object")
    if release.get("tag_name") != RELEASE_TAG:
        raise VerificationError("GitHub Release API returned the wrong tag")
    if release.get("draft") is not False or not release.get("published_at"):
        raise VerificationError("v1.3.7 is not a published release")
    if release.get("prerelease") is not False:
        raise VerificationError("v1.3.7 is unexpectedly marked as a prerelease")
    return release


def _release_assets_by_name(
    release: dict[str, object],
) -> dict[str, dict[str, object]]:
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list):
        raise VerificationError("GitHub Release API assets field is not a list")
    assets: dict[str, dict[str, object]] = {}
    duplicate_names: set[str] = set()
    for value in raw_assets:
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            raise VerificationError("GitHub Release API has a malformed asset")
        name = str(value["name"])
        if name in assets:
            duplicate_names.add(name)
        assets[name] = value
    expected = set(PATCHER_ASSET_FILENAMES)
    observed = set(assets)
    if duplicate_names or len(raw_assets) != 5 or observed != expected:
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        raise VerificationError(
            "release asset set differs from the exact five-file contract: "
            f"missing={missing}, unexpected={unexpected}, "
            f"duplicates={sorted(duplicate_names)}, count={len(raw_assets)}"
        )
    return assets


def _expected_digest(asset: dict[str, object], filename: str) -> str:
    digest = asset.get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise VerificationError(f"{filename}: GitHub SHA-256 digest is absent")
    value = digest.removeprefix("sha256:").lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise VerificationError(f"{filename}: GitHub SHA-256 digest is malformed")
    return value


def _download_asset(
    asset: dict[str, object],
    destination: Path,
    *,
    opener: Callable[..., object],
    timeout: float,
) -> dict[str, object]:
    filename = destination.name
    if asset.get("state") != "uploaded":
        raise VerificationError(f"{filename}: GitHub asset state is not uploaded")
    try:
        api_size = int(asset["size"])
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError(f"{filename}: GitHub asset size is invalid") from exc
    if not 0 < api_size <= MAX_ASSET_SIZE:
        raise VerificationError(
            f"{filename}: GitHub asset size {api_size} is outside the safe range"
        )
    expected_url = asset_url(filename)
    if asset.get("browser_download_url") != expected_url:
        raise VerificationError(f"{filename}: browser download URL is not canonical")
    expected_sha256 = _expected_digest(asset, filename)

    digest = hashlib.sha256()
    downloaded_size = 0
    try:
        with opener(_request(expected_url), timeout=timeout) as response:
            status_code = int(response.status)
            final_url = str(response.geturl())
            length_header = response.headers.get("Content-Length")
            with destination.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded_size += len(chunk)
                    if downloaded_size > MAX_ASSET_SIZE:
                        raise VerificationError(
                            f"{filename}: download exceeded the safe size limit"
                        )
                    digest.update(chunk)
                    handle.write(chunk)
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError(
            f"{filename}: download failed: {type(exc).__name__}: {exc}"
        ) from exc
    if status_code != 200:
        raise VerificationError(
            f"{filename}: download returned HTTP {status_code}, expected 200"
        )
    if downloaded_size != api_size:
        raise VerificationError(
            f"{filename}: downloaded size {downloaded_size} != API size {api_size}"
        )
    if length_header is not None and int(length_header) != downloaded_size:
        raise VerificationError(f"{filename}: HTTP Content-Length does not match")
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise VerificationError(
            f"{filename}: downloaded SHA-256 does not match GitHub digest"
        )
    return {
        "http_status": status_code,
        "content_length": downloaded_size,
        "final_url": final_url,
        "sha256": actual_sha256,
        "github_digest": f"sha256:{expected_sha256}",
    }


def _inspect_pe(payload: bytes, expected_architecture: str) -> dict[str, object]:
    if len(payload) < 0x40 or payload[:2] != b"MZ":
        raise VerificationError("Windows asset is not an MZ executable")
    pe_offset = struct.unpack_from("<I", payload, 0x3C)[0]
    if pe_offset + 26 > len(payload) or payload[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise VerificationError("Windows asset has no valid PE header")
    machine = struct.unpack_from("<H", payload, pe_offset + 4)[0]
    optional_magic = struct.unpack_from("<H", payload, pe_offset + 24)[0]
    if expected_architecture != "x86_64" or machine != PE_MACHINE_AMD64:
        raise VerificationError(
            f"Windows PE Machine is 0x{machine:04X}, expected AMD64 0x8664"
        )
    if optional_magic != 0x020B:
        raise VerificationError("Windows PE optional header is not PE32+")
    return {
        "container": "pe",
        "platform": "windows",
        "architecture": "x86_64",
        "pe_machine": "0x8664",
        "pe_optional_header": "PE32+",
    }


def _inspect_elf(payload: bytes, expected_architecture: str) -> dict[str, object]:
    if len(payload) < 20 or payload[:4] != b"\x7fELF":
        raise VerificationError("Linux archive member is not an ELF executable")
    if payload[4] != 2 or payload[5] != 1:
        raise VerificationError("Linux executable is not 64-bit little-endian ELF")
    machine = struct.unpack_from("<H", payload, 18)[0]
    expected_machine = {
        "x86_64": ELF_MACHINE_X86_64,
        "arm64": ELF_MACHINE_AARCH64,
    }[expected_architecture]
    if machine != expected_machine:
        raise VerificationError(
            f"Linux ELF machine {machine} does not match {expected_architecture}"
        )
    return {
        "container": "elf-in-tar.gz",
        "platform": "linux",
        "architecture": expected_architecture,
        "elf_machine": machine,
    }


def _inspect_macho(payload: bytes, expected_architecture: str) -> dict[str, object]:
    if len(payload) < 8:
        raise VerificationError("macOS app executable is truncated")
    if payload[:4] == b"\xcf\xfa\xed\xfe":
        endian = "<"
    elif payload[:4] == b"\xfe\xed\xfa\xcf":
        endian = ">"
    else:
        raise VerificationError("macOS app executable is not a thin 64-bit Mach-O")
    cpu_type = struct.unpack_from(f"{endian}I", payload, 4)[0]
    expected_cpu = {
        "x86_64": MACH_CPU_X86_64,
        "arm64": MACH_CPU_ARM64,
    }[expected_architecture]
    if cpu_type != expected_cpu:
        raise VerificationError(
            f"macOS Mach-O CPU 0x{cpu_type:08X} does not match "
            f"{expected_architecture}"
        )
    return {
        "container": "mach-o-in-app.zip",
        "platform": "macos",
        "architecture": expected_architecture,
        "macho_cpu_type": f"0x{cpu_type:08X}",
    }


def _safe_archive_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _inspect_linux_archive(
    path: Path,
    filename: str,
    architecture: str,
) -> tuple[dict[str, object], bytes, str]:
    executable_name = filename.removesuffix(".tar.gz")
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) != 1 or members[0].name != executable_name:
                raise VerificationError(
                    f"{filename}: tar.gz must contain only {executable_name}"
                )
            member = members[0]
            if not _safe_archive_member(member.name) or not member.isfile():
                raise VerificationError(f"{filename}: unsafe archive member")
            if not 0 < member.size <= MAX_ASSET_SIZE:
                raise VerificationError(f"{filename}: executable size is unsafe")
            if member.mode & 0o111 == 0:
                raise VerificationError(
                    f"{filename}: Linux executable permission bits are absent"
                )
            extracted = archive.extractfile(member)
            if extracted is None:
                raise VerificationError(f"{filename}: executable cannot be read")
            payload = extracted.read(MAX_ASSET_SIZE + 1)
    except VerificationError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise VerificationError(f"{filename}: invalid tar.gz: {exc}") from exc
    if len(payload) != member.size:
        raise VerificationError(f"{filename}: tar member size does not match")
    inspection = _inspect_elf(payload, architecture)
    inspection["archive_member"] = executable_name
    inspection["executable_mode"] = f"0o{member.mode & 0o777:03o}"
    return inspection, payload, executable_name


def _inspect_macos_archive(
    path: Path,
    filename: str,
    architecture: str,
) -> tuple[dict[str, object], bytes, str]:
    app_name = f"Langrisser II Korean Patcher {RELEASE_TAG}"
    executable_name = f"{app_name}.app/Contents/MacOS/{app_name}"
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or any(not _safe_archive_member(info.filename) for info in infos):
                raise VerificationError(f"{filename}: unsafe or empty ZIP")
            expanded_size = sum(info.file_size for info in infos)
            if expanded_size > MAX_ARCHIVE_EXPANDED_SIZE:
                raise VerificationError(f"{filename}: ZIP expanded size is unsafe")
            corrupt = archive.testzip()
            if corrupt is not None:
                raise VerificationError(f"{filename}: corrupt ZIP member {corrupt}")
            try:
                info = archive.getinfo(executable_name)
            except KeyError as exc:
                raise VerificationError(
                    f"{filename}: app executable is absent"
                ) from exc
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode) or info.is_dir():
                raise VerificationError(f"{filename}: app executable is not a file")
            if not 0 < info.file_size <= MAX_ASSET_SIZE:
                raise VerificationError(f"{filename}: app executable size is unsafe")
            payload = archive.read(info)
    except VerificationError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise VerificationError(f"{filename}: invalid app ZIP: {exc}") from exc
    inspection = _inspect_macho(payload, architecture)
    inspection["archive_member"] = executable_name
    if unix_mode:
        inspection["executable_mode"] = f"0o{unix_mode & 0o777:03o}"
    return inspection, payload, app_name


def _inspect_asset(
    path: Path,
    filename: str,
) -> tuple[dict[str, object], bytes, str]:
    spec = ASSET_SPECS[filename]
    architecture = str(spec["architecture"])
    if spec["container"] == "pe":
        payload = path.read_bytes()
        return _inspect_pe(payload, architecture), payload, filename
    if spec["container"] == "tar.gz":
        return _inspect_linux_archive(path, filename, architecture)
    return _inspect_macos_archive(path, filename, architecture)


def _normalized_host_architecture() -> str:
    value = platform.machine().lower()
    if value in {"amd64", "x64", "x86_64"}:
        return "x86_64"
    if value in {"aarch64", "arm64"}:
        return "arm64"
    return value


def run_native_self_test(
    payload: bytes,
    executable_name: str,
    platform_name: str,
    architecture: str,
    timeout: float,
) -> dict[str, object]:
    """Run only a downloaded binary matching the current OS and CPU."""
    host_platform = {"darwin": "macos", "win32": "windows"}.get(
        sys.platform,
        "linux" if sys.platform.startswith("linux") else sys.platform,
    )
    host_architecture = _normalized_host_architecture()
    if (platform_name, architecture) != (host_platform, host_architecture):
        return {
            "status": "skipped",
            "reason": (
                f"foreign target {platform_name}/{architecture} on "
                f"{host_platform}/{host_architecture}"
            ),
        }
    with tempfile.TemporaryDirectory(prefix="v137-patcher-self-test-") as temporary:
        executable = Path(temporary) / Path(executable_name).name
        executable.write_bytes(payload)
        executable.chmod(0o700)
        safe_environment = {
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
            "TEMP": temporary,
            "TMP": temporary,
            "TMPDIR": temporary,
        }
        for variable in ("SYSTEMROOT", "WINDIR"):
            if variable in os.environ:
                safe_environment[variable] = os.environ[variable]
        try:
            completed = subprocess.run(
                [str(executable), "--self-test"],
                cwd=temporary,
                env=safe_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise VerificationError(
                f"native --self-test could not run: {type(exc).__name__}: {exc}"
            ) from exc
    output = completed.stdout[-4000:]
    if completed.returncode != 0 or f"self-test 통과: {RELEASE_TAG}" not in output:
        raise VerificationError(
            f"native --self-test failed with exit code {completed.returncode}: "
            f"{output.strip()}"
        )
    return {"status": "pass", "exit_code": 0, "output": output.strip()}


def _verify_downloaded_assets(
    release: dict[str, object],
    assets: dict[str, dict[str, object]],
    download_dir: Path,
    *,
    opener: Callable[..., object],
    timeout: float,
    run_self_tests: bool,
    self_test_runner: Callable[..., dict[str, object]],
) -> dict[str, object]:
    download_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for filename in PATCHER_ASSET_FILENAMES:
        row: dict[str, object] = {
            "filename": filename,
            "url": asset_url(filename),
            "status": "fail",
        }
        destination = download_dir / filename
        try:
            row.update(
                _download_asset(
                    assets[filename],
                    destination,
                    opener=opener,
                    timeout=timeout,
                )
            )
            inspection, executable_payload, executable_name = _inspect_asset(
                destination,
                filename,
            )
            row["inspection"] = inspection
            if run_self_tests:
                self_test = self_test_runner(
                    executable_payload,
                    executable_name,
                    str(ASSET_SPECS[filename]["platform"]),
                    str(ASSET_SPECS[filename]["architecture"]),
                    timeout,
                )
                if self_test.get("status") not in {"pass", "skipped"}:
                    raise VerificationError(
                        f"{filename}: self-test returned an invalid status"
                    )
                row["self_test"] = self_test
            else:
                row["self_test"] = {
                    "status": "skipped",
                    "reason": "disabled by --skip-self-tests",
                }
            row["status"] = "pass"
        except Exception as exc:
            row["error_type"] = type(exc).__name__
            row["error"] = str(exc)
        results.append(row)

    passed = sum(row["status"] == "pass" for row in results)
    return {
        "schema_version": 2,
        "status": "pass" if passed == 5 else "fail",
        "repository": REPOSITORY,
        "release": RELEASE_TAG,
        "release_id": release.get("id"),
        "published_at": release.get("published_at"),
        "expected_asset_count": 5,
        "observed_asset_count": len(assets),
        "exact_asset_set_verified": True,
        "passed_asset_count": passed,
        "results": results,
    }


def verify_all(
    *,
    opener: Callable[..., object] = urlopen,
    timeout: float = 30.0,
    download_dir: Path | None = None,
    run_self_tests: bool = True,
    self_test_runner: Callable[..., dict[str, object]] = run_native_self_test,
) -> dict[str, object]:
    """Verify the published API set and every downloaded release asset."""
    try:
        release = _fetch_release(opener=opener, timeout=timeout)
    except Exception as exc:
        return {
            "schema_version": 2,
            "status": "fail",
            "repository": REPOSITORY,
            "release": RELEASE_TAG,
            "expected_asset_count": 5,
            "observed_asset_count": 0,
            "exact_asset_set_verified": False,
            "passed_asset_count": 0,
            "release_error_type": type(exc).__name__,
            "release_error": str(exc),
            "results": [],
        }
    raw_assets = release.get("assets")
    observed_asset_count = len(raw_assets) if isinstance(raw_assets, list) else 0
    try:
        assets = _release_assets_by_name(release)
    except Exception as exc:
        return {
            "schema_version": 2,
            "status": "fail",
            "repository": REPOSITORY,
            "release": RELEASE_TAG,
            "release_id": release.get("id"),
            "published_at": release.get("published_at"),
            "expected_asset_count": 5,
            "observed_asset_count": observed_asset_count,
            "exact_asset_set_verified": False,
            "passed_asset_count": 0,
            "release_error_type": type(exc).__name__,
            "release_error": str(exc),
            "results": [],
        }
    if download_dir is not None:
        return _verify_downloaded_assets(
            release,
            assets,
            download_dir,
            opener=opener,
            timeout=timeout,
            run_self_tests=run_self_tests,
            self_test_runner=self_test_runner,
        )
    with tempfile.TemporaryDirectory(prefix="v137-release-assets-") as temporary:
        return _verify_downloaded_assets(
            release,
            assets,
            Path(temporary),
            opener=opener,
            timeout=timeout,
            run_self_tests=run_self_tests,
            self_test_runner=self_test_runner,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--skip-self-tests",
        action="store_true",
        help="inspect assets without executing a native OS/CPU match",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    report = verify_all(
        timeout=args.timeout,
        download_dir=args.download_dir,
        run_self_tests=not args.skip_self_tests,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if report.get("release_error"):
        print(f"release: fail: {report['release_error']}")
    for row in report["results"]:
        inspection = row.get("inspection", {})
        print(
            f"{row['filename']}: {row['status']} "
            f"HTTP {row.get('http_status', 'error')} "
            f"{row.get('content_length', 0)} bytes "
            f"{inspection.get('platform', '?')}/"
            f"{inspection.get('architecture', '?')}"
        )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
