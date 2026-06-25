import requests

from ..localization.localization import Localizer

class Loader:

    @staticmethod 
    def fetch(endpoint="/"):
        try:
            resp = requests.get(f"https://valorant-api.com/v1{endpoint}?language=all", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {}
        except (requests.RequestException, ValueError, KeyError):
            return {}

    @staticmethod 
    def load_all_content(client):
        content_data = {
            "agents": [],
            "maps": [],
            "modes": [],   
            "comp_tiers": [],
            "season": {},
            "queue_aliases": { #i'm so sad these have to be hardcoded but oh well :(
                "newmap": "New Map",
                "competitive": "Competitive",
                "unrated": "Unrated",
                "spikerush": "Spike Rush",
                "deathmatch": "Deathmatch",
                "ggteam": "Escalation",
                "onefa": "Replication",
                "custom": "Custom",
                "snowball": "Snowball Fight",
                "swiftplay": "Swiftplay",
                "hurm": "Team Deathmatch",
                "skirmish": "Skirmish",
                "skirmish2v2": "Skirmish",
                "onesite": "All Random One Site",
                "valaram": "All Random One Site",
                "2v2": "Skirmish",
                "2v2skirmish": "Skirmish",
                "aros": "All Random One Site",
                "allrandomonesite": "All Random One Site",
                # Modes added post v3.2.3
                "premier": "Premier",
                "hurm_bo3": "TDM Best-of-3",
                "smash": "Swiftplay",
                # Patch 13.00 (June 2026)
                "retake": "Retake",
                "": "Custom",
            },
            "team_aliases": {
                "TeamOne": "Defender",
                "TeamTwo": "Attacker",
                "TeamSpectate": "Observer",
                "TeamOneCoaches": "Defender Coach",
                "TeamTwoCoaches": "Attacker Coach",
            },
            "team_image_aliases": {
                "TeamOne": "team_defender",
                "TeamTwo": "team_attacker",
                "Red": "team_defender",
                "Blue": "team_attacker",
            },
            "modes_with_icons": ["ggteam","onefa","snowball","spikerush","unrated","deathmatch","swiftplay","hurm","premier","retake","skirmish","skirmish2v2","onesite","valaram","2v2","2v2skirmish","aros","allrandomonesite"]
        }
        try:
            all_content = client.fetch_content() or {}
        except Exception:
            # Riot content API (shared.*.pvp.net/content-service/v3/content) peut renvoyer 404
            all_content = {}
        agents = (Loader.fetch("/agents")).get("data") or []
        maps = (Loader.fetch("/maps")).get("data") or []
        modes = (Loader.fetch("/gamemodes")).get("data") or []
        ct_data = (Loader.fetch("/competitivetiers")).get("data") or []
        comp_tiers = ct_data[-1].get("tiers", []) if ct_data else []

        for season in (all_content.get("Seasons") or []):
            if not isinstance(season, dict):
                continue
            if season.get("IsActive") and season.get("Type") == "act":
                content_data["season"] = {
                    "competitive_uuid": season.get("ID", ""),
                    "season_uuid": season.get("ID", ""),
                    "display_name": season.get("Name", ""),
                }

        locale = getattr(Localizer, "locale", "en-US")
        fallback_locale = "en-US"

        for agent in agents:
            if not isinstance(agent, dict):
                continue
            names = agent.get("displayName") or {}
            content_data["agents"].append({
                "uuid": agent.get("uuid", ""),
                "display_name": names.get(fallback_locale, ""),
                "display_name_localized": names.get(locale, names.get(fallback_locale, "")),
                "internal_name": agent.get("developerName", ""),
            })

        for game_map in maps:
            if not isinstance(game_map, dict):
                continue
            names = game_map.get("displayName") or {}
            map_url = game_map.get("mapUrl") or ""
            content_data["maps"].append({
                "uuid": game_map.get("uuid", ""),
                "display_name": names.get(fallback_locale, ""),
                "display_name_localized": names.get(locale, names.get(fallback_locale, "")),
                "path": map_url,
                "internal_name": map_url.split("/")[-1] if map_url else "",
            })

        for mode in modes:
            if not isinstance(mode, dict):
                continue
            names = mode.get("displayName") or {}
            content_data["modes"].append({
                "uuid": mode.get("uuid", ""),
                "display_name": names.get(fallback_locale, ""),
                "display_name_localized": names.get(locale, names.get(fallback_locale, "")),
            })

        for tier in comp_tiers:
            if not isinstance(tier, dict):
                continue
            tier_names = tier.get("tierName") or {}
            content_data["comp_tiers"].append({
                "display_name": tier_names.get(fallback_locale, ""),
                "display_name_localized": tier_names.get(locale, tier_names.get(fallback_locale, "")),
                "id": tier.get("tier", 0),
            })

        return content_data
