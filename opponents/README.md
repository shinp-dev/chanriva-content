# Standard Opponent Packs

This catalog is independent of the card catalog at the repository root. The endpoint is
`https://raw.githubusercontent.com/shinp-dev/chanriva-content/main/opponents/index.json`.
Older app versions ignore it. The matching app change is on
`shinp-dev/othello`, branch `codex/data-driven-opponent-packs`.

## Add or update a pack

1. Create `opponents/packs/<stable-id>/manifest.json` and `assets/`. Start from the complete
   animal example; `schema/manifest.schema.json` defines the allowed fields and numeric bounds.
2. Set localized title/description/name maps (`en` required, `ja` optional), banner and Players.
3. Set Home section FEATURED (before card features) or CHALLENGES (after), style HERO or COMPACT,
   and order. Ties sort by Pack ID. No arbitrary UI, coordinates, HTML or code are accepted.
4. Define Player ID, display order, prerequisites, AI tuning, portrait/win/loss images and
   NORMAL/MILESTONE unlock celebration. Prerequisites are AND conditions within the same Pack
   and must form a DAG. Multiple roots/branches are allowed; order is not strength.
5. Run `pip install -r scripts/opponent-requirements.txt`.
6. Run `python scripts/opponents.py build`, `python scripts/opponents.py validate` and
   `python -m unittest discover -s scripts -p test_opponents.py`.
7. Commit source, generated ZIP and `opponents/index.json` together. Increment version on every
   change. Published ZIPs are immutable: do not overwrite or delete old versions to bypass validation.

The main workflow builds and validates both independent catalogs. Opponent archives have deterministic
timestamps and platform headers; existing ZIP bytes are retained when their uncompressed source is identical,
even across compression-library changes. Validation checks source/ZIP manifest and image equality. The app updates at Standard entry
and switches the active catalog only after all packs validate. Failed updates retain the last catalog.

## Semantics and safety

Identity is `(packId, playerId)`; progress ignores versions, names and display order. Never repurpose
published IDs. Removing/restoring IDs retains progress, and changing prerequisites does not relock
previously unlocked players. A human win without Undo counts as a clear. Animal IDs have a migration
from the former eight-level progress format.

Images use the opponent's perspective: portrait for introduction/selection, loseImage on a human win,
winImage on an opponent win or draw. MILESTONE is a generic unlock celebration. Text is plain text
with English fallback. Availability dates are ISO-8601 offsets, inclusive start/exclusive end; they use
the device clock and are not entitlement enforcement. Keep at least one permanent pack available.

NATURAL uses phase weights and score-loss limits to choose from Edax-ranked candidates. SERIOUS
always chooses the best candidate (the moves object is still validated). Both use bounded adaptive
think-time and tension profiles. Edax is limited to 1–4; script names, expressions, native settings,
book/eval paths and arbitrary policy classes cannot be supplied.

Index: 128 KiB / 32 packs. ZIP: 32 MiB compressed / 64 MiB expanded / 256 entries. Manifest: 1 MiB /
64 players. PNG/JPEG/WebP images: 8 MiB / 2048×2048 each; static images only. Only manifest.json and
referenced `assets/<lowercase-name>.<extension>` files are allowed. Traversal, duplicate entries,
source symlinks, unreferenced/missing images, dangling/cyclic prerequisites, unknown fields and
unsupported schemas are rejected. HTTPS URLs cannot carry user info, fragments or nonstandard ports;
the app does not follow redirects. ZIP byte size and SHA-256 are verified before installation.

## Baseline synchronization

The app ships `app/src/main/assets/opponents/index.json` and animal-v1.zip as its offline baseline.
The ZIP is byte-identical to this repository's generated ZIP. Copy a matching subset index and ZIPs
when updating the app baseline, then run the app's
`python tools/check_opponent_baseline.py --content-root <this-checkout>`.
Normal remote additions do not require app releases. Keep older version archives available.
Full domain/bootstrap/progress design: `othello/docs/opponent-packs.md`.
