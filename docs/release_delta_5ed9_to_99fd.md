# Release Delta: 5ED9 to 99FD

This inventory compares the last full-game runtime baseline with the
current source-reproducible Korean ROM and assigns every changed byte
to an explicit owner.

- Baseline commit: `3e4954a8a493344cb31fb29b91e71f3a5c61ef54`
- Baseline checksum / SHA-256: `5ED9` / `ba9d3ae0f481a3f1421a1286d5e215fe4d49143d49fc1e32737c9868b66d4d27`
- Candidate last ROM change: `ed82c841a710125d90b371f81fb12a76db873a61`
- Candidate checksum / SHA-256: `99FD` / `526237277c8f46a4400c00980da704e6ebea23e74d967d89b6d223db28dd54d3`
- Changed bytes: `2244`
- Unclassified changed bytes: `0`

| Owner | Permitted bytes | Changed bytes | Changed ranges |
| --- | ---: | ---: | ---: |
| `bald_custom_sprite` | 256 | 0 | 0 |
| `header_checksum` | 2 | 2 | 1 |
| `loren_custom_sprite` | 256 | 94 | 51 |
| `shaman_commander_sprites` | 1792 | 1788 | 6 |
| `shaman_generic_sprite` | 256 | 256 | 2 |
| `shaman_sprite_pointers` | 16 | 16 | 8 |
| `villain_montage_records` | 136 | 88 | 28 |

The two checksum bytes are derived metadata. The 16 pointer bytes
select separate expanded-ROM Shaman sprites. The 88 montage bytes
are confined to the overlapping `0x0A6B20..0x0A6BA8` records.
All remaining changes are map-sprite pixels in reserved expanded-ROM
frames. No scenario event, shared UI code, text pointer, unit stat,
or balance record changed between these builds.

## Live Evidence

- `villain_montage_records`: cold-boot Alhazard line — `captures/run/99fd_opening_villain_alhazard.png` (`68d423bfc1fc728e41c0abd3ea02d3dd1b5a963fd0a13edfa816ce57af473e60`)
- `villain_montage_records`: cold-boot power line — `captures/run/99fd_opening_villain_power.png` (`f0c32e25ed3ac1b733dc9509d98355a2df5bf0c716eadda431e3516eea2c219d`)
- `villain_montage_records`: cold-boot world line — `captures/run/99fd_opening_villain_world.png` (`53e1ae5d9da6589d2fb2622e5eabfc4d810a9236331ca631cfaa124c25b5eef3`)
- `villain_montage_records`: return to intact title — `captures/run/99fd_opening_villain_title_return.png` (`4f7985b3f7e79eaed2f6deb8f4162003718b88e32fc7bee8468d03e731feae61`)
- `shaman_generic_sprite`: source candidate screen — `captures/run/99fd_release_shaman_candidate1.png` (`c51df1994b04395969b265402e36635c91b57f4715e19e49b2cb533a87691660`)
- `shaman_commander_sprites`: applied Shaman stable map — `captures/run/99fd_release_shaman_stable_map.png` (`5047664afe51b2b57f1f6b373003b97258ecb1cad362d0d37a1355b33b6f61bb`)
- `shaman_commander_sprites`: applied Shaman command and status panel — `captures/run/99fd_release_shaman_applied_status.png` (`55a59a07a8bce3db9aaf96367a00ec6738549f2d3c8bd9e1f79bd92e0c8045ae`)
- `shaman_sprite_pointers`: applied class 0A / commander 1 / LV1 GST — `captures/analysis/99fd_release_shaman.gst` (`74464277f3977e4dff2dc2aaddcc09a992679efabb14c9bc67553453ac6ba9b7`)
- `loren_custom_sprite`: Scenario 2 Loren map and status row — `captures/run/99fd_release_loren_status.png` (`ab8bd0090b7f680ecce5134753e408da9e6e9d9258c2345d96121d7009a81edc`)
- `loren_custom_sprite`: Scenario 2 Loren popup — `captures/run/99fd_release_loren_popup.png` (`7002e058d071178e7c0902a1c0769c28d6f3ca8676e39fd1df20f6b11ba58cf2`)

The baseline can be reproduced by checking out the recorded detached
commit in a temporary worktree, copying the same Japanese source ROM
to `roms/original/`, and running `scripts/build_korean_jp_probe.py`.
