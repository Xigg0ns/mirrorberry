# Coming from MagicMirror²

MirrorBerry recreates the look and behaviour of a
[MagicMirror²](https://magicmirror.builders/) screen with the default clock,
weather and calendar modules plus
[MMM-ResRobot](https://github.com/Alvinger/MMM-ResRobot) and
[MMM-Namnsdag](https://github.com/Menturan/MMM-Namnsdag), on hardware too small to
run MagicMirror² itself. It is not a MagicMirror² replacement in general:
MagicMirror² modules (JavaScript) don't run in MirrorBerry, and only the widgets
listed here exist.

This page maps what you know from MagicMirror² to MirrorBerry. All settings are
described in [configuration.md](configuration.md).

## Concepts

| MagicMirror² | MirrorBerry |
|--------------|-------------|
| `config/config.js` | `config.toml` ([TOML](https://toml.io/) instead of JavaScript) |
| a module | a widget |
| `position: "top_left"` | a zone: `[zones.TopLeft]` |
| several modules in one position | `[[zones.TopLeft]]` repeated, in the same order as in config.js |
| `header: "Kalender"` | `header = "Kalender"` |
| `zoom` | `[display] scale`, see [Matching a MagicMirror² screen](configuration.md#display) |
| `language`, `locale` | `[general] language`, `locale` |
| `css/custom.css` | `[theme]` for sizes, line heights, letter spacing and headers; `cell_padding` and `column_widths` on widgets for table spacing |
| module intervals in **milliseconds** (`updateInterval: 600000`) | intervals in **seconds** (`update_interval = 600`) |
| option names in camelCase (`maximumEntries`) | snake_case (`maximum_entries`) |
| moment.js date formats (`"ddd, DD MMM"`) | strftime formats (`"%a, %d %b"`), see [below](#date-formats) |

## Positions

| MagicMirror² position | MirrorBerry zone |
|-----------------------|------------------|
| `top_left`, `top_center`, `top_right` | `TopLeft`, `TopCenter`, `TopRight` |
| `middle_center` | `Center` |
| `bottom_left`, `bottom_center`, `bottom_right` | `BottomLeft`, `BottomCenter`, `BottomRight` |
| (none) | `CenterLeft`, `CenterRight` |
| `top_bar`, `bottom_bar`, `upper_third`, `lower_third`, `fullscreen_*` | no equivalent; use zones and `column_weights` |

MagicMirror²'s regions grow with their content; MirrorBerry's zones are fixed
parts of the screen. A zone reaches down over empty zones below it, so a
`top_right` stack of clock and calendar works the same way when `CenterRight`
and `BottomRight` are empty. Use `row_weights` and `[layout.valign]` to place a
bottom widget where it sat in MagicMirror².

## Module options

Options not listed here have no MirrorBerry equivalent. Defaults match
MagicMirror²'s unless noted.

### clock

| MagicMirror² | MirrorBerry |
|--------------|-------------|
| `timeFormat: 24` / `12` | `time_format = "%H:%M"` / `"%-I:%M %p"` |
| `displaySeconds` | `seconds` |
| `showDate: false` | `date_format = ""` |
| `dateFormat` | `date_format` (strftime) |
| `showWeek` | `week_format = "Vecka %-V"` (`""` hides it) |
| `secondsColor` | `seconds_color` |
| `displayType: "analog"` | not supported |

The clock also has `sizing = "theme"` to use the theme's text sizes like
MagicMirror²'s clock does; the default `"fit"` fills its zone instead.

### weather

| MagicMirror² | MirrorBerry |
|--------------|-------------|
| `weatherProvider: "smhi"` / `"openmeteo"` | `provider = "smhi"` / `"openmeteo"` |
| `type: "current"` / `"forecast"` (`"daily"`) | `type = "current"` / `"forecast"` |
| `lat`, `lon` | `latitude`, `longitude` |
| `updateInterval` (ms) | `update_interval` (s) |
| `roundTemp` | `round_temp` |
| `decimalSymbol` | `decimal_symbol` |
| `showFeelsLike`, `showSun`, `showWindDirection` | `show_feels_like`, `show_sun`, `show_wind_direction` |
| `maxNumberOfDays`, `ignoreToday` | `max_days`, `ignore_today` |
| `forecastDateFormat` | `forecast_date_format` (strftime) |
| `colored`, `fade`, `fadePoint`, `tableClass` | `colored`, `fade`, `fade_point`, `table_class` |

Units are metric (°C, m/s). Hourly forecasts, humidity, precipitation, UV and
indoor values are not supported, nor other providers. MirrorBerry's SMHI and
Open-Meteo processing is ported from MagicMirror²'s, so days, icons and values
match.

### calendar

| MagicMirror² | MirrorBerry |
|--------------|-------------|
| `calendars: [{ url, symbol }]` | `[[zones.X.calendars]]` blocks with `url`, `symbol` (also `maximum_number_of_days`, `fetch_interval` per calendar) |
| `defaultSymbol` | `symbol` |
| `maximumEntries`, `maximumNumberOfDays` | `maximum_entries`, `maximum_number_of_days` |
| `maxTitleLength` | `max_title_length` |
| `getRelative`, `urgency` | `get_relative`, `urgency` |
| `timeFormat: "relative"` / `"absolute"` | `time_format = "relative"` / `"absolute"` (`"dateheaders"` is not supported) |
| `dateFormat`, `fullDayEventDateFormat` | `date_format`, `full_day_event_date_format` (strftime) |
| `nextDaysRelative` | `next_days_relative` |
| `displaySymbol`, `hideDuplicates` | `display_symbol`, `hide_duplicates` |
| `fetchInterval` (ms) | `fetch_interval` (s) |
| `fade`, `fadePoint`, `tableClass` | `fade`, `fade_point`, `table_class` |

Colours per calendar, locations, custom events, broadcasting and end times are
not supported. Symbols are Font Awesome 7 icon names, the same version
MagicMirror² ships, so `calendar-days` or `cake-candles` look identical.

### MMM-ResRobot

| MMM-ResRobot | MirrorBerry `resrobot` |
|--------------|------------------------|
| `apiKey` | `api_key` |
| `routes: [{ from, to }]` | `[[zones.X.routes]]` blocks with `from`, `to` |
| `skipMinutes`, `maximumEntries`, `maximumDuration` | `skip_minutes`, `maximum_entries`, `maximum_duration` |
| `getRelative` | `get_relative` |
| `truncateAfter`, `truncateLineAfter` | `truncate_after`, `truncate_line_after` |
| `showTrack` | `show_track` |
| `coloredIcons`, `iconTable`, `colorTable` | `colored_icons`, `icon_table`, `color_table` |

MirrorBerry adds `provider = "trafiklab"` for Trafiklab's Realtime API, the
replacement for the deprecated ResRobot v2.1; real-time departure times;
`lines` and `destinations` filters; and `column_widths` to match MMM-ResRobot's
CSS column spacing.

### MMM-Namnsdag

| MMM-Namnsdag | MirrorBerry `namnsdag` |
|--------------|------------------------|
| `header` | `header` |
| `debug` | run with `python3 -m mirrorberry -v` |

MirrorBerry adds `single_line`, `separator`, `center_lines`, `text_class` and
`update_interval`. Names come from the same Svenska Dagar API.

## Date formats

MagicMirror² uses moment.js format tokens; MirrorBerry uses strftime codes.

| moment.js | strftime | Example (sv) |
|-----------|----------|--------------|
| `dddd` / `ddd` | `%A` / `%a` | söndag / sön |
| `MMMM` / `MMM` | `%B` / `%b` | september / sep |
| `D` / `DD` | `%-d` / `%d` | 7 / 07 |
| `M` / `MM` | `%-m` / `%m` | 9 / 09 |
| `YYYY` | `%Y` | 2026 |
| `HH:mm` | `%H:%M` | 08:05 |
| `h:mm A` | `%-I:%M %p` | 8:05 PM |
| `W` | `%-V` | 39 |
| `Do` | no equivalent; leave `date_format` unset for MagicMirror²'s "Okt 20:e" | |

Example: MagicMirror²'s `fullDayEventDateFormat: "ddd, DD MMM"` is
`full_day_event_date_format = "%a, %d %b"`.

## Matching your MagicMirror² screen exactly

`config.example.toml` was calibrated against a MagicMirror² screenshot (zoom 2 on
2560x1440, with a custom.css) and matches it to within a few pixels on 1080p. To
match your own:

1. Set `scale` from your MagicMirror² zoom and screen heights.
2. Measure text heights in a screenshot and set `[theme] sizes`: a digit is
   about 0.72 × the font size in Roboto Condensed.
3. Measure the spacing between lines for `line_heights`, and between modules for
   `stack_gap`.
4. Fine-tune table spacing with the widgets' `cell_padding` and `column_widths`.

Render with `python3 -m mirrorberry --screenshot out.png --size 1920x1080` to
compare without the Pi.
