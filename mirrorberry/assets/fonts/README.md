# Bundled icon fonts

| File | Font | License |
|------|------|---------|
| `weathericons-regular-webfont.ttf` | [Weather Icons](https://github.com/erikflowers/weather-icons) by Erik Flowers, the set MagicMirror uses | SIL OFL 1.1, see `WeatherIcons-OFL.txt` |
| `fa-solid-900.ttf` | [Font Awesome Free 7.3.1](https://fontawesome.com) Solid, the version MagicMirror ships: calendar symbols, transport icons | Font: SIL OFL 1.1; icons: CC BY 4.0, see `FontAwesome-LICENSE.txt` |

`fa-solid-names.json` maps Font Awesome icon names to codepoints (from Font Awesome's CSS),
so `symbol = "calendar-check"` works as in MagicMirror's config. Font Awesome 7 is only
published as WOFF2; `fa-solid-900.ttf` is that file unpacked to TTF with fontTools (same
glyphs and tables, only the container changed), because not every SDL_ttf build reads WOFF2.
Weather Icons is unmodified.
