import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools import v137_release_assets as assets
from tools import verify_v137_release_assets as verifier


class FakeResponse:
    def __init__(self, request, payload=b"", *, status=200, size=None):
        self.status = status
        self._payload = payload
        self._offset = 0
        self.headers = {
            "Content-Length": str(len(payload) if size is None else size)
        }
        self._url = request.full_url + "?download=1"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self._url

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self._payload) - self._offset
        start = self._offset
        self._offset = min(len(self._payload), start + size)
        return self._payload[start : self._offset]


def pe_payload(*, machine=verifier.PE_MACHINE_AMD64):
    payload = bytearray(512)
    payload[:2] = b"MZ"
    struct.pack_into("<I", payload, 0x3C, 0x80)
    payload[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", payload, 0x84, machine)
    struct.pack_into("<H", payload, 0x98, 0x020B)
    return bytes(payload)


def elf_payload(architecture):
    payload = bytearray(64)
    payload[:4] = b"\x7fELF"
    payload[4] = 2
    payload[5] = 1
    machine = {
        "x86_64": verifier.ELF_MACHINE_X86_64,
        "arm64": verifier.ELF_MACHINE_AARCH64,
    }[architecture]
    struct.pack_into("<H", payload, 18, machine)
    return bytes(payload)


def linux_archive(filename, architecture, *, mode=0o755):
    executable_name = filename.removesuffix(".tar.gz")
    payload = elf_payload(architecture)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        info = tarfile.TarInfo(executable_name)
        info.mode = mode
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return output.getvalue()


def macho_payload(architecture):
    cpu_type = {
        "x86_64": verifier.MACH_CPU_X86_64,
        "arm64": verifier.MACH_CPU_ARM64,
    }[architecture]
    return b"\xcf\xfa\xed\xfe" + struct.pack("<I", cpu_type) + bytes(56)


def macos_archive(architecture):
    app_name = f"Langrisser II Korean Patcher {assets.RELEASE_TAG}"
    executable_name = f"{app_name}.app/Contents/MacOS/{app_name}"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(executable_name)
        info.create_system = 3
        info.external_attr = 0o100755 << 16
        archive.writestr(info, macho_payload(architecture))
    return output.getvalue()


def valid_payloads():
    return {
        assets.WINDOWS_PATCHER_ASSET: pe_payload(),
        assets.LINUX_PATCHER_ASSETS["x86_64"]: linux_archive(
            assets.LINUX_PATCHER_ASSETS["x86_64"], "x86_64"
        ),
        assets.LINUX_PATCHER_ASSETS["arm64"]: linux_archive(
            assets.LINUX_PATCHER_ASSETS["arm64"], "arm64"
        ),
        assets.MACOS_PATCHER_ASSETS["arm64"]: macos_archive("arm64"),
        assets.MACOS_PATCHER_ASSETS["x86_64"]: macos_archive("x86_64"),
    }


def release_payload(payloads, *, extra_assets=(), overrides=None):
    overrides = overrides or {}
    records = []
    for filename, payload in payloads.items():
        record = {
            "name": filename,
            "state": "uploaded",
            "size": len(payload),
            "digest": f"sha256:{hashlib.sha256(payload).hexdigest()}",
            "browser_download_url": verifier.asset_url(filename),
        }
        record.update(overrides.get(filename, {}))
        records.append(record)
    records.extend(extra_assets)
    return json.dumps(
        {
            "id": 137,
            "tag_name": assets.RELEASE_TAG,
            "draft": False,
            "prerelease": False,
            "published_at": "2026-08-11T00:00:00Z",
            "assets": records,
        }
    ).encode()


def fake_opener(payloads, release):
    def opener(request, *, timeout):
        if request.full_url == verifier.RELEASE_API_URL:
            return FakeResponse(request, release)
        filename = request.full_url.rsplit("/", 1)[-1]
        return FakeResponse(request, payloads[filename])

    return opener


class V137ReleaseAssetHttpTests(unittest.TestCase):
    def test_exact_five_urls_use_the_candidate_tag(self):
        urls = [verifier.asset_url(name) for name in assets.PATCHER_ASSET_FILENAMES]
        self.assertEqual(len(urls), 5)
        self.assertTrue(all("/releases/download/v1.3.7/" in url for url in urls))
        self.assertEqual(
            {url.rsplit("/", 1)[-1] for url in urls},
            set(assets.PATCHER_ASSET_FILENAMES),
        )

    def test_pending_release_head_probe_requires_200_and_nonzero_size(self):
        def opener(request, *, timeout):
            self.assertEqual(request.method, "HEAD")
            self.assertEqual(timeout, 1.0)
            return FakeResponse(request, size=1234)

        row = verifier.probe_asset(
            assets.WINDOWS_PATCHER_ASSET,
            opener=opener,
            timeout=1.0,
        )
        self.assertEqual(row["status"], "pass")
        self.assertEqual(row["content_length"], 1234)

    def test_pending_release_head_probe_rejects_zero_or_non_200(self):
        def opener(request, *, timeout):
            return FakeResponse(request, status=404, size=0)

        row = verifier.probe_asset(
            assets.WINDOWS_PATCHER_ASSET,
            opener=opener,
        )
        self.assertEqual(row["status"], "fail")

    def test_full_fixture_checks_exact_set_digest_formats_and_self_tests(self):
        payloads = valid_payloads()
        release = release_payload(payloads)
        calls = []

        def self_test_runner(payload, name, platform, architecture, timeout):
            self.assertTrue(payload)
            self.assertGreater(timeout, 0)
            calls.append((name, platform, architecture))
            return {"status": "pass", "exit_code": 0}

        with TemporaryDirectory() as temporary:
            report = verifier.verify_all(
                opener=fake_opener(payloads, release),
                timeout=1.0,
                download_dir=Path(temporary),
                self_test_runner=self_test_runner,
            )
            self.assertEqual(
                {path.name for path in Path(temporary).iterdir()},
                set(assets.PATCHER_ASSET_FILENAMES),
            )
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["exact_asset_set_verified"])
        self.assertEqual(report["passed_asset_count"], 5)
        self.assertEqual(len(calls), 5)
        observed = {
            (
                row["inspection"]["platform"],
                row["inspection"]["architecture"],
            )
            for row in report["results"]
        }
        self.assertEqual(
            observed,
            {
                ("windows", "x86_64"),
                ("linux", "x86_64"),
                ("linux", "arm64"),
                ("macos", "arm64"),
                ("macos", "x86_64"),
            },
        )
        linux = [
            row
            for row in report["results"]
            if row["inspection"]["platform"] == "linux"
        ]
        self.assertTrue(
            all(row["inspection"]["executable_mode"] == "0o755" for row in linux)
        )

    def test_release_api_rejects_extra_or_missing_assets_before_download(self):
        payloads = valid_payloads()
        extra = {
            "name": "unexpected-checksum.txt",
            "state": "uploaded",
            "size": 1,
            "digest": f"sha256:{'0' * 64}",
            "browser_download_url": "https://example.invalid/checksum",
        }
        opened = []

        def opener(request, *, timeout):
            opened.append(request.full_url)
            return FakeResponse(
                request,
                release_payload(payloads, extra_assets=(extra,)),
            )

        report = verifier.verify_all(opener=opener)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["exact_asset_set_verified"])
        self.assertEqual(report["observed_asset_count"], 6)
        self.assertIn("unexpected-checksum.txt", report["release_error"])
        self.assertEqual(opened, [verifier.RELEASE_API_URL])

    def test_download_digest_mismatch_fails(self):
        payloads = valid_payloads()
        filename = assets.WINDOWS_PATCHER_ASSET
        release = release_payload(
            payloads,
            overrides={filename: {"digest": f"sha256:{'0' * 64}"}},
        )
        report = verifier.verify_all(
            opener=fake_opener(payloads, release),
            run_self_tests=False,
        )
        row = next(value for value in report["results"] if value["filename"] == filename)
        self.assertEqual(report["status"], "fail")
        self.assertIn("downloaded SHA-256", row["error"])

    def test_wrong_pe_machine_is_rejected(self):
        payloads = valid_payloads()
        filename = assets.WINDOWS_PATCHER_ASSET
        payloads[filename] = pe_payload(machine=verifier.MACH_CPU_ARM64 & 0xFFFF)
        report = verifier.verify_all(
            opener=fake_opener(payloads, release_payload(payloads)),
            run_self_tests=False,
        )
        row = next(value for value in report["results"] if value["filename"] == filename)
        self.assertEqual(report["status"], "fail")
        self.assertIn("expected AMD64 0x8664", row["error"])

    def test_linux_archive_requires_executable_permission(self):
        payloads = valid_payloads()
        filename = assets.LINUX_PATCHER_ASSETS["x86_64"]
        payloads[filename] = linux_archive(filename, "x86_64", mode=0o644)
        report = verifier.verify_all(
            opener=fake_opener(payloads, release_payload(payloads)),
            run_self_tests=False,
        )
        row = next(value for value in report["results"] if value["filename"] == filename)
        self.assertEqual(report["status"], "fail")
        self.assertIn("executable permission bits", row["error"])

    def test_macos_archive_requires_matching_thin_architecture(self):
        payloads = valid_payloads()
        filename = assets.MACOS_PATCHER_ASSETS["arm64"]
        payloads[filename] = macos_archive("x86_64")
        report = verifier.verify_all(
            opener=fake_opener(payloads, release_payload(payloads)),
            run_self_tests=False,
        )
        row = next(value for value in report["results"] if value["filename"] == filename)
        self.assertEqual(report["status"], "fail")
        self.assertIn("does not match arm64", row["error"])

    def test_default_self_test_runner_skips_foreign_target(self):
        report = verifier.run_native_self_test(
            b"not executed",
            "foreign.exe",
            "foreign-os",
            "foreign-arch",
            1.0,
        )
        self.assertEqual(report["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
