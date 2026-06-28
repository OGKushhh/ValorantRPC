<p align="center">
  <img width="3891" height="494" alt="banner" src="https://github.com/user-attachments/assets/b3bf96a5-212e-460d-b487-d36f73be74b8" />
</p>

<p align="center">
  <strong>Show your live match details — score, map, agent, and more — right on your Discord profile.</strong>
</p>

<p align="center">
  <a href="#-about">About</a> •
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-support">Support</a> •
  <a href="#-disclaimer">Disclaimer</a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/downloads/OGKushhh/ValorantRPC/total?label=downloads&color=brightgreen" alt="Total Downloads">
  <img src="https://img.shields.io/github/downloads/OGKushhh/ValorantRPC/latest/total?label=downloads%40latest&color=brightgreen" alt="Latest Release Downloads">
  <img src="https://img.shields.io/github/languages/top/colinhartigan/valorant-rpc?logo=python&logoColor=yellow" alt="Language">
  <img src="https://img.shields.io/github/license/colinhartigan/valorant-rpc?color=green" alt="License">
</p>

---

## 🔥 About

Valorant RPC (Rich Presence) shows your live match details — score, map, agent, idle status, and more — right on your Discord profile.

This is a community fork of [colinhartigan/valorant-rpc](https://github.com/colinhartigan/valorant-rpc) (archived July 2024), merging fixes and features from [krvntzkl/valorant-rpc](https://github.com/krvntzkl/valorant-rpc) plus additional improvements to keep the project working with the current Valorant client.

<p align="center">
  <img src="assets/Demo1.png" alt="Demo" width="205" height="112">
  <img src="assets/Demo2.png" alt="Demo" width="205" height="112">
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🏆 **Live Rank & Score** | Pulls your current competitive rank directly from `LatestCompetitiveUpdate`. |
| 🗺️ **Map & Agent Display** | All maps (Sunset, Abyss, Corrode, etc.) are fetched dynamically, so new maps work without an update. |
| 🎯 **Smart Game-Phase Detection** | Falls back to the coregame/pregame API when `sessionLoopState` is missing, keeping status accurate across client versions. |
| 🕒 **Idle & Menu Status** | Shows menu/idle state whenever you're not in a match. |
| 🎬 **Replay Detection** | Displays "Watching replay" instead of Menu when reviewing a match. |
| 🌐 **Full Locale Support** | All 26 locales include the newer mode names (`swiftplay`, `hurm`, `premier`, etc.). |
| ⚡ **Lightweight** | Account level is cached locally to avoid repeated API calls. |

### Supported Modes

| Mode | Queue ID(s) |
|---|---|
| Skirmish | `skirmish`, `skirmish2v2`, `2v2`, `2v2skirmish` |
| All Random One Site | `valaram`, `onesite`, `aros`, `allrandomonesite` |
| Premier | `premier` |
| TDM Best-of-3 | `hurm_bo3` |
| Retake | `fortcollins` |
| Replay | Shows "Watching replay" instead of Menu |

---

## 🚀 Installation

1. Download the latest release from the [Releases](https://github.com/OGKushhh/ValorantRPC/releases) page.
2. Run it.

> ⚠️ **Antivirus flag?** Some AV engines may flag the exe as a false positive due to UPX compression — this is a well-documented pattern with PyInstaller-built executables in general, not a sign of anything malicious. Every release is scanned with [VirusTotal](https://www.virustotal.com/) and the results are linked in the release notes if you want to check for yourself.

---

## 🕹️ Usage

- Run the program instead of launching VALORANT.
  - If VALORANT isn't running, the program will launch it for you.
- If VALORANT is already running, just launch the program — your presence starts automatically.

---

## 💬 Support

Found a bug or have a feature request? Open an [issue](https://github.com/OGKushhh/ValorantRPC/issues).

---

## ⚠️ Disclaimer

This project is not affiliated with Riot Games or any of its employees and therefore does not reflect the views of said parties.

Riot Games does not endorse or sponsor this project. Riot Games, and all associated properties, are trademarks or registered trademarks of Riot Games, Inc.
