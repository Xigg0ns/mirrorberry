# Installation

MirrorBerry is written for a Raspberry Pi Zero W with a 1920x1080 HDMI screen,
but runs on any Raspberry Pi, and on a PC for development.

## 1. Prepare the Pi

Flash **Raspberry Pi OS Lite (32-bit)** with Raspberry Pi Imager. In the OS
customisation screen set the hostname (for example `mirrorberry`), your user,
Wi-Fi (the Zero W only has 2.4 GHz), your time zone, and enable SSH.

After the first boot, log in over SSH and install the packages:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y python3-pygame fonts-roboto-unhinted python3-recurring-ical-events git
```

| Package | Why |
|---------|-----|
| `python3-pygame` | drawing; use the apt package rather than `pip install pygame`, it's prebuilt for the Zero's ARMv6 CPU |
| `fonts-roboto-unhinted` | Roboto and Roboto Condensed, MagicMirror²'s fonts |
| `python3-recurring-ical-events` | the calendar widget (pulls in `python3-icalendar`) |
| `git` | to clone and update MirrorBerry |

For Swedish day and month names (`locale = "sv_SE.UTF-8"` in `config.toml`),
generate the locale once:

```bash
sudo sed -i 's/^# *sv_SE\.UTF-8/sv_SE.UTF-8/' /etc/locale.gen && sudo locale-gen
```

### Recommended system tweaks

Append to the single line in `/boot/firmware/cmdline.txt` (same line, separated
by spaces):

```
consoleblank=0 vt.global_cursor_default=0 video=HDMI-A-1:1920x1080@60
```

`consoleblank=0` stops the console from blanking the screen, and
`vt.global_cursor_default=0` hides the blinking cursor. `video=` forces the HDMI
mode even if the screen is off when the Pi boots; use `1280x720@60` if redraws
feel slow.

Turn off Wi-Fi power saving, which makes SSH laggy and drops connections on the
Zero W:

```bash
nmcli connection show                                  # find your Wi-Fi connection name
sudo nmcli connection modify "<name>" 802-11-wireless.powersave 2
```

Optional: if you don't use Bluetooth, add `dtoverlay=disable-bt` to
`/boot/firmware/config.txt` and run `sudo systemctl disable hciuart`.

Reboot after these changes.

## 2. Install MirrorBerry

```bash
git clone https://github.com/<you>/mirrorberry.git ~/mirrorberry
cd ~/mirrorberry
cp config.example.toml config.toml
nano config.toml
```

At a minimum, set your location for the weather, your Trafiklab API key and stop
for departures, and your calendar URLs, or remove the widgets you don't want.
[configuration.md](configuration.md) explains every setting.

`config.toml` is listed in `.gitignore`, so your API keys and private calendar
addresses are never committed, and `git pull` never overwrites your settings.

Try it:

```bash
python3 -m mirrorberry        # fullscreen on HDMI; Esc or q to quit (with a keyboard)
```

Over SSH, stop it with Ctrl+C. Started by hand, the text console may flicker
through; that goes away when it runs as a service.

## 3. Start at boot

```bash
sudo cp deploy/mirrorberry@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mirrorberry@$USER
```

The part after `@` is the Linux user whose home folder holds `~/mirrorberry`.
The service takes over `tty1`, the HDMI console, so the login prompt and cursor
can't draw over the display. Use SSH, or press Ctrl+Alt+F2 on a keyboard for a
local console.

Useful commands:

```bash
systemctl status mirrorberry@$USER          # running? last log lines
journalctl -u mirrorberry@$USER -f          # follow the log
journalctl -u mirrorberry@$USER -b          # everything since boot
sudo systemctl restart mirrorberry@$USER    # after changing config.toml
```

At startup the log lists which widget runs in each zone, for example
`Zones: TopLeft: weather + weather, TopRight: clock + calendar; empty: Center, …`.

## Updating

```bash
cd ~/mirrorberry
git pull
sudo systemctl restart mirrorberry@$USER
```

New settings get sensible defaults, so an existing `config.toml` keeps working.
Compare with `config.example.toml` to see what's new.

## Display backends

`backend` in `[display]`:

- `auto` (default): `fbdev` on a Pi without a desktop, an SDL window elsewhere.
- `fbdev`: draws in memory and copies frames to `/dev/fb0`. No GPU involved;
  the reliable choice on a Pi Zero W.
- `sdl`: lets SDL drive the screen through KMS/DRM and the GPU. Needs
  `sudo apt install libegl1 libgles2`. On the Zero W this currently gives a
  black screen with only a mouse cursor, so it's for other hardware.

## Troubleshooting

**The Pi boots to a login prompt.** The service is not enabled or is crashing.
`systemctl status mirrorberry@$USER` shows which, and the journal shows the
error.

**A zone shows a message instead of its widget.** A setting in `config.toml` is
wrong (a misspelt option, a missing API key, a bad value). The message says
which zone, widget and setting; the rest of the screen keeps working. The same
message is in the log.

**"Autentisering misslyckades" (Authentication failed) on the departures.**
Trafiklab rejected the API key. Check that the key is for the API you chose
with `provider`: ResRobot and the Realtime API have separate keys.

**"För många förfrågningar" (Too many requests).** The API key's quota is used
up. Increase `update_interval` or use fewer routes; MirrorBerry retries later.

**The whole screen shows coloured blocks.** MirrorBerry found no
`config.toml` and shows its placeholder layout. Copy `config.example.toml` to
`config.toml`.

**Days and months are in English.** The locale in `[general]` isn't installed;
run the `locale-gen` step above. `locale -a` lists installed locales.

**Text is in the wrong font.** Install `fonts-roboto-unhinted`; the log warns
about missing fonts.

**Old data after a network outage.** Widgets keep showing the last good data
while downloads fail, and retry after 1 minute, then 2, 4, … up to their normal
interval. The log shows each failure.

**Checking redraw speed.** Stop the service and run `python3 -m mirrorberry -v`
to log how long each redraw takes.

## Command line

```
python3 -m mirrorberry [options]

  -c, --config PATH     config file (default: config.toml next to the mirrorberry package)
  --windowed            run in a window instead of fullscreen
  --size WxH            window size, e.g. 1280x720 (implies --windowed)
  --backend auto|fbdev|sdl
                        override [display] backend
  --screenshot PNG      render one frame to an image and exit (no screen needed)
  -v, --verbose         debug logging
```

## Developing on a PC

```bash
pip install pygame recurring-ical-events
python3 -m mirrorberry --size 1280x720       # resizable window
python3 -m mirrorberry --screenshot out.png  # one frame, no screen needed
```

For the intended look, install the Roboto fonts at the Debian/Ubuntu location
(`sudo apt install fonts-roboto-unhinted`); elsewhere text falls back to pygame's
default font. See [development.md](development.md) for writing widgets.
