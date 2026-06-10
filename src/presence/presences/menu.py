import os
import json
from .menu_presences import (default,queue,custom_setup)
from ..presence_utilities import Utilities
from ...localization.localization import Localizer

def _write_presence_debug(data):
    """Écrit les champs présence dans un fichier pour diagnostiquer la détection « Dans la file »."""
    if not data:
        return
    try:
        # Écrire à la racine du projet (dossier d’où tu lances le programme)
        debug_path = os.path.join(os.path.abspath("."), "presence_debug.json")
        payload = dict(data)
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
    except Exception:
        pass

def presence(rpc,client=None,data=None,content_data=None,config=None):
    state_types = {
        "DEFAULT": default,
        "MATCHMAKING": queue,
        "IN_QUEUE": queue,
        "InQueue": queue,
        "INQUEUE": queue,
        "SEARCHING": queue,
        "CUSTOM_GAME_SETUP": custom_setup,
    }
    
    # Vérifier d'abord si on est dans un match personnalisé (salon)
    # Indicateurs possibles forts :
    # - partyState == "CUSTOM_GAME_SETUP"
    # - queueId == "custom"
    # - provisioningFlow == "CustomGame"
    is_custom_game = False
    if data:
        pp = data.get("partyPresenceData") or {}
        mp = data.get("matchPresenceData") or {}
        party_state_root = data.get("partyState")
        party_state_pp = pp.get("partyState")
        queue_id = (data.get("queueId") or pp.get("queueId") or mp.get("queueId") or "").lower()
        prov_root = str(data.get("provisioningFlow") or "").upper()
        prov_match = str(mp.get("provisioningFlow") or "").upper()

        if party_state_root == "CUSTOM_GAME_SETUP" or party_state_pp == "CUSTOM_GAME_SETUP":
            is_custom_game = True
        elif queue_id == "custom":
            is_custom_game = True
        elif "CUSTOMGAME" in prov_root or "CUSTOMGAME" in prov_match:
            is_custom_game = True
    
    if is_custom_game:
        custom_setup.presence(rpc,client=client,data=data,content_data=content_data,config=config)
        return

    # L’API peut mettre les champs à la racine ou dans partyPresenceData / matchPresenceData
    party_data = data.get("partyPresenceData") or {} if data else {}
    match_data = data.get("matchPresenceData") or {} if data else {}
    party_state = data.get("partyState") or party_data.get("partyState", "") if data else ""
    queue_entry_time = data.get("queueEntryTime") or party_data.get("queueEntryTime", "0001.01.01-00.00.00") if data else "0001.01.01-00.00.00"
    matchmaking_state = data.get("matchmakingState") or party_data.get("matchmakingState") or match_data.get("matchmakingState") or ""
    is_matchmaking = data.get("isMatchmakingGame", False) or party_data.get("isMatchmakingGame", False) if data else False
    
    # Détection replay : sessionLoopState == "REPLAY" dans matchPresenceData ou partyPresenceData
    session_loop_state = data.get("sessionLoopState") or match_data.get("sessionLoopState") or party_data.get("partyOwnerSessionLoopState") or ""
    if session_loop_state and "REPLAY" in str(session_loop_state).upper():
        # Afficher "Watching replay" au lieu de "Menu"
        if not data:
            return
        party_state, party_size = Utilities.build_party_state(data)
        account_level = Utilities.fetch_account_level(client, data)
        party_id = data.get("partyId", "") or party_data.get("partyId", "")
        rpc.update(
            state=party_state,
            details=Localizer.get_localized_text("presences", "replay", "watching"),
            large_image="game_icon",
            large_text=f"{Localizer.get_localized_text('presences','leveling','level')} {account_level}",
            party_size=party_size,
            party_id=party_id if party_id else None,
        )
        return

    # Check if partyState exists and is valid
    if data and party_state and party_state in state_types.keys():
        state_types[party_state].presence(rpc,client=client,data=data,content_data=content_data,config=config)
    elif data and (data.get('queueId') or party_data.get('queueId') or match_data.get('queueId')):
        # If we have a queueId, check multiple indicators to determine if we're in queue
        
        # Check if we're in queue using multiple indicators:
        # - queueEntryTime is valid and not default
        # - matchmakingState indicates we're matchmaking (plusieurs valeurs possibles selon les versions API)
        # - isMatchmakingGame flag is True
        matchmaking_values = [
            'MATCHMAKING', 'QUEUED', 'SEARCHING', 'IN_QUEUE', 'InQueue', 'INQUEUE',
            'Searching', 'InProgress', 'in_queue', 'matchmaking'
        ]
        is_in_queue = (
            (queue_entry_time and queue_entry_time != "0001.01.01-00.00.00") or
            (matchmaking_state and matchmaking_state.upper() in [v.upper() for v in matchmaking_values]) or
            is_matchmaking
        )
        
        if is_in_queue:
            # We're in queue
            queue.presence(rpc,client=client,data=data,content_data=content_data,config=config)
        else:
            # We're in menu but not in queue
            default.presence(rpc,client=client,data=data,content_data=content_data,config=config)
    elif data:
        # Fallback to default menu presence
        default.presence(rpc,client=client,data=data,content_data=content_data,config=config)