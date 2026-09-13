"""Build/validate independently versioned Standard opponent packs. No dynamic policies/code."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "opponents"
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_ASSET = 8 * 1024 * 1024
MAX_MANIFEST = 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
ASSET = re.compile(r"assets/[a-z0-9_-]+\.(png|webp|jpg|jpeg)\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def schema(name, value):
    Draft202012Validator(read_json((ROOT / "schema" / f"{name}.schema.json").read_bytes()),
                        format_checker=FormatChecker()).validate(value)


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_manifest(manifest):
    schema("manifest", manifest)
    players = {p["id"]: p for p in manifest["players"]}
    require(len(players) == len(manifest["players"]), "Duplicate player ID")
    visited, visiting = set(), set()
    def visit(key):
        if key in visited:
            return
        require(key in players and key not in visiting, "Unknown or cyclic prerequisite")
        visiting.add(key)
        for parent in players[key]["requires"]:
            visit(parent)
        visiting.remove(key)
        visited.add(key)
    for key in players:
        visit(key)
    for player in players.values():
        ai = player["ai"]
        moves = ai["moves"]
        weights = [moves[k] for k in ("openingWeights", "midgameWeights", "endgameWeights")]
        require(len({len(w) for w in weights}) == 1 and all(w[0] > 0 for w in weights), "Invalid weights")
        require(moves["midgamePly"] < moves["endgamePly"], "Invalid phase boundaries")
        require(ai["think"]["minMs"] <= ai["think"]["maxMs"], "Invalid think time bounds")
        require(ai["tension"]["tenseScore"] < ai["tension"]["criticalScore"], "Invalid tension bounds")
        for value in player["name"].values():
            require(value.strip(), "Blank name")
    for key in ("title", "description"):
        require(all(v.strip() for v in manifest[key].values()), "Blank text")
    if "availableFrom" in manifest and "availableUntil" in manifest:
        require(instant(manifest["availableFrom"]) < instant(manifest["availableUntil"]), "Invalid availability")
    return {manifest["banner"]} | {p[k] for p in players.values() for k in ("portrait", "winImage", "loseImage")}


def validate_image(raw):
    require(0 < len(raw) <= MAX_ASSET, "Image size limit")
    with Image.open(io.BytesIO(raw)) as image:
        require(image.format in {"PNG", "WEBP", "JPEG"}, "Unsupported image format")
        require(1 <= image.width <= 2048 and 1 <= image.height <= 2048, "Image dimensions limit")
        require(getattr(image, "n_frames", 1) == 1, "Animated image not supported")
        image.verify()


def validate_archive(raw, descriptor):
    require(len(raw) == descriptor["sizeBytes"] and len(raw) <= MAX_ARCHIVE, "Archive size mismatch")
    require(hashlib.sha256(raw).hexdigest() == descriptor["sha256"], "Archive SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)) and len(names) <= 256, "Duplicate/too many ZIP entries")
        require(sum(i.file_size for i in infos) <= MAX_EXPANDED, "Expanded size limit")
        for entry in infos:
            require(not entry.is_dir() and (entry.filename == "manifest.json" or ASSET.fullmatch(entry.filename)), "Unsafe ZIP path")
            require((entry.external_attr >> 16) & 0o170000 != 0o120000, "Symlink forbidden")
            require(entry.file_size <= (MAX_MANIFEST if entry.filename == "manifest.json" else MAX_ASSET), "Entry size limit")
        manifest = read_json(archive.read("manifest.json"))
        require(manifest["id"] == descriptor["id"] and manifest["version"] == descriptor["version"], "Manifest identity mismatch")
        assets = validate_manifest(manifest)
        require(set(names) == assets | {"manifest.json"}, "Missing/unreferenced assets")
        for path in assets:
            validate_image(archive.read(path))
        return manifest


def validate_index(index):
    schema("index", index)
    require(len({p["id"] for p in index["packs"]}) == len(index["packs"]), "Duplicate pack ID")
    require(len(encoded(index)) <= 128 * 1024, "Index size limit")
    for p in index["packs"]:
        url = urlparse(p["url"])
        require(url.scheme == "https" and url.hostname and not url.username and not url.password and not url.fragment and url.port in (None, 443), "Unsafe URL")


def build():
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    descriptors = []
    for folder in sorted((ROOT / "packs").iterdir()):
        if not folder.is_dir():
            continue
        manifest = read_json((folder / "manifest.json").read_bytes())
        paths = validate_manifest(manifest)
        require(folder.name == manifest["id"], "Pack folder/ID mismatch")
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in ["manifest.json"] + sorted(paths):
                file = folder / name
                require(not file.is_symlink(), "Source symlink forbidden")
                raw = encoded(manifest) if name == "manifest.json" else file.read_bytes()
                info = zipfile.ZipInfo(name, (2026, 9, 13, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
        raw = payload.getvalue()
        filename = f'{manifest["id"]}-v{manifest["version"]}.zip'
        descriptor = dict(id=manifest["id"], version=manifest["version"], sizeBytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                          url=f"https://raw.githubusercontent.com/shinp-dev/chanriva-content/main/opponents/dist/{filename}")
        validate_archive(raw, descriptor)
        target = dist / filename
        require(not target.exists() or target.read_bytes() == raw, "Published version is immutable: increment version")
        target.write_bytes(raw)
        descriptors.append(descriptor)
    index = dict(schemaVersion=1, packs=descriptors)
    validate_index(index)
    (ROOT / "index.json").write_bytes(encoded(index))
    print(f"Built {len(descriptors)} opponent packs")


def validate():
    index = read_json((ROOT / "index.json").read_bytes())
    validate_index(index)
    for descriptor in index["packs"]:
        path = ROOT / "dist" / f'{descriptor["id"]}-v{descriptor["version"]}.zip'
        manifest = validate_archive(path.read_bytes(), descriptor)
        folder = ROOT / "packs" / descriptor["id"]
        require(manifest == read_json((folder / "manifest.json").read_bytes()), "Source/ZIP manifest mismatch")
        with zipfile.ZipFile(path) as archive:
            for asset in validate_manifest(manifest):
                require(archive.read(asset) == (folder / asset).read_bytes(), "Source/ZIP image mismatch")
    print(f"Validated {len(index['packs'])} opponent packs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "validate"])
    args = parser.parse_args()
    (build if args.command == "build" else validate)()
