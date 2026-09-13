import copy
import hashlib
import io
import unittest
import zipfile

import opponents as o


class OpponentValidationTest(unittest.TestCase):
    def setUp(self):
        self.manifest = o.read_json((o.ROOT / "packs/animal/manifest.json").read_bytes())

    def test_real_pack_and_distribution(self):
        o.validate()

    def test_rejects_cycles_missing_dependencies_and_duplicate_players(self):
        for dependency in ("chick", "rabbit", "unknown"):
            manifest = copy.deepcopy(self.manifest)
            manifest["players"][0]["requires"] = [dependency]
            with self.assertRaises(ValueError):
                o.validate_manifest(manifest)
        self.manifest["players"].append(self.manifest["players"][0])
        with self.assertRaises(ValueError):
            o.validate_manifest(self.manifest)

    def test_rejects_out_of_range_and_code_fields(self):
        for key, value in (("edaxLevel", 5), ("personality", "python"), ("script", "eval()")):
            manifest = copy.deepcopy(self.manifest)
            manifest["players"][0]["ai"][key] = value
            with self.assertRaises(Exception):
                o.validate_manifest(manifest)
        self.manifest["players"][0]["ai"]["think"]["baseMs"] = 5001
        with self.assertRaises(Exception):
            o.validate_manifest(self.manifest)

    def test_bounds_weights_and_paths(self):
        for key, value in (("midgamePly", 55), ("openingWeights", [0, 0]), ("endgameWeights", [1])):
            manifest = copy.deepcopy(self.manifest)
            manifest["players"][0]["ai"]["moves"][key] = value
            with self.assertRaises(Exception):
                o.validate_manifest(manifest)
        self.manifest["banner"] = "assets/../escape.png"
        with self.assertRaises(Exception):
            o.validate_manifest(self.manifest)

    def test_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            o.read_json('{"id":"animal","id":"other"}')

    def test_different_pack_with_shared_player_ids_is_valid(self):
        self.manifest["id"] = "beginner"
        self.manifest["home"] = dict(section="CHALLENGES", style="COMPACT", order=10)
        o.validate_manifest(self.manifest)

    def test_archive_traversal_and_hash_mismatch(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as archive:
            archive.writestr("../escape.png", b"bad")
        payload = raw.getvalue()
        descriptor = dict(id="animal", version=1, sizeBytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        with self.assertRaises(ValueError):
            o.validate_archive(payload, descriptor)
        descriptor["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            o.validate_archive(payload, descriptor)

    def test_oversized_image_dimensions(self):
        payload = io.BytesIO()
        o.Image.new("RGB", (2049, 1)).save(payload, format="PNG")
        with self.assertRaises(ValueError):
            o.validate_image(payload.getvalue())


if __name__ == "__main__":
    unittest.main()
