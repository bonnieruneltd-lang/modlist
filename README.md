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
MRPACK-MANIFEST.txt                  per tier: every file resolved on Modrinth (version id + sha1 + URL)
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
| content & gameplay | 11 | 3 | 0 | 14 |
| world generation | 0 | 2 | 0 | 2 |
| utilities, QoL & libraries | 9 | 1 | 0 | 10 |
| performance, rendering & visuals | 11 | 6 | 10 | 27 |
| server management & security | 1 | 4 | 0 | 5 |
| **total** | **32** | **16** | **10** | **58** |

**Every record is Modrinth-hosted** (project id + Forge 1.20.1 file), so each of
the five buckets can be exported straight to a `.mrpack` without a single
CurseForge download. 58 records = 46 from the server mod list + 12 that only
exist in the four client `.mrpack` tiers, after the Modrinth-only migration
(15 CurseForge projects already had a Modrinth listing, 5 were substituted for a
Modrinth equivalent, 5 were dropped because no Modrinth build exists, and the two
world-save mods were merged into one). Additions and substitutions are itemised
in `AUDIT-NOTES.txt` sections G and H; pack membership now reads 31 core mods,
32 files in no-shaders, 34 files in each shader tier. Vein mining needs no
record of its own: ChainVein is already in the pack.

## Record format

Every data line is pipe separated and self-describing:

```
kind|side|source|slug|mr_id|cf_id|client|server|version|packs|display name
```

| field | meaning |
|---|---|
| `kind` | `mod`, `datapack`, `resourcepack` or `shader` |
| `side` | `BOTH`, `SERVER` or `CLIENT` - the bucket the record is filed under |
| `source` | always `modrinth` - every download comes from Modrinth so the tiers can be packed as `.mrpack` |
| `slug` | Modrinth project slug (the label used by the source documents is quoted in `AUDIT-NOTES.txt` when it differed) |
| `mr_id` | Modrinth project id - required for every record (blank = cannot be packed) |
| `cf_id` | numeric CurseForge id **cross-link only** - kept so the original source-list id stays traceable; nothing is downloaded from CurseForge. Blank = the project has no CurseForge page (or the record is a substitution, see section H) |
| `client` | `required` / `optional` / `unsupported` - can the game run *without* a client copy |
| `server` | `required` / `optional` / `unsupported` - can the game run *without* a server copy |
| `version` | the exact Modrinth `version_number` to pin (`n/a` = the source documents pinned nothing; take the newest 1.20.1 Forge file) |
| `packs` | `S` = server mod list, `N` = no-shaders, `L` = low, `M` = mid, `H` = high |

Side rule applied to every record:

* **BOTH** - `client=required` and `server=required`, or the mod is usable and
  recommended on both sides (e.g. both `optional`).
* **SERVER** - `server=required`, client `optional`/`unsupported`.
* **CLIENT** - `client=required`, server `optional`/`unsupported`.

## How the records were verified

1. **Modrinth project API** (`/v2/project/<slug|id>`) for every record - the
   `client_side` / `server_side` fields are set by the mod authors, so they are
   used as the authority. All 58 records have a Modrinth project id.
2. **Modrinth version API** (`/v2/project/<id>/version?loaders=["forge"]&game_versions=["1.20.1"]`)
   for every record: each pinned `version` string was matched against the real
   `version_number` list, which is what a `.mrpack` has to resolve. Six pins that
   only existed as file names on the source side were rewritten to the Modrinth
   string (section H3).
3. **CurseForge metadata** (title, summary, description, file tags) is now used
   only to cross-check identity and the install side of a project that is listed
   on both platforms, and to record the legacy `cf_id`.
4. **Web search** as a second opinion on the handful of descriptions that are
   ambiguous (results recorded in `AUDIT-NOTES.txt`).

No API keys or credentials are stored in this repository.

## Building the five `.mrpack` tiers

`MRPACK-MANIFEST.txt` is the machine-readable output of the lists: one section
per tier (`S`, `N`, `L`, `M`, `H`), one line per file, already resolved through
the Modrinth API.

```
kind|side|slug|mr_id|version_id|version_number|file name|size|sha1|url
```

Every `url` is the Modrinth CDN link for that exact file (checked with HTTP 200
and a size match), so a pack builder can emit the `files` array of each
`.mrpack` without touching CurseForge: `path` = `mods/<file name>` (or
`shaderpacks/`, `resourcepacks/`, `datapacks/` for those kinds), `hashes.sha1`
and `hashes.sha512` from `/v2/version/<version_id>`, `downloads[0]` = `url`,
`fileSize` = `size`, and `env.client` / `env.server` from the `side` +
`client`/`server` columns of the category files.

Tier sizes: S 46, N 32, L 34, M 34, H 34 files (180 lines in total). Lines whose
`version_number` is `latest` come from records where the source documents pinned
no version - pin those before publishing (AUDIT-NOTES D7).

## Auditing

```bash
grep -h '^mod|SERVER' *.txt            # everything that must be on the server
grep -h '^mod|CLIENT' *.txt            # client-only jars
grep -h '|S|' *.txt | cut -d'|' -f11   # records in the server mod list
grep -h '^datapack' *.txt              # datapacks (not jars)
awk -F'|' '$9=="n/a"{print $11}' *.txt # records with no pinned version
awk -F'|' '!/^#/ && NF==11 && $3!="modrinth"{print}' *.txt  # must print nothing
awk -F'|' '!/^#/ && NF==11 && $5==""{print}' *.txt          # must print nothing
```

`SUMMARY.txt` holds the same counts in one place; `AUDIT-NOTES.txt` lists the
open questions (mis-filed mods, a missing dependency on the server list, a
client-only mod shipped on the server, stale labels and version caveats), plus
section G (the post-audit feature additions: Vanilla Backport, Platform,
Darceno's Minecarts, Walking Horses) and section H (the Modrinth-only migration:
which CurseForge projects already existed on Modrinth, which five were
substituted, which five had to be dropped because they have no Modrinth build,
and the six version strings that had to be re-pinned to a real Modrinth
`version_number` before an `.mrpack` could resolve them).
