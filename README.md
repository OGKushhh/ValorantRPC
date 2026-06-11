```
 _   _____   __   ____  ___  ___   _  ________                
| | / / _ | / /  / __ \/ _ \/ _ | / |/ /_  __/__________  ____
| |/ / __ |/ /__/ /_/ / , _/ __ |/    / / / /___/ __/ _ \/ __/
|___/_/ |_/____/\____/_/|_/_/ |_/_/|_/ /_/     /_/ / .__/\__/ 
                                                  /_/         
```
[![Discord][discord-shield]][discord-url]
[![Stars][stars-shield]][stars-url]
[![Releases][releases-shield]][releases-url]
[![Language][language-shield]][language-url]
[![License][license-shield]][license-url]

  <ol>  
    <li><a href="#about">About</a></li>
    <li><a href="#whats-new">What's New</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#support">Support</a></li>
    <li><a href="#disclaimer">Disclaimer</a></li>
  </ol>


## About

Valorant RPC (Rich Presence) allows you to show in-game details such as the current score in your Discord Profile! Additional features include showing current map, agent, idle status, etc.

This is a community fork of [colinhartigan/valorant-rpc](https://github.com/colinhartigan/valorant-rpc) (archived July 2024), merging fixes and features from [krvntzkl/valorant-rpc](https://github.com/krvntzkl/valorant-rpc) and additional improvements to keep the project working with the current Valorant client.

<a>
  <img src="assets/Demo1.png" alt="Demo" width="205" height="112">
  <img src="assets/Demo2.png" alt="Demo" width="205" height="112">
</a>


## What's New

### Bug Fixes
- Fixed rank not showing — now uses `LatestCompetitiveUpdate` directly instead of the broken season UUID lookup
- Fixed game phase detection for Valorant 12.03+ — falls back to coregame/pregame API when `sessionLoopState` is missing
- Fixed crashes on missing presence fields (`partyAccessibility`, `partySize`, `CharacterID`, `accountLevel`, etc.)
- Fixed queue detection to handle `IN_QUEUE`, `INQUEUE`, `SEARCHING` and other API variants
- Fixed custom game and replay detection from nested presence fields
- Fixed agent display refreshing each tick (supports All Random One Site mode)
- Fixed score fetching from nested presence fields
- Fixed range loop exit detection using `provisioningFlow` instead of `sessionLoopState`
- Fixed crash when Valorant process disappears mid-iteration
- Fixed `color_print` crash in threaded context

### New Modes Supported
| Mode | Queue ID(s) |
|---|---|
| Skirmish | `skirmish`, `skirmish2v2`, `2v2`, `2v2skirmish` |
| All Random One Site | `valaram`, `onesite`, `aros`, `allrandomonesite` |
| Premier | `premier` |
| TDM Best-of-3 | `hurm_bo3` |
| Replay | shows "Watching replay" instead of Menu |

### Other Improvements
- All maps (Sunset, Abyss, Corrode, etc.) fetched dynamically — no hardcoding needed
- All 16 locales now include missing mode names (`swiftplay`, `hurm`, `premier`, etc.)
- Account level cached to avoid repeated API calls


## Installation

- Download the latest release and run it.


## Usage

- Run the program instead of launching VALORANT
    - If VALORANT is not running, the program will launch it for you
- If VALORANT is already running, launch the program and the presence will start


## Support

Either make an issue or:

[![Discord Banner 2][discord-banner]][discord-url]


## Disclaimer

This project is not affiliated with Riot Games or any of its employees and therefore does not reflect the views of said parties.

Riot Games does not endorse or sponsor this project. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.



[discord-shield]: https://img.shields.io/discord/860288779558715402?color=7289da&label=Support&logo=discord&logoColor=7289da&style=for-the-badge
[discord-url]: https://discord.gg/uGuswsZwAT
[discord-banner]: https://discordapp.com/api/guilds/860288779558715402/widget.png?style=banner2
[license-shield]: https://img.shields.io/github/license/colinhartigan/valorant-rpc?style=for-the-badge
[license-url]: https://github.com/colinhartigan/valorant-rpc/blob/v3/LICENSE.txt

[stars-shield]: https://img.shields.io/github/stars/OGKushhh/ValorantRPC?logo=github&style=for-the-badge
[stars-url]: https://github.com/OGKushhh/ValorantRPC/stargazers

[releases-shield]: https://img.shields.io/github/downloads/OGKushhh/ValorantRPC/total?style=for-the-badge
[releases-url]: https://github.com/OGKushhh/ValorantRPC/releases

[language-shield]: https://img.shields.io/github/languages/top/colinhartigan/valorant-rpc?logo=python&logoColor=yellow&style=for-the-badge
[language-url]: https://www.python.org/
