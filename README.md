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
5. Restart Home Assistant.

Use **`platform: blackbird_matrix`** in your config (not `blackbird`) so Home Assistant uses this integration and accepts the `model` option.

## Configuration

### 8x8 matrix (PN 44568)

Use `model: 44568` and the serial port. Default baud is **115200**. Example:

```yaml
media_player:
  - platform: blackbird_matrix
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
  - platform: blackbird_matrix
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
- Use **`platform: blackbird_matrix`** so config validation accepts `model` and `baud`. The core **blackbird** integration remains available if you use `platform: blackbird` (without `model`).

## Repository layout

The **entire** HACS/repository content lives under this repository root (`blackbird-44568-hacs/`): `custom_components/blackbird_matrix/`, `hacs.json`, `README.md`, `info.md`, etc. There is no other copy of the integration in this repo. For local development, you can symlink your Home Assistant config’s `custom_components/blackbird_matrix` to `blackbird-44568-hacs/custom_components/blackbird_matrix` so the running instance uses this tree.

## Updating

In HACS, find **Monoprice Blackbird Matrix Switch**, click the three-dot menu, and choose **Update** (or **Redownload**). HACS installs directly from the `main` branch — no zip file or release asset is required.
