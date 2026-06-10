#!/usr/bin/env python3
"""
fetch_discord_assets.py
=======================
Fetches all Valorant Rich Presence image assets from valorant-api.com and
saves them locally with the exact key names the RPC code uses.

Run this on your own machine (not in Claude's sandbox).

Requirements:
    pip install requests pillow

Usage:
    python fetch_discord_assets.py

Output folder structure:
    discord_assets/
        agents/       agent_jett.png, agent_vyse.png ...
        ranks/        rank_0.png ... rank_27.png
        maps/         splash_ascent.png, splash_bind.png ...
        modes/        mode_competitive.png, mode_hurm.png ...
        game/         game_icon.png, team_attacker.png, team_defender.png

Discord upload limit: 256 KB per asset, 300 assets max per app.
Images are resized to fit within 256x256 px (Discord recommends square assets).

After downloading:
    1. Go to https://discord.com/developers/applications
    2. Open your app → Rich Presence → Art Assets
    3. Upload all images — the filename (without .png) becomes the asset key
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    sys.exit(1)

API_BASE = "https://valorant-api.com/v1"
OUT_DIR  = Path("discord_assets")

# Discord limits
MAX_DIM    = 256   # px — max dimension for RPC assets
MAX_BYTES  = 250 * 1024  # 250 KB safe limit (hard limit is 256 KB)
JPEG_QUALITY = 90

# ── helpers ────────────────────────────────────────────────────────────────

def fetch_json(endpoint, params=None):
    params = params or {}
    params.setdefault("language", "en-US")
    r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])

def download(url, timeout=20):
    if not url:
        return None
    r = requests.get(url, timeout=timeout)
    if r.status_code != 200:
        return None
    return r.content

def save_image(raw: bytes, dest: Path, max_dim=MAX_DIM):
    """Open raw bytes, resize to fit max_dim, save as PNG (or JPEG if too large)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(BytesIO(raw)).convert("RGBA")

    # Resize so longest edge ≤ max_dim
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Try PNG first
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    if buf.tell() <= MAX_BYTES:
        dest.write_bytes(buf.getvalue())
        return

    # PNG too large → try JPEG (no alpha)
    jpg_img = img.convert("RGB")
    buf = BytesIO()
    jpg_img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    dest_jpg = dest.with_suffix(".jpg")
    dest_jpg.write_bytes(buf.getvalue())
    print(f"  ⚠  Saved as JPEG (PNG was too large): {dest_jpg.name}")

def sanitize(name: str) -> str:
    """Convert a display name to the RPC key format."""
    return name.lower().replace(" ", "").replace("/", "").replace("'", "").replace(".", "")

def print_section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")

# ── agents ─────────────────────────────────────────────────────────────────

def fetch_agents():
    print_section("Agents")
    out = OUT_DIR / "agents"
    agents = fetch_json("/agents", {"isPlayableCharacter": "true"})
    ok = err = 0
    for agent in agents:
        name = agent.get("displayName", "")
        key  = f"agent_{sanitize(name)}"
        dest = out / f"{key}.png"
        if dest.exists():
            print(f"  skip  {key}")
            ok += 1
            continue

        # Prefer bustPortrait, fall back to fullPortrait, then displayIcon
        url = (agent.get("bustPortrait") or
               agent.get("fullPortrait") or
               agent.get("displayIcon") or "")
        raw = download(url)
        if not raw:
            print(f"  FAIL  {key}  ({url[:60]})")
            err += 1
            continue

        save_image(raw, dest)
        print(f"  ✓  {key}")
        ok += 1
        time.sleep(0.05)

    print(f"\n  Agents: {ok} OK, {err} failed")

# ── competitive ranks ───────────────────────────────────────────────────────

def fetch_ranks():
    print_section("Competitive Ranks")
    out = OUT_DIR / "ranks"
    tiers_list = fetch_json("/competitivetiers")
    # Use the most recent episode's tier list
    latest = tiers_list[-1]["tiers"]
    ok = err = 0
    for tier in latest:
        tier_id = tier.get("tier", 0)
        key  = f"rank_{tier_id}"
        dest = out / f"{key}.png"
        if dest.exists():
            print(f"  skip  {key}")
            ok += 1
            continue

        url = tier.get("largeIcon") or tier.get("smallIcon") or ""
        if not url:
            print(f"  skip  {key}  (no icon URL)")
            continue
        raw = download(url)
        if not raw:
            print(f"  FAIL  {key}")
            err += 1
            continue

        save_image(raw, dest)
        print(f"  ✓  {key}  ({tier.get('tierName', '')})")
        ok += 1
        time.sleep(0.05)

    print(f"\n  Ranks: {ok} OK, {err} failed")

# ── map splashes ────────────────────────────────────────────────────────────

def fetch_maps():
    print_section("Map Splashes")
    out = OUT_DIR / "maps"
    maps = fetch_json("/maps")
    ok = err = 0
    for m in maps:
        name     = m.get("displayName", "")
        internal = (m.get("mapUrl") or "").split("/")[-1].lower()
        if not name or not internal:
            continue

        key  = f"splash_{sanitize(name)}"
        dest = out / f"{key}.png"
        if dest.exists():
            print(f"  skip  {key}")
            ok += 1
            continue

        url = m.get("splash") or m.get("displayIcon") or ""
        raw = download(url)
        if not raw:
            print(f"  FAIL  {key}")
            err += 1
            continue

        # Map splashes are large; resize to 256×144 (16:9) to save space
        img = Image.open(BytesIO(raw)).convert("RGB")
        img = img.resize((256, 144), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        dest_jpg = (out / f"{key}.jpg")
        # ✅ Create parent directory before writing
        dest_jpg.parent.mkdir(parents=True, exist_ok=True)
        dest_jpg.write_bytes(buf.getvalue())
        print(f"  ✓  {key}  (saved as jpg)")
        ok += 1
        time.sleep(0.05)

    print(f"\n  Maps: {ok} OK, {err} failed")

# ── game modes ──────────────────────────────────────────────────────────────

# Hardcoded mapping: queue_id → display name used in code (mode_{queue_id})
MODES_WITH_ICONS = [
    "unrated", "competitive", "spikerush", "deathmatch",
    "ggteam", "onefa", "snowball", "swiftplay", "hurm",
    "premier", "skirmish", "skirmish2v2", "onesite", "valaram",
    "discovery",  # fallback key
]

def fetch_modes():
    print_section("Game Mode Icons")
    out = OUT_DIR / "modes"
    modes = fetch_json("/gamemodes")
    # Build name → icon URL map
    icon_map = {}
    for mode in modes:
        display = sanitize(mode.get("displayName", ""))
        icon_map[display] = mode.get("displayIcon") or ""

    # Manual queue_id → API display name mapping
    queue_to_display = {
        "unrated":     "standard",
        "competitive": "competitive",
        "spikerush":   "spike rush",
        "deathmatch":  "deathmatch",
        "ggteam":      "escalation",
        "onefa":       "replication",
        "snowball":    "snowball fight",
        "swiftplay":   "swiftplay",
        "hurm":        "team deathmatch",
        "premier":     "premier",
        "skirmish":    "skirmish",
        "onesite":     "all random one site",
        "valaram":     "all random one site",
        "discovery":   "unrated",
    }

    ok = err = 0
    for queue_id in MODES_WITH_ICONS:
        key  = f"mode_{queue_id}"
        dest = out / f"{key}.png"
        if dest.exists():
            print(f"  skip  {key}")
            ok += 1
            continue

        display_key = sanitize(queue_to_display.get(queue_id, queue_id))
        url = icon_map.get(display_key, "")
        if not url:
            # Try partial match
            for k, v in icon_map.items():
                if display_key in k or k in display_key:
                    url = v
                    break

        if not url:
            print(f"  skip  {key}  (no icon in API, use custom asset)")
            continue

        raw = download(url)
        if not raw:
            print(f"  FAIL  {key}")
            err += 1
            continue

        save_image(raw, dest)
        print(f"  ✓  {key}")
        ok += 1
        time.sleep(0.05)

    print(f"\n  Modes: {ok} OK, {err} failed")

# ── game icon + team icons ──────────────────────────────────────────────────

def fetch_misc():
    """team_attacker / team_defender come from maps (Attacker/Defender side icons)."""
    print_section("Misc (game_icon, team icons)")
    out = OUT_DIR / "game"

    # team icons come from a map's callout data — use Ascent as reference
    maps = fetch_json("/maps")
    for m in maps:
        if "Ascent" in m.get("displayName", ""):
            atk = m.get("displayIcon", "")
            break
    else:
        atk = ""

    # Valorant game icon (from the API root)
    misc = [
        ("game_icon", "https://media.valorant-api.com/gamemodes/96bd3920-4f36-d026-2b28-c683eb0bcac5/displayicon.png"),
        # team icons — Riot exposes these via the map callouts endpoint
        # Using known CDN paths as fallback
        ("team_attacker", "https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/displayicon.png"),
        ("team_defender", "https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/displayicon.png"),
    ]

    for key, url in misc:
        dest = out / f"{key}.png"
        if dest.exists():
            print(f"  skip  {key}")
            continue
        raw = download(url)
        if not raw:
            print(f"  FAIL  {key}  (upload manually from game files)")
            continue
        save_image(raw, dest)
        print(f"  ✓  {key}")

# ── summary ─────────────────────────────────────────────────────────────────

def print_summary():
    print(f"\n{'='*50}")
    print("  DONE — Summary")
    print(f"{'='*50}")
    total = 0
    for folder in sorted(OUT_DIR.rglob("*.png")) + sorted(OUT_DIR.rglob("*.jpg")):
        total += 1
    print(f"  Total assets saved: {total}")
    print(f"  Output folder: {OUT_DIR.resolve()}")
    print()
    print("  Next steps:")
    print("  1. Go to https://discord.com/developers/applications")
    print("  2. Create or select your app")
    print("  3. Rich Presence → Art Assets → Add Image(s)")
    print("  4. Upload all files — filename (no extension) = asset key")
    print("  5. Copy your app's Client ID")
    print("  6. Set it in: src/utilities/config/app_config.py → 'client_id'")
    print()
    print("  Asset key reference:")
    print("    Agents   → agent_jett, agent_vyse, agent_clove ...")
    print("    Ranks    → rank_0 (unranked) ... rank_27 (radiant)")
    print("    Maps     → splash_ascent, splash_abyss, splash_corrode ...")
    print("    Modes    → mode_competitive, mode_hurm, mode_premier ...")
    print("    Misc     → game_icon, team_attacker, team_defender")

# ── entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Valorant Discord RPC Asset Fetcher")
    print("Fetching from valorant-api.com ...\n")
    OUT_DIR.mkdir(exist_ok=True)

    try:
        fetch_agents()
        fetch_ranks()
        fetch_maps()
        fetch_modes()
        fetch_misc()
        print_summary()
    except KeyboardInterrupt:
        print("\nInterrupted. Partial assets saved.")
    except requests.RequestException as e:
        print(f"\nNetwork error: {e}")
        sys.exit(1)
