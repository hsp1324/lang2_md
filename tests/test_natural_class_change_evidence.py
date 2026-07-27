from dataclasses import replace
import unittest

from tools import verify_natural_class_change_evidence as evidence


class NaturalClassChangeEvidenceTests(unittest.TestCase):
    def test_retained_gsts_prove_liana_natural_application(self):
        before = evidence.read_identities(evidence.DEFAULT_BEFORE.read_bytes())
        after = evidence.read_identities(evidence.DEFAULT_AFTER.read_bytes())
        evidence.verify(before, after, evidence.LIANA_PROOF)
        self.assertEqual(
            before[evidence.LIANA_RUNTIME_RECORD],
            evidence.RuntimeIdentity(0x02, 2, 3, 0),
        )
        self.assertEqual(
            after[evidence.LIANA_RUNTIME_RECORD],
            evidence.RuntimeIdentity(0x0A, 2, 1, 0),
        )

    def test_retained_gsts_prove_sherry_natural_application(self):
        proof = evidence.SHERRY_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x01, 4, 9, 15),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x04, 4, 1, 0),
        )

    def test_retained_gsts_prove_aaron_natural_application(self):
        proof = evidence.AARON_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x01, 8, 8, 6),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x04, 8, 1, 0),
        )

    def test_retained_gsts_prove_scott_natural_application(self):
        proof = evidence.SCOTT_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x01, 6, 1, 0),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x06, 6, 1, 0),
        )

    def test_retained_gsts_prove_lana_natural_application(self):
        proof = evidence.LANA_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x02, 3, 1, 0),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x0A, 3, 1, 0),
        )

    def test_retained_gsts_prove_keith_natural_application(self):
        proof = evidence.KEITH_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x06, 7, 1, 5),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x0D, 7, 1, 0),
        )

    def test_retained_gsts_prove_lester_natural_application(self):
        proof = evidence.LESTER_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x07, 9, 7, 15),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x0D, 9, 1, 0),
        )

    def test_retained_gsts_prove_jessica_natural_application(self):
        proof = evidence.JESSICA_PROOF
        before = evidence.read_identities(proof.before_path.read_bytes())
        after = evidence.read_identities(proof.after_path.read_bytes())
        evidence.verify(before, after, proof)
        self.assertEqual(
            before[proof.runtime_record],
            evidence.RuntimeIdentity(0x09, 10, 5, 0),
        )
        self.assertEqual(
            after[proof.runtime_record],
            evidence.RuntimeIdentity(0x12, 10, 1, 0),
        )

    def test_rejects_an_unrelated_identity_change(self):
        before = evidence.read_identities(evidence.DEFAULT_BEFORE.read_bytes())
        after = list(evidence.read_identities(evidence.DEFAULT_AFTER.read_bytes()))
        after[1] = replace(after[1], level=after[1].level + 1)
        with self.assertRaisesRegex(
            ValueError,
            "unrelated player runtime identities changed: 1",
        ):
            evidence.verify(before, tuple(after), evidence.LIANA_PROOF)

    def test_rejects_a_short_gst(self):
        with self.assertRaisesRegex(ValueError, "runtime record 0"):
            evidence.read_identities(b"")


if __name__ == "__main__":
    unittest.main()
