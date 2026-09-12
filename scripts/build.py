#!/usr/bin/env python3
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "packs"
DIST_ROOT = ROOT / "dist"
INDEX_PATH = ROOT / "index.json"
RAW_BASE = "https://raw.githubusercontent.com/shinp-dev/chanriva-content/main/dist"
FIXED_ZIP_TIME = (2026, 9, 12, 0, 0, 0)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def add_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, payload)


def build_pack(pack_dir: Path):
    manifest = read_json(pack_dir / "manifest.json")
    cards = read_json(pack_dir / "cards.json")
    pack_id = manifest["id"]
    version = manifest["version"]
    archive_name = f"{pack_id}-v{version}.zip"
    archive_path = DIST_ROOT / archive_name

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        add_bytes(archive, "manifest.json", json_bytes(manifest))
        add_bytes(archive, "cards.json", json_bytes(cards))
        asset_root = pack_dir / "assets"
        if asset_root.is_dir():
            for path in sorted(p for p in asset_root.rglob("*") if p.is_file()):
                relative = path.relative_to(pack_dir).as_posix()
                add_bytes(archive, relative, path.read_bytes())

    raw = archive_path.read_bytes()
    return {
        "id": pack_id,
        "version": version,
        "url": f"{RAW_BASE}/{archive_name}",
        "sizeBytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def main() -> None:
    if DIST_ROOT.exists():
        shutil.rmtree(DIST_ROOT)
    DIST_ROOT.mkdir(parents=True)

    descriptors = []
    for pack_dir in sorted(p for p in PACK_ROOT.iterdir() if p.is_dir()):
        if not (pack_dir / "manifest.json").is_file() or not (pack_dir / "cards.json").is_file():
            continue
        descriptors.append(build_pack(pack_dir))

    index = {"schemaVersion": 1, "packs": descriptors}
    INDEX_PATH.write_bytes(json_bytes(index))
    print(f"built {len(descriptors)} packs")


if __name__ == "__main__":
    main()
