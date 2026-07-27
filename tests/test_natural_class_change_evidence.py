from dataclasses import replace
import unittest

from tools import verify_natural_class_change_evidence as evidence


class NaturalClassChangeEvidenceTests(unittest.TestCase):
    def test_retained_gsts_prove_liana_natural_application(self):
        before = evidence.read_identities(evidence.DEFAULT_BEFORE.read_bytes())
        after = evidence.read_identities(evidence.DEFAULT_AFTER.read_bytes())
        evidence.verify(before, after)
        self.assertEqual(
            before[evidence.LIANA_RUNTIME_RECORD],
            evidence.RuntimeIdentity(0x02, 2, 3, 0),
        )
        self.assertEqual(
            after[evidence.LIANA_RUNTIME_RECORD],
            evidence.RuntimeIdentity(0x0A, 2, 1, 0),
        )

    def test_rejects_an_unrelated_identity_change(self):
        before = evidence.read_identities(evidence.DEFAULT_BEFORE.read_bytes())
        after = list(evidence.read_identities(evidence.DEFAULT_AFTER.read_bytes()))
        after[1] = replace(after[1], level=after[1].level + 1)
        with self.assertRaisesRegex(
            ValueError,
            "unrelated player runtime identities changed: 1",
        ):
            evidence.verify(before, tuple(after))

    def test_rejects_a_short_gst(self):
        with self.assertRaisesRegex(ValueError, "runtime record 0"):
            evidence.read_identities(b"")


if __name__ == "__main__":
    unittest.main()
