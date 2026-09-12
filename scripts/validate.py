#!/usr/bin/env python3
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.json"
ALLOWED_TYPES = {"trivia", "book", "history", "person", "collab"}
ALLOWED_RARITIES = {"common", "rare", "special"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
ASSET_RE = re.compile(r"^assets/[^\\:]+\.(?:webp|png|jpe?g)$", re.I)


def fail(message: str) -> None:
    raise ValueError(message)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require_https(value: str, label: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        fail(f"{label} must be an HTTPS URL without user info")


def validate_cards(data, label: str, zip_names=None):
    if data.get("schemaVersion") != 1 or not isinstance(data.get("cards"), list):
        fail(f"{label}: invalid cards root")
    if len(data["cards"]) > 5000:
        fail(f"{label}: too many cards")
    ids = set()
    for card in data["cards"]:
        for key in ("id", "type", "title", "summary"):
            if not isinstance(card.get(key), str) or not card[key].strip():
                fail(f"{label}: card required field {key} is invalid")
        card_id = card["id"]
        if not ID_RE.fullmatch(card_id) or card_id in ids:
            fail(f"{label}: duplicate/invalid card id {card_id}")
        ids.add(card_id)
        if card["type"] not in ALLOWED_TYPES:
            fail(f"{label}: invalid type for {card_id}")
        if card.get("rarity", "common") not in ALLOWED_RARITIES:
            fail(f"{label}: invalid rarity for {card_id}")
        image = card.get("imagePath")
        if image is not None:
            if not isinstance(image, str) or not ASSET_RE.fullmatch(image):
                fail(f"{label}: invalid imagePath for {card_id}")
            if any(part in {".", "..", ""} for part in image.split("/")):
                fail(f"{label}: unsafe imagePath for {card_id}")
            if zip_names is not None and image not in zip_names:
                fail(f"{label}: missing image asset {image}")
        for key in ("sourceUrl", "externalUrl"):
            if key in card:
                require_https(card[key], f"{label}:{card_id}:{key}")
    return ids


def main():
    index = read_json(INDEX)
    if index.get("schemaVersion") != 1 or not isinstance(index.get("packs"), list):
        fail("invalid index root")
    pack_ids = set()
    all_card_ids = set()
    for descriptor in index["packs"]:
        pack_id = descriptor.get("id")
        version = descriptor.get("version")
        if not isinstance(pack_id, str) or not PACK_ID_RE.fullmatch(pack_id) or pack_id in pack_ids:
            fail(f"duplicate/invalid pack id {pack_id}")
        pack_ids.add(pack_id)
        if not isinstance(version, int) or version < 1:
            fail(f"{pack_id}: invalid version")
        require_https(descriptor.get("url", ""), f"{pack_id}:url")
        dist = ROOT / "dist" / Path(urlparse(descriptor["url"]).path).name
        if not dist.is_file():
            fail(f"{pack_id}: missing dist archive {dist.name}")
        raw = dist.read_bytes()
        if len(raw) != descriptor.get("sizeBytes"):
            fail(f"{pack_id}: sizeBytes mismatch")
        if hashlib.sha256(raw).hexdigest() != descriptor.get("sha256"):
            fail(f"{pack_id}: sha256 mismatch")

        source_dir = ROOT / "packs" / pack_id
        source_manifest = read_json(source_dir / "manifest.json")
        source_cards = read_json(source_dir / "cards.json")
        if source_manifest != {"schemaVersion": 1, "id": pack_id, "version": version}:
            fail(f"{pack_id}: source manifest mismatch")

        with zipfile.ZipFile(dist) as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names or "cards.json" not in names:
                fail(f"{pack_id}: archive metadata missing")
            if any(name.startswith("/") or "\\" in name or ":" in name or ".." in Path(name).parts for name in names):
                fail(f"{pack_id}: unsafe archive path")
            zip_manifest = json.loads(archive.read("manifest.json"))
            zip_cards = json.loads(archive.read("cards.json"))
            if zip_manifest != source_manifest or zip_cards != source_cards:
                fail(f"{pack_id}: dist differs from source")
            card_ids = validate_cards(zip_cards, pack_id, names)

        overlap = all_card_ids & card_ids
        if overlap:
            fail(f"card id reused across packs: {sorted(overlap)[0]}")
        all_card_ids |= card_ids

    print(f"validated {len(pack_ids)} packs / {len(all_card_ids)} cards")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise
