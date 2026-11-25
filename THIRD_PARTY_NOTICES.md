# Third-party notices

Prism itself is MIT licensed (see `LICENSE`). The ready-to-run folder
`build/bin/` bundles third-party components. Their licenses and obligations
are listed here honestly — including the one thing that is **not** confirmed.

## Qt 6.10.2 (LGPLv3 / GPLv2 / GPLv3, dual licensed)

Qt Quick, Qt Core, Qt Gui, Qt Multimedia, Qt Network and the bundled Qt
runtime DLLs are copyright The Qt Company and contributors. Prism uses the
open-source LGPLv3 option.

- License: GNU Lesser General Public License v3 (or commercial licensing from Qt).
- Source: https://code.qt.io/cgit/qt/qtbase.git/  (and sibling Qt modules)
- Obligations respected: Qt is dynamically linked, its source is publicly
  available from upstream, and users may replace the LGPL libraries. No Qt
  source code has been modified.

## mpv 0.42.0 (license mode — see the honest note below)

Bundled as `build/bin/mpv.exe` (thumbnail extraction) and `libmpv-2.dll`
(in-process rendering). mpv is copyright mpv/MPlayer/mplayer2 projects.

- Upstream: https://github.com/mpv-player/mpv
- mpv is **GPLv2+ by default**, and **LGPLv2.1+** only when built with
  `-Dgpl=false` (excluding GPL-only files). See
  https://github.com/mpv-player/mpv/blob/master/Copyright
- **Honest status: the exact license mode of the bundled binary is not
  confirmed.** The design doc records the intent to use an LGPL build, but the
  shipped binary reports FFmpeg + libplacebo, and no `-Dgpl=false` build flag
  was captured. Treat it as GPLv2+ until proven otherwise. If you redistribute
  this bundle commercially, verify the build mode first; an LGPL build can be
  built with `-Dgpl=false`.
- FFmpeg (bundled inside mpv): LGPLv2.1+ / GPLv2+ depending on configuration;
  source: https://ffmpeg.org/download.html

## Kenney Interface Sounds (CC0 1.0)

The 35 interface WAV files under `themes/<id>/` are derived from
[Kenney Interface Sounds](https://kenney.nl/assets/interface-sounds)
(100 sounds, CC0 1.0 / public domain dedication), with per-theme pitch,
filtering and bit-crushing applied by `tools/apply_theme_sfx_v3.py`.

- License: CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/
- Attribution is optional; credit "Kenney (kenney.nl)".
- Kenney's logo is **not** used, and no endorsement is implied.

## Fonts

The theme typefaces (Microsoft YaHei UI, SimHei, SimSun, FangSong, DengXian,
Consolas, Noto Sans SC) are **referenced by name only** — no font files are
redistributed. Each remains under its own vendor license on the user's system.

## No secrets / personal data

This repository contains no credentials, API keys, or personal identifiers.
Git history uses the public GitHub identity `mike22890` only.
