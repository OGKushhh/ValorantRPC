import iso8601
from ..utilities.logging import Logger 
from ..localization.localization import Localizer
debug = Logger.debug

# Cache global pour le niveau du compte (évite les appels API répétés)
_account_level_cache = None

class Utilities:

    @staticmethod 
    def build_party_state(data):
        party_state = Localizer.get_localized_text("presences","party_states","solo")     
        party_accessibility = data.get("partyAccessibility", "CLOSED")  # Default to CLOSED if not present
        party_size_val = data.get("partySize", 1)
        
        if party_size_val > 1:
            party_state = Localizer.get_localized_text("presences","party_states","in_party")   
        elif party_accessibility == "OPEN":
            party_state = Localizer.get_localized_text("presences","party_states","open")

        max_party_size = data.get("maxPartySize", 5)
        party_size = [party_size_val, max_party_size] if party_size_val > 1 or party_accessibility == "OPEN" else None
        if party_size is not None:
            if party_size[0] == 0: 
                party_size[0] = 1
            if party_size[1] < 1:
                party_size[1] = 1
        return party_state, party_size 

    @staticmethod 
    def iso8601_to_epoch(time):
        if time == "0001.01.01-00.00.00":
            return None
        split = time.split("-")
        split[0] = split[0].replace(".","-")
        split[1] = split[1].replace(".",":")
        split = "T".join(i for i in split)
        split = iso8601.parse_date(split).timestamp() #converts iso8601 to epoch
        return split

    @staticmethod 
    def fetch_rank_data(client,content_data):
        try:
            mmr = client.fetch_mmr()["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"][content_data["season"]["season_uuid"]]
        except:
            return "rank_0","Rank not found"
        rank_data = {}
        for tier in content_data["comp_tiers"]:
            if tier["id"] == mmr["CompetitiveTier"]:
                rank_data = tier
        rank_image = f"rank_{rank_data['id']}"
        rank_text = f"{rank_data['display_name_localized']} - {mmr['RankedRating']}{Localizer.get_localized_text('presences','leveling','ranked_rating')}" + (f" // #{mmr['LeaderboardRank']}" if mmr['LeaderboardRank'] != 0 else "") 

        return rank_image, rank_text
        
    @staticmethod 
    def fetch_map_data(coregame_data,content_data):
        map_id = coregame_data.get("MapID", "") if coregame_data else ""
        if not map_id:
            return "", ""
        for gmap in content_data["maps"]:
            if gmap["path"] == map_id:
                return gmap["display_name"], gmap["display_name_localized"]
        return "", ""
 
    @staticmethod 
    def fetch_agent_data(uuid,content_data):
        for agent in content_data["agents"]:
            if agent["uuid"] == uuid:
                agent_image = f"agent_{agent['display_name'].lower().replace('/','')}"
                agent_name = agent['display_name_localized']
                return agent_image, agent_name
        return "rank_0","?"

    @staticmethod
    def fetch_mode_data(data, content_data):
        # queueId peut être à la racine ou dans partyPresenceData / matchPresenceData
        pp = data.get("partyPresenceData") or {}
        mp = data.get("matchPresenceData") or {}
        queue_id = data.get("queueId") or pp.get("queueId") or mp.get("queueId") or ""
        queue_id_lower = (queue_id or "").lower().strip()
        aliases = content_data["queue_aliases"]
        icons = content_data["modes_with_icons"]
        mode_name = aliases.get(queue_id) or aliases.get(queue_id_lower)
        if mode_name is None:
            mode_name = "Custom"
            # Log pour identifier le queueId réel envoyé par l’API (Skirmish, All Random One Site, etc.)
            debug(f"[mode] Custom fallback -> queueId root={data.get('queueId')!r} party={pp.get('queueId')!r} match={mp.get('queueId')!r} | provisioningFlow={data.get('provisioningFlow')!r} | party keys={list(pp.keys())} match keys={list(mp.keys())}")
        image_key = queue_id if queue_id in icons else (queue_id_lower if queue_id_lower in icons else "discovery")
        image = f"mode_{image_key}"
        mode_name = Utilities.localize_content_name(mode_name, "presences", "modes", queue_id or queue_id_lower)
        return image, mode_name

    @staticmethod 
    def get_content_preferences(client,pref,presence,player_data,coregame_data,content_data):
        if pref == Localizer.get_localized_text("config", "rank"):
            return Utilities.fetch_rank_data(client,content_data)
        if pref == Localizer.get_localized_text("config", "map"): 
            gmap = Utilities.fetch_map_data(coregame_data,content_data)
            return f"splash_{gmap[0].lower()}", gmap[1]
        if pref == Localizer.get_localized_text("config", "agent"):
            # CharacterID peut venir du coregame (player_data) ou de la présence (mise à jour en partie, ex. All Random One Site)
            char_id = None
            if player_data:
                char_id = player_data.get("CharacterID") or player_data.get("characterId")
            if not char_id and presence:
                pp = presence.get("partyPresenceData") or {}
                mp = presence.get("matchPresenceData") or {}
                pl = presence.get("playerPresenceData") or {}
                pr = presence.get("premierPresenceData") or {}
                char_id = (
                    presence.get("CharacterID") or presence.get("characterId")
                    or pp.get("CharacterID") or pp.get("characterId")
                    or mp.get("CharacterID") or mp.get("characterId")
                    or pl.get("CharacterID") or pl.get("characterId")
                    or pr.get("CharacterID") or pr.get("characterId")
                )
            if char_id:
                return Utilities.fetch_agent_data(char_id, content_data)
            return "rank_0", "?"

    @staticmethod
    def localize_content_name(default,*keys):
        localized = Localizer.get_localized_text(*keys)
        if localized is not None:
            return localized 
        return default

    @staticmethod 
    def get_join_state(client,config,presence=None):
        '''
        if presence is None:
            presence = client.fetch_presence()
        base_api_url = "https://colinhartigan.github.io/valorant-rpc?redir={redirect}&type={req_type}"
        base_api_url = f"{base_api_url}&region={client.region}&playername={client.player_name}&playertag={client.player_tag}" # add on static values (region/playername)
        party_size = presence.get("partySize", 1)
        max_party_size = presence.get("maxPartySize", 5)
        party_accessibility = presence.get("partyAccessibility", "CLOSED")
        if int(party_size) < int(max_party_size):
            if party_accessibility == "OPEN" and config["presences"]["menu"]["show_join_button_with_open_party"]:
                debug(f"join link: " + base_api_url.format(redirect=f"/valorant/join/{presence['partyId']}"))
                return [{"label":"Join","url":base_api_url.format(redirect=f"/valorant/join/{presence['partyId']}",req_type="join")}]
            
            if party_accessibility == "CLOSED" and config["presences"]["menu"]["allow_join_requests"]:
                return [{"label":"Request to Join","url":base_api_url.format(redirect=f"/valorant/request/{presence['partyId']}/{client.puuid}",req_type="request")}]
        '''

        return None

    @staticmethod
    def fetch_account_level(client, data=None):
        """
        Récupère le niveau du compte.
        Essaie d'abord depuis les données de présence, sinon via l'API du client.
        Utilise un cache pour éviter les appels API répétés.
        """
        global _account_level_cache
        
        # Si on a un cache valide, l'utiliser
        if _account_level_cache is not None and _account_level_cache > 0:
            return _account_level_cache
        
        # Essayer depuis les données de présence
        if data and "accountLevel" in data:
            level = data.get("accountLevel", 0)
            if level and level > 0:
                _account_level_cache = level
                return level
        
        # Essayer via fetch_account_xp (méthode la plus fiable)
        try:
            if hasattr(client, 'fetch_account_xp'):
                account_xp = client.fetch_account_xp()
                if account_xp:
                    # Le niveau peut être dans Progress.Level
                    if "Progress" in account_xp and isinstance(account_xp["Progress"], dict):
                        if "Level" in account_xp["Progress"]:
                            level = account_xp["Progress"]["Level"]
                            if level and level > 0:
                                _account_level_cache = level
                                return level
                    # Vérifier aussi au niveau racine
                    if "Level" in account_xp:
                        level = account_xp["Level"]
                        if level and level > 0:
                            _account_level_cache = level
                            return level
                    if "accountLevel" in account_xp:
                        level = account_xp["accountLevel"]
                        if level and level > 0:
                            _account_level_cache = level
                            return level
                    # Vérifier dans d'autres structures possibles
                    for key in ["AccountLevel", "account_level", "PlayerLevel", "playerLevel"]:
                        if key in account_xp:
                            level = account_xp[key]
                            if level and level > 0:
                                _account_level_cache = level
                                return level
        except Exception as e:
            debug(f"Erreur lors de la récupération du niveau via fetch_account_xp: {e}")
            pass
        
        # Essayer via fetch_player_loadout
        try:
            player_loadout = client.fetch_player_loadout()
            if player_loadout:
                # Vérifier différentes clés possibles pour le niveau
                if "AccountLevel" in player_loadout:
                    level = player_loadout["AccountLevel"]
                    if level and level > 0:
                        _account_level_cache = level
                        return level
                if "accountLevel" in player_loadout:
                    level = player_loadout["accountLevel"]
                    if level and level > 0:
                        _account_level_cache = level
                        return level
                # Certaines versions peuvent avoir le niveau dans Identity
                if "Identity" in player_loadout and isinstance(player_loadout["Identity"], dict):
                    if "AccountLevel" in player_loadout["Identity"]:
                        level = player_loadout["Identity"]["AccountLevel"]
                        if level and level > 0:
                            _account_level_cache = level
                            return level
        except Exception as e:
            debug(f"Erreur lors de la récupération du niveau via fetch_player_loadout: {e}")
            pass
        
        return 0  # Valeur par défaut si rien ne fonctionne
