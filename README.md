# RUNE modpack - mod lists (5 categories, server vs client)

Text deliverables for audit. The two source documents that were handed over are
kept byte-for-byte in [`source/`](source/); everything else is derived from them
and split into **five categories**, each one sorted into **BOTH / SERVER / CLIENT**
sections so a reviewer can see at a glance what has to be installed on the
dedicated server and what belongs to the client instance only.

Target: **Minecraft 1.20.1, Forge 47.4.10**

```
README.md                            this file
SUMMARY.txt                          counts per category, per side, per pack
AUDIT-NOTES.txt                      every discrepancy found + what still needs a human decision
01-content-and-gameplay.txt          category 1 of 5
02-world-generation.txt              category 2 of 5
03-utilities-qol-libraries.txt       category 3 of 5
04-performance-rendering-visuals.txt category 4 of 5
05-server-management-security.txt    category 5 of 5
source/modlist-server.txt            original server mod list (46 records, verbatim)
source/rune-modpack-filelist.txt     original .mrpack file list (4 tiers, 32 files, verbatim)
```

## Headline numbers

| | BOTH | SERVER | CLIENT | total |
|---|---:|---:|---:|---:|
| content & gameplay | 10 | 4 | 0 | 14 |
| world generation | 0 | 2 | 0 | 2 |
| utilities, QoL & libraries | 9 | 1 | 0 | 10 |
| performance, rendering & visuals | 12 | 8 | 10 | 30 |
| server management & security | 1 | 5 | 0 | 6 |
| **total** | **32** | **20** | **10** | **62** |

62 unique records = 46 from the server mod list + 12 that only exist in the four
client `.mrpack` tiers + 4 added after the audit (Vanilla Backport, Platform,
Better Horses and Donkeys, Darceno's Minecarts - section G of
`AUDIT-NOTES.txt`). Pack membership reproduces the source documents exactly
(27 core mods from the sources, 31 with the four additions; 32 files in
no-shaders; 34 files in each shader tier). Vein mining needed no new record:
ChainVein was already in the pack.

## Record format

Every data line is pipe separated and self-describing:

```
kind|side|source|slug|mr_id|cf_id|client|server|version|packs|display name
```

| field | meaning |
|---|---|
| `kind` | `mod`, `datapack`, `resourcepack` or `shader` |
| `side` | `BOTH`, `SERVER` or `CLIENT` - the bucket the record is filed under |
| `source` | `modrinth` or `curseforge` - the host the download comes from |
| `slug` | project slug / label as used by the source documents |
| `mr_id` | Modrinth project id. Blank = not published on Modrinth. A trailing `?` = cross-link that could not be confirmed from the author or the API |
| `cf_id` | numeric CurseForge project id. Blank = not on CurseForge |
| `client` | `required` / `optional` / `unsupported` - can the game run *without* a client copy |
| `server` | `required` / `optional` / `unsupported` - can the game run *without* a server copy |
| `version` | version pinned by the source documents (`n/a` = the document only lists the record, no version) |
| `packs` | `S` = server mod list, `N` = no-shaders, `L` = low, `M` = mid, `H` = high |

Side rule applied to every record:

* **BOTH** - `client=required` and `server=required`, or the mod is usable and
  recommended on both sides (e.g. both `optional`).
* **SERVER** - `server=required`, client `optional`/`unsupported`.
* **CLIENT** - `client=required`, server `optional`/`unsupported`.

## How the client/server values were verified

1. **Modrinth project API** (`/v2/project/<slug|id>`) for every project that is
   published on Modrinth - the `client_side` / `server_side` fields are set by
   the mod authors, so they are used as the authority.
2. **CurseForge project metadata** (title, summary, description) for the 9
   projects that are CurseForge-only, so the numeric id in the source list is
   resolved to a real project and the install side is read from its own
   description ("Only required on serverside", "Server-side anti-cheat", ...).
3. **Web search** as a second opinion on the handful of descriptions that are
   ambiguous (results recorded in `AUDIT-NOTES.txt`).

No API keys or credentials are stored in this repository.

## Auditing

```bash
grep -h '^mod|SERVER' *.txt            # everything that must be on the server
grep -h '^mod|CLIENT' *.txt            # client-only jars
grep -h '|S|' *.txt | cut -d'|' -f11   # records in the server mod list
grep -h '^datapack' *.txt              # datapacks (not jars)
awk -F'|' '$9=="n/a"{print $11}' *.txt # records with no pinned version
```

`SUMMARY.txt` holds the same counts in one place; `AUDIT-NOTES.txt` lists the 20
open questions (mis-filed mods, a missing dependency on the server list, a
client-only mod shipped on the server, stale labels and version caveats) plus
section G, which documents the four mods added after the audit (Vanilla
Backport, Platform, Darceno's Minecarts, Better Horses and Donkeys) and why
vein mining needed no new record (ChainVein already covers it).
