from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.run_blastem_sequence import (
    BLASTEM_SRAM_SIZE,
    GENESIS_PLUS_GX_SRM_SIZE,
    SRAM_FORMAT_MARKER,
    SRAM_FORMAT_MARKER_OFFSET,
    SRAM_VALID_FLAGS_OFFSET,
    MANUAL_SLOT_BASES,
    MANUAL_SLOT_CHECKSUM_DATA_SIZE,
    MANUAL_SLOT_CHECKSUM_OFFSET,
    copy_manual_slot,
    genesis_plus_gx_srm_to_blastem,
    import_manual_slot_srm,
    manual_slot_checksum,
    manual_slot_scenario_number,
)


class GenesisPlusGxSramImportTests(unittest.TestCase):
    def make_blastem_sram(self) -> bytes:
        payload = bytearray(BLASTEM_SRAM_SIZE)
        payload[
            SRAM_FORMAT_MARKER_OFFSET : SRAM_FORMAT_MARKER_OFFSET + 2
        ] = SRAM_FORMAT_MARKER.to_bytes(2, "big")
        return bytes(payload)

    def interleave(self, payload: bytes) -> bytes:
        result = bytearray([0xFF]) * GENESIS_PLUS_GX_SRM_SIZE
        result[1:0x4000:2] = payload
        return bytes(result)

    def test_extracts_interleaved_64k_genesis_plus_gx_save(self) -> None:
        expected = self.make_blastem_sram()
        self.assertEqual(
            genesis_plus_gx_srm_to_blastem(self.interleave(expected)),
            expected,
        )

    def test_accepts_native_8k_blastem_save(self) -> None:
        expected = self.make_blastem_sram()
        self.assertEqual(genesis_plus_gx_srm_to_blastem(expected), expected)

    def test_rejects_non_padding_even_byte(self) -> None:
        payload = bytearray(self.interleave(self.make_blastem_sram()))
        payload[2] = 0
        with self.assertRaisesRegex(ValueError, "even-byte padding"):
            genesis_plus_gx_srm_to_blastem(bytes(payload))

    def test_rejects_non_padding_tail_byte(self) -> None:
        payload = bytearray(self.interleave(self.make_blastem_sram()))
        payload[0x4000] = 0
        with self.assertRaisesRegex(ValueError, "beyond its used range"):
            genesis_plus_gx_srm_to_blastem(bytes(payload))

    def test_rejects_invalid_format_marker(self) -> None:
        payload = bytearray(self.make_blastem_sram())
        payload[SRAM_FORMAT_MARKER_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "invalid format marker"):
            genesis_plus_gx_srm_to_blastem(self.interleave(bytes(payload)))

    def test_import_writes_only_the_contiguous_payload(self) -> None:
        expected = self.make_blastem_sram()
        with TemporaryDirectory() as directory:
            source = Path(directory) / "input.srm"
            destination = Path(directory) / "runtime/save.sram"
            source.write_bytes(self.interleave(expected))
            import_manual_slot_srm(source, destination)
            self.assertEqual(destination.read_bytes(), expected)

    def test_copies_a_valid_saved_slot_over_slot_one(self) -> None:
        payload = bytearray(self.make_blastem_sram())
        source = MANUAL_SLOT_BASES[2]
        payload[source : source + 2] = (13).to_bytes(2, "big")
        payload[source + 2 : source + 6] = b"S13!"
        checksum = manual_slot_checksum(payload, source)
        payload[
            source + MANUAL_SLOT_CHECKSUM_OFFSET :
            source + MANUAL_SLOT_CHECKSUM_OFFSET + 2
        ] = checksum.to_bytes(2, "big")
        payload[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = (
            1 << 3
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(payload)
            copy_manual_slot(path, 2)
            copied = path.read_bytes()
            destination = MANUAL_SLOT_BASES[0]
            size = MANUAL_SLOT_CHECKSUM_OFFSET + 2
            self.assertEqual(
                copied[destination : destination + size],
                copied[source : source + size],
            )
            self.assertEqual(manual_slot_scenario_number(path), 13)

    def test_copy_rejects_an_invalid_source_slot(self) -> None:
        payload = bytearray(self.make_blastem_sram())
        payload[SRAM_VALID_FLAGS_OFFSET : SRAM_VALID_FLAGS_OFFSET + 2] = (
            1 << 3
        ).to_bytes(2, "big")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.sram"
            path.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, "invalid checksum"):
                copy_manual_slot(path, 2)


if __name__ == "__main__":
    unittest.main()
