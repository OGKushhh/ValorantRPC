# Fork Changelog — Best-of-Both

Based on **colinhartigan/valorant-rpc v3.2.3** + **krvntzkl/valorant-rpc v3.4.2**

---

## From krvntzkl/valorant-rpc (v3.3.x → v3.4.2) — Bug fixes & new features

### Critical bug fixes
- **`content_loader.py`**: Wrapped all `valorant-api.com` HTTP calls in try/except with timeout (was crashing on network errors). All dict accesses now use `.get()` to survive partial/malformed API responses.
- **`presence.py`**: Fixed `sessionLoopState` being missing/empty in Valorant 12.03+ — now detects game phase via coregame/pregame API calls as fallback. Fixed `color_print` crash in threaded context (replaced with `print()`).
- **`presence_utilities.py`**: Fixed `KeyError` on `partyAccessibility`, `partySize`, `maxPartySize`, `CharacterID` — all use `.get()` with defaults. `fetch_mode_data` now resolves `queueId` from nested `partyPresenceData`/`matchPresenceData` fields.
- **`menu.py`**: Rewrote party state detection — now correctly handles `IN_QUEUE`/`INQUEUE`/`SEARCHING` variants, custom game detection, and replay detection from multiple nested fields.
- **`menu_presences/away.py`, `default.py`, `queue.py`, `custom_setup.py`**: All fixed `KeyError` on `accountLevel`, `partyId`, `isIdle`, `matchMap` etc.
- **`ingame.py`**: Added try/except around session creation; shows basic presence immediately before full session loads.
- **`ingame_presences/session.py`**: Fixed session loop to use coregame API check instead of `sessionLoopState` (which is unreliable in v12+). Agent display now refreshes each tick (supports All Random One Site). Scores now fetched from nested presence fields.
- **`ingame_presences/range.py`**: Range loop now checks `provisioningFlow` to detect exit instead of `sessionLoopState`. Fixed bare `except` → `except Exception`.
- **`processes.py`**: Fixed crash when process disappears mid-iteration (`NoSuchProcess`, `AccessDenied`).
- **`startup.py`**: Fixed crash on exit when `systray` is None.
- **`logging.py`**: Log path now relative to working directory (avoids AppData path issues). Added noise suppression for `urllib3`/`asyncio`.
- **`presence_utilities.py`**: Fixed outdated rank api fetch call with LatestCompetitiveUpdate directly instead of the season UUID lookup.

### New features
- **Skirmish mode** (`skirmish`, `skirmish2v2`, `2v2`, `2v2skirmish`) — new 2v2 mode
- **All Random One Site** (`valaram`, `onesite`, `aros`, `allrandomonesite`) — agent changes per round, handled
- **Replay detection** — shows "Watching replay" instead of Menu when `sessionLoopState == REPLAY`
- **Account level caching** — fetched once and cached to avoid repeated API calls
- **`dependencies.py`** — new utility to check/install Python dependencies at runtime
- **`app_config.py`** — updated Discord client ID to `1354173612487213268` (v3.4.2)

---

## From this fork (OGKushhh) — Missing modes & locale completions

### New queue IDs added (all locales)
| Queue ID | Display Name |
|---|---|
| `premier` | Premier |
| `hurm_bo3` | TDM Best-of-3 |
| `smash` | Swiftplay (internal alias) |
| `skirmish` / `skirmish2v2` / `2v2` / `2v2skirmish` | Skirmish |
| `onesite` / `valaram` / `aros` / `allrandomonesite` | All Random One Site |

### Locale completions
All 14 locales (`ar-AE`, `de-DE`, `es-ES`, `es-MX`, `fr-FR`, `id-ID`, `it-IT`, `ja-JP`, `ko-KR`, `pl-PL`, `pt-BR`, `ru-RU`, `th-TH`, `tr-TR`, `vi-VN`, `zh-TW`) now include:
- `swiftplay`, `hurm` (were missing in most locales)
- `premier`, `hurm_bo3`, `smash`, `skirmish`, `valaram`, `onesite`
- `replay.watching` localized text

### Maps
All maps (Sunset, Abyss, Corrode, etc.) are fetched dynamically from `valorant-api.com` — no hardcoding needed.

## Known Issues
- some agents icons are missing/not updated
