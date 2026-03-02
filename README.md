# Monoprice Blackbird Matrix (44568 / 39670 / legacy)

Home Assistant custom integration for **Monoprice Blackbird** matrix switches. Supports:

- **PN 44568** – 18G 8x8 HDMI 2.0 Matrix HDBaseT 150M (default **115200** baud, `!`-delimited ASCII commands)
- **PN 39670** – 4K 8x8 HDBaseT Matrix (9600 baud, `.`-delimited commands)
- **Legacy** – 4x4-style units via pyblackbird (serial or host)

## Install via HACS

1. In HACS → **Integrations** → **⋮** → **Custom repositories**
2. Add this URL (use **HTTPS**, not SSH):
   ```
   https://github.com/gbg108/blackbird-44568-hacs
   ```
3. Category: **Integration**
4. Click **Add**, then search for **Monoprice Blackbird Matrix Switch** and install.

**Note:** This repo uses a zip release (like [home-assistant-rivian](https://github.com/bretterer/home-assistant-rivian)). You must have at least one [GitHub Release](https://github.com/gbg108/blackbird-44568-hacs/releases) with an asset named `blackbird.zip`. See **Publishing a release** below.

After install, restart Home Assistant and set `model: 44568` (or `39670` / `legacy`) in your Blackbird `media_player` config (see below).

## Configuration

### 8x8 matrix (PN 44568)

Use `model: 44568` and the serial port. Default baud is **115200**. Example:

```yaml
media_player:
  - platform: blackbird
    port: /dev/tty-MonopriceBlackbird
    model: 44568
    # baud: 115200   # optional, default for 44568
    zones:
      1: { name: "Great Room" }
      # ... zones 2–8
    sources:
      1: { name: "Xbox" }
      # ... sources 2–8
```

### 8x8 matrix (PN 39670)

Use `model: 39670`; default baud is 9600. Optional `baud:` if you changed the unit’s baud rate.

### Legacy 4x4-style matrix

Omit `model` or set `model: legacy`. Same YAML as before; uses pyblackbird over serial or host.

```yaml
media_player:
  - platform: blackbird
    port: /dev/ttyUSB0
    # model: legacy   # optional, default
    zones: { ... }
    sources: { ... }
```

## Requirements

- **44568**: Serial port only; default **115200** 8N1. No extra Python deps.
- **39670**: Serial port only; default 9600 8N1. No extra Python deps.
- **Legacy**: `pyblackbird==0.6` (installed automatically). Serial or TCP host.

## Notes

- **44568** uses the protocol from the [PN 44568 manual](https://downloads.monoprice.com/files/manuals/44568_Manual_230712.pdf) (`s in x av out y!`, `r av out 0!`, `s hdmi y stream z!`, etc.).
- **39670** uses the [39670 RS-232 guide](https://downloads.monoprice.com/files/manuals/39670_RS-232_210210.pdf) (`OUTxx:yy`, `@OUTxx`, `$OUTxx`, `STA_VIDEO`, `STA_POUT`).
- This integration replaces the core **blackbird** integration when installed (same `domain`). To use core again, remove this custom integration.

## Publishing a release (for HACS)

HACS expects a release asset named `blackbird.zip`. From the repo root:

```bash
zip -r blackbird.zip custom_components/
```

Then create a new [GitHub Release](https://github.com/gbg108/blackbird-44568-hacs/releases/new) (tag e.g. `v1.0.0`), attach `blackbird.zip`, and publish. HACS will offer that release when users install or update.
