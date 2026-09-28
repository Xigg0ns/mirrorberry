# Third-party notices

MirrorBerry is licensed under the GNU General Public License v3.0 or later (see
[LICENSE](LICENSE)). It contains code ported from, and bundles files from, the
projects below, which keep their own licences. Their copyright notices and
licence texts are reproduced here as those licences require.

MirrorBerry is an independent project, not affiliated with or endorsed by any of
the projects or services listed here.

## Code ported into MirrorBerry

### MagicMirror²

<https://github.com/MagicMirrorOrg/MagicMirror>. Used in `mirrorberry/widgets/weather.py`
(weather processing, including the SMHI and Open-Meteo providers),
`mirrorberry/widgets/calendar.py` (event selection and time wording) and
`mirrorberry/i18n.py` (Swedish and English translations). The visual design
(sizes, colours, headers, fading) follows MagicMirror²'s CSS.

```text
The MIT License (MIT)

Copyright © 2016-2026 Michael Teeuw

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the “Software”), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

The software is provided “as is”, without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.
```

### MMM-ResRobot

<https://github.com/Alvinger/MMM-ResRobot> by Johan Alvinger. Used in
`mirrorberry/widgets/resrobot.py` (departure processing, options, icon and
colour tables). MMM-ResRobot declares the MIT licence in its `package.json`; the
repository has no separate licence file, so the standard MIT text is reproduced.

```text
The MIT License (MIT)

Copyright (c) Johan Alvinger and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### moment.js

<https://momentjs.com/>. The relative-time rules and thresholds ("Om 2 timmar",
"På fredag 14:00") in `mirrorberry/i18n.py` follow moment.js and its Swedish
locale, as MagicMirror² uses them.

```text
Copyright (c) OpenJS Foundation and other contributors

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
```

### suncalc

<https://github.com/mourner/suncalc>. `mirrorberry/sun.py` is a port of
suncalc's sunrise and sunset calculation.

```text
Copyright (c) 2026, Volodymyr Agafonkin
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Behaviour recreated without copying code

### MMM-Namnsdag

<https://github.com/Menturan/MMM-Namnsdag> by Menturan, licensed GPL-3.0.
`mirrorberry/widgets/namnsdag.py` was written from scratch to behave like this
module (today's names from the same Svenska Dagar API, one per line under a
header, refreshed after midnight). No code was copied. MirrorBerry's own licence,
GPL-3.0-or-later, is compatible with it either way.

## Bundled fonts

In `mirrorberry/assets/fonts/`, unmodified apart from the format conversion noted:

| File | Project | Licence |
|------|---------|---------|
| `fa-solid-900.ttf`, `fa-solid-names.json` | [Font Awesome Free](https://fontawesome.com) 7.3.1 by Fonticons, Inc. The font was converted from WOFF2 to TTF (same glyphs); the names file lists icon names and codepoints from Font Awesome's CSS. | Icons: CC BY 4.0; font: SIL OFL 1.1; see `FontAwesome-LICENSE.txt` |
| `weathericons-regular-webfont.ttf` | [Weather Icons](https://github.com/erikflowers/weather-icons) by Erik Flowers | SIL OFL 1.1, see `WeatherIcons-OFL.txt` |

## Used but not included

Installed separately (see [docs/installation.md](docs/installation.md)):

| Component | Licence |
|-----------|---------|
| [pygame](https://www.pygame.org/) | LGPL-2.1 |
| [icalendar](https://github.com/collective/icalendar) | BSD-2-Clause |
| [recurring-ical-events](https://github.com/niccokunzmann/python-recurring-ical-events) | LGPL-3.0-or-later |
| Roboto and Roboto Condensed fonts by Google (Debian package `fonts-roboto-unhinted`) | Apache-2.0 |

## Data services

MirrorBerry downloads data from these services. Their terms apply to the data,
not to MirrorBerry's code; check each service's current terms before use.

| Service | Used by | Terms |
|---------|---------|-------|
| [SMHI open data](https://www.smhi.se/data/om-smhis-data/villkor-for-anvandning) | weather, `provider = "smhi"` | Creative Commons Erkännande (Attribution) 4.0 SE. Credit SMHI as the source. |
| [Open-Meteo](https://open-meteo.com/en/terms) | weather, `provider = "openmeteo"` | Free API for non-commercial use only, rate-limited; data CC BY 4.0 with attribution. |
| [Trafiklab Realtime API](https://www.trafiklab.se/api/our-apis/trafiklab-realtime-apis/) | departures, `provider = "trafiklab"` | CC BY 4.0. MirrorBerry shows the required "Data från Trafiklab.se" credit under the departures. Needs an API key. |
| [ResRobot v2.1](https://www.trafiklab.se/api/resrobot-reseplanerare/licens) (Samtrafiken, via Trafiklab) | departures, `provider = "resrobot"` | Data CC0 1.0. Needs an API key. |
| Svenska Dagar API 2.1 ([sholiday.faboul.se](https://sholiday.faboul.se/), originally api.dryg.net) | name days | Free public API; no licence stated. |
| Your calendar provider | calendar | Your own data. |
