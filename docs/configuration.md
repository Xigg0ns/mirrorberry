# Configuration

Everything is set in `config.toml` in the MirrorBerry folder. Start from
`config.example.toml`, which reproduces a typical MagicMirror² screen:

```bash
cp config.example.toml config.toml
```

The file uses [TOML](https://toml.io/). Restart MirrorBerry after editing it
(`sudo systemctl restart mirrorberry@$USER`). If a widget's settings are wrong,
that zone shows what's wrong and the rest of the screen keeps running; a mistake
outside the zones (a TOML syntax error, an unknown `[theme]` key) stops the app
with the error in the log.

**Units used below**

- **seconds** for all intervals.
- **px** means MagicMirror² CSS pixels: they are multiplied by
  [`scale`](#display) to get screen pixels, so the whole screen can be resized in
  one place. This is also why values copied from MagicMirror²'s CSS work as-is.
- **Colours** are `"#RRGGBB"`.

Contents: [general](#general) · [display](#display) · [layout](#layout) ·
[theme](#theme) · [loop](#loop) · [zones](#zones) · widgets:
[clock](#clock) · [weather](#weather) · [calendar](#calendar) ·
[resrobot](#resrobot-departures) · [namnsdag](#namnsdag-name-days) ·
[placeholder](#placeholder) · [date formats](#date-and-time-formats)

---

## [general]

| Setting | Default | Description |
|---------|---------|-------------|
| `locale` | `""` | Locale for day and month names, e.g. `"sv_SE.UTF-8"` or `"en_GB.UTF-8"`. It must be installed on the system (see [installation](installation.md)). `""` uses the system default. |
| `language` | `""` | Language of MirrorBerry's own texts ("I morgon", "Känns som", error messages): `"sv"` or `"en"`. `""` takes it from `locale`; other languages fall back to English. |

## [display]

| Setting | Default | Description |
|---------|---------|-------------|
| `backend` | `"auto"` | `"fbdev"` writes to `/dev/fb0` (use this on a Pi Zero W), `"sdl"` lets SDL drive the screen via the GPU, `"auto"` picks `fbdev` on a Pi without a desktop and a window elsewhere. See [installation](installation.md#display-backends). |
| `fullscreen` | `true` | `false` opens a window, for development. |
| `window_size` | `[540, 960]` | Window size in windowed mode, `[width, height]`. |
| `rotation` | `0` | `0`, `90`, `180` or `270` degrees counter-clockwise, for a monitor mounted in portrait. Fullscreen only. |
| `background` | `"#000000"` | Screen background. |
| `scale` | `"auto"` | How many screen pixels one px is. `"auto"` is 1.0 on a 1080p screen (and scales with other resolutions), which matches MagicMirror² at zoom 1 on a 1080p screen. |

**Matching a MagicMirror² screen.** MagicMirror²'s `zoom` option enlarges
everything. MirrorBerry looks the same when
`scale = zoom × (MirrorBerry screen height ÷ MagicMirror² screen height)`.
Example: MagicMirror² with `zoom: 2` on a 2560x1440 screen, MirrorBerry on
1920x1080: `scale = 2 × 1080 ÷ 1440 = 1.5`.

## [layout]

The screen is divided into a 3x3 grid of zones:

```
+-------------+--------------+-------------+
| TopLeft     | TopCenter    | TopRight    |
+-------------+--------------+-------------+
| CenterLeft  | Center       | CenterRight |
+-------------+--------------+-------------+
| BottomLeft  | BottomCenter | BottomRight |
+-------------+--------------+-------------+
```

| Setting | Default | Description |
|---------|---------|-------------|
| `column_weights` | `[1, 1, 1]` | Relative widths of the left, centre and right columns. `[1, 2, 1]` makes the centre twice as wide. `0` collapses a column. |
| `row_weights` | `[1, 1, 1]` | Relative heights of the top, centre and bottom rows. |
| `margin` | `0` | Space around the whole grid, px. MagicMirror²'s default body margin is 60. |
| `gutter` | `0` | Space between zones, px. |
| `padding` | `0.08` | Space inside each zone, as a fraction of the zone's shorter side. Use `0` together with `margin` for a MagicMirror²-like layout. |
| `stack_gap` | `30` | Space between widgets stacked in one zone, px (MagicMirror²'s gap between modules). |

### [layout.valign]

Where a zone's widgets sit vertically when they don't fill it: `"top"`,
`"center"` or `"bottom"`, per zone. Top and centre rows default to `"top"`, the
bottom row to `"bottom"` (like MagicMirror²'s bottom regions).

```toml
[layout.valign]
BottomLeft = "top"
```

## [theme]

MirrorBerry styles text with MagicMirror²'s size classes. `[theme]` changes them
the way a MagicMirror² `custom.css` would. Leave it out for MagicMirror²'s stock
look.

| Setting | Default | Description |
|---------|---------|-------------|
| `sizes` | `{ xsmall = 15, small = 20, medium = 30, large = 65, xlarge = 75 }` | Font size per class, px. |
| `line_heights` | `{ xsmall = 1.275, small = 1.25, medium = 1.225, large = 1.0, xlarge = 1.0 }` | Line height per class, as a multiple of the font size. |
| `letter_spacing` | `{ xlarge = -3 }` | Extra space between letters per class, px; negative is tighter. |
| `header_size` | `15` | Font size of module headers ("KALENDER"). MagicMirror² uses its xsmall size. |
| `header_line` | `1.0` | Header line height, as a multiple of `header_size`. |
| `header_padding` | `5` | Space between the header text and its line, px. |
| `header_rule` | `1` | Thickness of the line under the header, px. |
| `header_margin` | `10` | Space between the header line and the widget's content, px. |
| `cell_padding` | `1` | Padding in table cells (forecast, calendar, departures), px; browsers use 1. |

You only need to list what you change; `sizes = { small = 26.67 }` keeps the
other classes at their defaults.

Which text uses which class:

| Class | Used by |
|-------|---------|
| xsmall | the "Data från Trafiklab.se" credit; error details; tables with `table_class = "xsmall"` |
| small | forecast, calendar and departure tables (default `table_class`), name days, clock seconds (`sizing = "theme"`) |
| medium | current weather's first and last line, clock date and week (`sizing = "theme"`) |
| large | current temperature, clock time (`sizing = "theme"`) |
| xlarge | not used by the built-in widgets |

Example: the theme in `config.example.toml`, measured from a MagicMirror² screen
with a custom.css:

```toml
[theme]
sizes          = { xsmall = 20, small = 26.67, medium = 40, large = 50 }
line_heights   = { xsmall = 1.135, small = 1.1, medium = 1.1, large = 1.0 }
letter_spacing = { large = -3 }
header_size    = 40
header_line    = 1.0
header_margin  = 6
```

## [loop]

| Setting | Default | Description |
|---------|---------|-------------|
| `tick_ms` | `1000` | Longest the main loop sleeps, in milliseconds. Widgets are woken exactly when they're due regardless, so there's rarely a reason to change this. |

---

## Zones

Each zone is configured in a `[zones.<Name>]` section. `widget` picks the widget;
every other key is an option for that widget.

```toml
[zones.TopCenter]
widget = "resrobot"
api_key = "…"
```

**Several widgets in one zone.** Repeat `[[zones.<Name>]]` (double brackets) to
stack widgets top to bottom, in the order they appear, like modules in a
MagicMirror² region. Sub-tables such as `[[zones.TopRight.calendars]]` belong to
the widget just above them:

```toml
[[zones.TopRight]]
widget = "clock"
sizing = "theme"

[[zones.TopRight]]
widget = "calendar"
header = "Kalender"

[[zones.TopRight.calendars]]
url = "https://…"
```

A zone uses either `[zones.X]` or `[[zones.X]]`, not both.

**Empty zones.** Zones that `config.toml` doesn't mention are empty, as is a zone
whose section is only the `[zones.X]` line, or one with `widget = "empty"`. A
section with options but no `widget` line shows an error in its zone. (With no
`config.toml` at all, every zone shows a coloured placeholder.)

**Tall stacks.** A zone reaches down over empty zones below it in the same
column. With `CenterRight` and `BottomRight` empty, `TopRight` gets the whole
right column, so a clock and a long calendar fit. Content that still doesn't fit
is cut off at the bottom of the zone; long calendar titles and destinations are
shortened with "…".

**Alignment.** Widgets are left-aligned in the left column, centred in the
centre column and right-aligned in the right column (the clock defaults to
right-aligned everywhere); set `align` to override. Headers in a zone share the
width of the zone's widest widget, like MagicMirror² modules in a region.

**Placeholders.** `widget = "placeholder"` shows the coloured block from
MirrorBerry's first revision, handy for trying out layouts.

### Options most widgets share

| Option | Widgets | Description |
|--------|---------|-------------|
| `header` | weather, calendar, resrobot, namnsdag | Header text above the widget, shown in capitals with a line under it. `""` = no header. |
| `align` | all | `"left"`, `"center"` or `"right"`. Default: follows the column. |
| `fade`, `fade_point` | weather forecast, calendar, resrobot | MagicMirror²'s fading list: rows after `fade_point` (a fraction of the list, default `0.25`) get dimmer towards the end. `fade = false` turns it off. |
| `table_class` | weather forecast, calendar, resrobot | Text size of the table: a [theme](#theme) class, default `"small"`. |
| `update_interval` / `fetch_interval` | weather, resrobot, namnsdag / calendar | Seconds between downloads, at least 60. |

---

## clock

Date, time with small superscript seconds, and the week number, right-aligned in
Roboto Condensed like MagicMirror²'s clock. Uses the Pi's local time and time
zone.

| Option | Default | Description |
|--------|---------|-------------|
| `time_format` | `"%H:%M"` | [Format](#date-and-time-formats) of the time. `"%-I:%M %p"` gives 12-hour time. |
| `seconds` | `false` | Show seconds as a small superscript after the time. |
| `date_format` | `"%A, %-d %b %Y"` | Format of the date line; `""` hides it. |
| `week_format` | `""` | Format of the week line, e.g. `"Vecka %-V"`; `""` hides it. |
| `capitalize_names` | `false` | Capitalize day and month names: "Söndag, 27 Sep" instead of "söndag, 27 sep". Other words are left alone. |
| `sizing` | `"fit"` | `"fit"` scales the clock to fill its zone. `"theme"` uses the theme's sizes (date and week medium, time large, seconds small), which is what you want when the clock shares a zone. |
| `align` | `"right"` | |
| `color` | `"#FFFFFF"` | Time. |
| `date_color` | `"#999999"` | Date line. |
| `seconds_color` | `"#666666"` | Seconds. |
| `week_color` | `"#666666"` | Week line. |
| `background` | `"#000000"` | |
| `font` | Roboto Condensed Regular | Path to a .ttf/.otf font for the date and week lines. |
| `time_font` | Roboto Condensed Light | Font for the time and seconds. |

## weather

Current weather or a daily forecast, like MagicMirror²'s default weather module.
Current weather and the forecast are two widgets (`type`); use one of each,
stacked, for MagicMirror²'s usual pair. Widgets for the same place and provider
share one download.

**Providers** (no API key needed):

- `"smhi"`: [SMHI](https://opendata.smhi.se/)'s point forecast (SNOW1gv1),
  covering Sweden and the surrounding Nordic area, processed exactly like
  MagicMirror²'s SMHI provider.
- `"openmeteo"`: [Open-Meteo](https://open-meteo.com/), worldwide. Free for
  non-commercial use.

| Option | Default | Applies to | Description |
|--------|---------|-----------|-------------|
| `type` | `"current"` | | `"current"` or `"forecast"`. |
| `provider` | `"openmeteo"` | | `"smhi"` or `"openmeteo"`. |
| `latitude`, `longitude` | required | | Your location in decimal degrees, e.g. `59.3293`, `18.0686`. |
| `header` | `""` | | |
| `update_interval` | `600` | | Seconds between downloads. Two widgets sharing a download use the shorter interval. |
| `round_temp` | `false` | both | `12°` instead of `12.3°`. |
| `decimal_symbol` | `"."` | both | e.g. `","` for `12,3°`. |
| `show_wind_direction` | `true` | current | Compass direction after the wind speed (in the display language, e.g. "NO"). Wind speed is in m/s. |
| `show_sun` | `true` | current | Next sunrise or sunset with its icon. |
| `show_feels_like` | `true` | current | The "Känns som" line. |
| `temp_gap` | `10` | current | Space between the weather icon and the temperature, px. |
| `max_days` | `5` | forecast | Number of rows, including today. |
| `ignore_today` | `false` | forecast | Start the forecast tomorrow. |
| `forecast_date_format` | `"%a"` | forecast | [Format](#date-and-time-formats) of the day names after "I dag" and "I morgon". |
| `capitalize_names` | `false` | forecast | "Tis" instead of "tis". |
| `colored` | `false` | forecast | Maximum temperatures in red, minimums in blue. |
| `fade`, `fade_point` | `true`, `0.25` | forecast | See [shared options](#options-most-widgets-share). |
| `table_class` | `"small"` | forecast | Text size. |
| `cell_padding` | see below | forecast | Space around the forecast columns, px. |
| `align` | by column | both | |

`cell_padding` keys and their defaults (MagicMirror²'s weather.css):
`{ day_right = 25, icon_left = 1, icon_right = 30, max_left = 1, max_right = 1, min_left = 20 }`.
List only the ones you change, e.g. `cell_padding = { day_right = 16 }`.

## calendar

Upcoming events from one or more iCal (.ics) feeds, like MagicMirror²'s default
calendar module. Recurring events, exceptions and moved occurrences are expanded.

**Calendar addresses.** Any URL to an .ics file works (`https://`, `webcal://`,
or `file:///path/to/calendar.ics`):

- Google Calendar: *Settings → your calendar → Integrate calendar → Secret address
  in iCal format*. Treat this address like a password.
- iCloud: share the calendar as a public calendar and use its `webcal://` link.
- Outlook / Microsoft 365: *Settings → Calendar → Shared calendars → Publish a
  calendar*, then the ICS link.
- Nextcloud: the calendar's *Copy subscription link*.

Add one `[[zones.<Name>.calendars]]` block per calendar:

```toml
[[zones.TopRight.calendars]]
url    = "https://calendar.google.com/calendar/ical/…/basic.ics"
symbol = "calendar-days"

[[zones.TopRight.calendars]]
url    = "https://…/birthdays.ics"
symbol = "cake-candles"
```

Keys per calendar:

| Key | Default | Description |
|-----|---------|-------------|
| `url` | required | Address of the .ics file. |
| `symbol` | the widget's `symbol` | Font Awesome icon name for this calendar's events. |
| `maximum_number_of_days` | the widget's | How many days ahead to look. |
| `fetch_interval` | the widget's | Seconds between downloads of this calendar. |

For a single calendar, `url` and `symbol` can also be set directly on the widget.

Widget options:

| Option | Default | Description |
|--------|---------|-------------|
| `header` | `""` | |
| `maximum_entries` | `10` | Number of events shown. |
| `maximum_number_of_days` | `365` | How many days ahead to look. |
| `max_title_length` | `25` | Longer titles are cut with "…". |
| `hide_duplicates` | `true` | An event that is in several calendars is shown once. |
| `display_symbol` | `true` | Show the symbol column. |
| `symbol` | `"calendar-days"` | Default symbol: any Font Awesome 7 Free Solid icon name, see [fontawesome.com/icons](https://fontawesome.com/icons) (Free, Solid). |
| `time_format` | `"relative"` | How the time of an event is written, see below. |
| `get_relative` | `6` | Hours: events starting within this time show "Om 2 timmar" instead of a clock time. Running events show "Slutar om …". |
| `date_format` | like "Okt 20:e" | [Format](#date-and-time-formats) for timed events further away, e.g. `"%-d %b"`. |
| `full_day_event_date_format` | like "Okt 20:e" | Format for full-day events further away, e.g. `"%a, %d %b"` → "Tor, 01 okt". |
| `urgency` | `7` | `absolute` only: timed events within this many days still say "Om 3 dagar". `0` turns it off. |
| `next_days_relative` | `false` | `absolute` only: full-day events today, tomorrow and the day after say "I dag", "I morgon" and "I övermorgon". |
| `capitalize_names` | `false` | Capitalize day and month names in dates: "Tor, 01 Okt". |
| `fetch_interval` | `3600` | Seconds between downloads, per calendar. |
| `fade`, `fade_point` | `true`, `0.25` | |
| `table_class` | `"small"` | Text size. |
| `cell_padding` | see below | Space around the columns, px. |
| `align` | by column | Titles are aligned like the zone: right-aligned in the right column. |

**`time_format`**, as in MagicMirror²:

- `"relative"`: "I dag", "I morgon", "På fredag", "Om 2 timmar", and a date for
  events more than a week away.
- `"absolute"`: dates ("Tor, 01 okt") for everything, except timed events within
  `urgency` days ("Om 3 dagar") and running events ("Slutar om 1 timme").

`cell_padding` keys and their defaults (MagicMirror²'s calendar.css):
`{ title_left = 10, title_right = 10, time_left = 20 }`.

## resrobot (departures)

Departures from one or more public transport stops in Sweden, from
[Trafiklab](https://www.trafiklab.se/), like MMM-ResRobot. One table for all
routes, earliest first: time, vehicle icon, line, track, destination.

**Providers.** Both need a free API key: create an account and a project at
trafiklab.se and add a key for the API you use.

- `"resrobot"`: ResRobot v2.1, what MMM-ResRobot uses. Trafiklab has marked it
  deprecated.
- `"trafiklab"`: the Trafiklab Realtime API, ResRobot's replacement, with
  real-time times and platforms for much of Sweden. Its data is CC BY, so a small
  "Data från Trafiklab.se" credit is shown under the table.

**Stop IDs** look like `740000001` and are the same in both APIs. Look them up
with Trafiklab's stop lookup (ResRobot Stop lookup or Trafiklab Stop Lookup).

**Routes.** Add one `[[zones.<Name>.routes]]` block per stop:

```toml
[[zones.TopCenter.routes]]
from = "740020749"    # departures from this stop
to   = "740000002"    # optional, ResRobot only: only vehicles heading towards this stop
```

| Option | Default | Description |
|--------|---------|-------------|
| `api_key` | required | Your Trafiklab key for the chosen provider. |
| `provider` | `"resrobot"` | `"resrobot"` or `"trafiklab"`. |
| `routes` | required | See above. |
| `lines` | all | Only these lines, e.g. `["4", "19"]`. |
| `destinations` | all | Only destinations containing one of these texts, e.g. `["Hässelby"]`. |
| `header` | `""` | |
| `maximum_entries` | `6` | Number of departures shown. |
| `maximum_duration` | `360` | ResRobot only: minutes ahead to ask for. |
| `skip_minutes` | `0` | Hide departures leaving within this many minutes (time to walk to the stop). |
| `get_relative` | `0` | Show "5 min" and "Nu" for departures within this many minutes; `0` always shows the time. |
| `realtime` | `true` | Use real-time times and tracks when Trafiklab has them; `false` shows timetable times only. |
| `truncate_after` | `5` | Shorten destinations at the first space after this many characters, like MMM-ResRobot; `0` = never. |
| `truncate_line_after` | `5` | Longest line name, in characters; `0` = no limit. |
| `show_track` | `true` | Show the track or platform column. |
| `colored_icons` | `false` | Colour the vehicle icons (see `color_table`). |
| `icon_table` | see below | Font Awesome icon per vehicle type. |
| `color_table` | see below | Icon colour per vehicle type. |
| `update_interval` | `300` | Seconds between downloads, per route. Each download is one API call: 288 per route per day at 300. |
| `fade`, `fade_point` | `true`, `0.25` | |
| `table_class` | `"small"` | Text size. |
| `column_widths` | natural | Minimum `[time, icon, line, track]` column widths, px. MMM-ResRobot's CSS sizes columns by percentage; use this to match its spacing. |
| `align` | by column | |

Departures leave the list as they depart (checked every minute, without extra
API calls). If a long destination doesn't fit its zone, it's shortened with "…".

Vehicle types are the first letter of Trafiklab's product category.
`icon_table` and `color_table` merge with the defaults, so list only what you
change:

| Type | Default icon | Default colour |
|------|-------------|----------------|
| `B` bus | `bus` | `#DA4439` |
| `S` tram | `train-subway` | `#019CD5` |
| `J` train | `train` | `#FDB813` |
| `U` metro | `train-subway` | `#019CD5` |
| `F` ferry | `ship` | `#444400` |
| `T` taxi | `taxi` | |

```toml
icon_table  = { B = "bus-simple" }
color_table = { B = "#00A0E0" }
```

## namnsdag (name days)

Today's Swedish name days, like MMM-Namnsdag, from the Svenska Dagar API. One
name per line, fetched again right after midnight.

| Option | Default | Description |
|--------|---------|-------------|
| `header` | `""` | |
| `single_line` | `false` | "Lennart, Leonard" on one line instead of one name per line. |
| `separator` | `", "` | Between names with `single_line`. |
| `center_lines` | `false` | Centre the names on each other. |
| `text_class` | `"small"` | Text size. |
| `update_interval` | `21600` | Seconds between downloads (6 hours). |
| `align` | by column | |

## placeholder

A coloured block labelled with its zone name, from MirrorBerry's first revision.

| Option | Default | Description |
|--------|---------|-------------|
| `color` | a different colour per zone | Block colour. |
| `label` | the zone name | Text in the block. |
| `show_geometry` | `true` | Show the zone's size and position in pixels. |

---

## Date and time formats

Clock, weather and calendar formats use Python's
[strftime codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).
Day and month names follow `[general] locale`.

| Code | Example (sv) | Meaning |
|------|--------------|---------|
| `%A` / `%a` | söndag / sön | Weekday name, full / short |
| `%B` / `%b` | september / sep | Month name, full / short |
| `%d` / `%-d` | 07 / 7 | Day of the month, with / without leading zero |
| `%m` / `%-m` | 09 / 9 | Month number |
| `%Y` / `%y` | 2026 / 26 | Year |
| `%H` / `%-H` | 08 / 8 | Hour, 24-hour clock |
| `%I` / `%-I`, `%p` | 08 / 8, PM | Hour, 12-hour clock, and AM/PM |
| `%M` / `%-M` | 05 / 5 | Minute |
| `%S` / `%-S` | 09 / 9 | Second |
| `%V` / `%-V` | 09 / 9 | ISO week number |

The `%-` forms (no leading zero) work on every platform in MirrorBerry. With
`capitalize_names = true`, the name codes (`%A %a %B %b`) are capitalized;
everything else is left as written. `%%` is a literal `%`.
