import time

from ...presence_utilities import Utilities
from ..menu_presences.away import presence as away
from ....localization.localization import Localizer
from ....utilities.logging import Logger
from valclient.exceptions import PhaseError
debug = Logger.debug


class Game_Session:

    def __init__(self,rpc,client,data,match_id,content_data,config):
        self.rpc = rpc
        self.client = client
        self.config = config
        self.content_data = content_data
        self.match_id = match_id 
        self.puuid = self.client.puuid

        self.start_time = time.time()
        self.large_text = ""
        self.large_image = ""
        self.small_text = ""
        self.small_image = ""
        self.mode_name = ""

        self.large_pref = Localizer.get_config_value("presences","modes","all","large_image",0)
        self.small_pref = Localizer.get_config_value("presences","modes","all","small_image",0)
        self._logged_presence_keys = False
        self._last_logged_cid = None
        self.build_static_states()

    def fetch_current_display(self, presence):
        """Récupère agent, carte, mode actuels (pour modes où l’agent change en partie, ex. All Random One Site)."""
        try:
            coregame_data = self.client.coregame_fetch_match(self.match_id)
        except Exception:
            return None
        coregame_player_data = {}
        for player in coregame_data.get("Players", []):
            if player.get("Subject") == self.puuid:
                coregame_player_data = dict(player)
                break
        # Modes où l'agent change en partie (ex. All Random One Site) : essayer loadouts pour CharacterID à jour
        try:
            loadouts_data = self.client.coregame_fetch_match_loadouts(self.match_id)
            loadouts_list = loadouts_data.get("Loadouts", [])
            if not isinstance(loadouts_list, list):
                loadouts_list = list(loadouts_list.values()) if isinstance(loadouts_list, dict) else []
            for item in loadouts_list:
                loadout = item.get("Loadout", {}) if isinstance(item, dict) else {}
                subject = loadout.get("Subject") if isinstance(loadout, dict) else (getattr(item, "Loadout", None) and getattr(item.Loadout, "Subject", None))
                if subject == self.puuid:
                    cid = item.get("CharacterID") if isinstance(item, dict) else getattr(item, "CharacterID", None)
                    if cid:
                        if coregame_player_data:
                            coregame_player_data["CharacterID"] = cid
                        else:
                            coregame_player_data = {"CharacterID": cid, "Subject": self.puuid}
                    break
        except Exception:
            pass
        large_image, large_text = Utilities.get_content_preferences(
            self.client, self.large_pref, presence, coregame_player_data, coregame_data, self.content_data
        )
        small_image, small_text = Utilities.get_content_preferences(
            self.client, self.small_pref, presence, coregame_player_data, coregame_data, self.content_data
        )
        _, mode_name = Utilities.fetch_mode_data(presence, self.content_data)
        # All Random One Site : l’API ne met pas à jour l’agent par round → afficher le mode au lieu d’un agent figé
        queue_id = presence.get("queueId") or (presence.get("matchPresenceData") or {}).get("queueId") or (presence.get("partyPresenceData") or {}).get("queueId") or ""
        if (queue_id or "").lower() == "valaram":
            if self.large_pref == "agent":
                large_image, large_text = f"mode_{queue_id}", mode_name
            if self.small_pref == "agent":
                small_image, small_text = f"mode_{queue_id}", mode_name
        return large_image, large_text, small_image, small_text, mode_name

    def build_static_states(self):
        # Valeurs initiales (seront rafraîchies à chaque tour dans main_loop si besoin)
        presence = self.client.fetch_presence()
        try:
            coregame_data = self.client.coregame_fetch_match(self.match_id)
        except PhaseError:
            raise Exception
        coregame_player_data = {}
        for player in coregame_data["Players"]:
            if player["Subject"] == self.puuid:
                coregame_player_data = player

        self.large_image, self.large_text = Utilities.get_content_preferences(self.client,self.large_pref,presence,coregame_player_data,coregame_data,self.content_data)
        self.small_image, self.small_text = Utilities.get_content_preferences(self.client,self.small_pref,presence,coregame_player_data,coregame_data,self.content_data)
        _, self.mode_name = Utilities.fetch_mode_data(presence,self.content_data)
        queue_id = presence.get("queueId") or (presence.get("matchPresenceData") or {}).get("queueId") or (presence.get("partyPresenceData") or {}).get("queueId") or ""
        if (queue_id or "").lower() == "valaram":
            if self.large_pref == "agent":
                self.large_image, self.large_text = f"mode_{queue_id}", self.mode_name
            if self.small_pref == "agent":
                self.small_image, self.small_text = f"mode_{queue_id}", self.mode_name

    def main_loop(self):
        presence = self.client.fetch_presence()
        # Don't rely on sessionLoopState, check if we're still in game using coregame
        while presence is not None:
            try:
                # Check if we're still in game
                from valclient.exceptions import PhaseError
                coregame = self.client.coregame_fetch_player()
                if coregame is None:
                    # No longer in game, exit loop
                    break
            except PhaseError:
                # No longer in game, exit loop
                break
            except:
                # Error checking, continue anyway
                pass
            
            presence = self.client.fetch_presence()
            if presence is None:
                break
                
            is_afk = presence.get("isIdle", False)
            if is_afk:
                away(self.rpc,self.client,presence,self.content_data,self.config)
            else:
                # Log une fois les clés de la présence en partie (pour debug Escarmouche / modes)
                if not self._logged_presence_keys:
                    self._logged_presence_keys = True
                    keys = list(presence.keys()) if presence else []
                    pp = presence.get("partyPresenceData") or {}
                    mp = presence.get("matchPresenceData") or {}
                    pl = presence.get("playerPresenceData") or {}
                    char_vals = {k: presence.get(k) for k in keys if k and ("char" in k.lower() or "agent" in k.lower() or "character" in k.lower())}
                    char_vals["party_char_keys"] = [k for k in pp if k and ("char" in k.lower() or "agent" in k.lower())]
                    char_vals["match_char_keys"] = [k for k in mp if k and ("char" in k.lower() or "agent" in k.lower())]
                    char_vals["player_char_keys"] = [k for k in pl if k and ("char" in k.lower() or "agent" in k.lower())]
                    debug(f"[session] presence keys={keys} | char-related={char_vals}")
                # Rafraîchir agent/carte/mode à chaque tour
                current = self.fetch_current_display(presence)
                if current is not None:
                    large_image, large_text, small_image, small_text, mode_name = current
                    if large_text != self.large_text or small_text != self.small_text:
                        cid = (presence.get("CharacterID") or (presence.get("matchPresenceData") or {}).get("CharacterID") or "")
                        if cid != self._last_logged_cid:
                            self._last_logged_cid = cid
                            debug(f"[session] affichage changé -> large_text={large_text!r} small_text={small_text!r} cid={cid!r}")
                    self.large_image, self.large_text = large_image, large_text
                    self.small_image, self.small_text = small_image, small_text
                    self.mode_name = mode_name

                party_state, party_size = Utilities.build_party_state(presence)
                provisioning = presence.get("provisioningFlow", "") or ""
                if "replay" in provisioning.lower():
                    details = Localizer.get_localized_text("presences", "replay", "watching")
                else:
                    pp = presence.get("partyPresenceData") or {}
                    mp = presence.get("matchPresenceData") or {}
                    my_score = (
                        presence.get("partyOwnerMatchScoreAllyTeam")
                        or pp.get("partyOwnerMatchScoreAllyTeam")
                        or mp.get("partyOwnerMatchScoreAllyTeam")
                    )
                    other_score = (
                        presence.get("partyOwnerMatchScoreEnemyTeam")
                        or pp.get("partyOwnerMatchScoreEnemyTeam")
                        or mp.get("partyOwnerMatchScoreEnemyTeam")
                    )
                    if my_score is None:
                        my_score = 0
                    if other_score is None:
                        other_score = 0
                    details = f"{self.mode_name} • {my_score} - {other_score}"

                small_text_final = self.small_text if self.small_text and len(self.small_text) >= 2 else None
                small_image_final = self.small_image if small_text_final else None

                self.rpc.update(
                    state=party_state,
                    details=details,
                    start=self.start_time,
                    large_image=self.large_image,
                    large_text=self.large_text,
                    small_image=small_image_final,
                    small_text=small_text_final,
                    party_size=party_size,
                    party_id=presence.get("partyId", "") if presence.get("partyId") else None,
                    instance=True,
                )

            time.sleep(Localizer.get_config_value("presence_refresh_interval"))