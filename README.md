# Monoprice Blackbird Matrix (44568 / 39670 / legacy)

Home Assistant custom integration for **Monoprice Blackbird** matrix switches. Supports:

- **PN 44568** – 18G 8x8 HDMI 2.0 Matrix HDBaseT 150M (default **115200** baud, `!`-delimited ASCII commands)
- **PN 39670** – 4K 8x8 HDBaseT Matrix (9600 baud, `.`-delimited commands)
- **Legacy** – 4x4-style units via pyblackbird (serial or host)

## Current functionality

| Feature | Status |
|---|---|
| Power on / off per zone | ✅ Working |
| Current source display | ✅ Working — updates within ~10 seconds |
| Source selection via service call | ✅ Working (`media_player.select_source`) |
| Source selection via media-control card dropdown | ❌ Not working — HA frontend bug (see below) |

### Known issue: source dropdown does not work

The source selection dropdown inside the **media-control card** (and Mushroom media player card) does not trigger a source change. This is caused by a bug in the HA frontend's `ha-dropdown` component (`more-info-media_player.ts`) where the clicked item's value is not correctly propagated in the `@select` event handler. The backend integration is fully functional — the issue is entirely in the HA UI layer.

**Workaround:** use explicit button cards for source selection (see [Dashboard setup](#dashboard-setup) below). Each button calls `media_player.select_source` directly, which works reliably, and highlights when that source is active.

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

Add `blackbird_matrix: {}` to your `configuration.yaml` so the integration domain loads before the platform:

```yaml
blackbird_matrix: {}

media_player:
  - platform: blackbird_matrix
    port: /dev/tty-MonopriceBlackbird
    model: "44568"
    zones:
      1: { name: "Great Room" }
      2: { name: "Sunroom" }
      # ... zones up to 8
    sources:
      1: { name: "Xbox" }
      2: { name: "Xfinity" }
      3: { name: "Switch" }
      # ... sources up to 8
```

### 8x8 matrix (PN 44568)

Use `model: "44568"` and the serial port. Default baud is **115200**. The `model` value must be quoted as a string.

### 8x8 matrix (PN 39670)

Use `model: "39670"`; default baud is 9600. Optional `baud:` if you changed the unit's baud rate.

### Legacy 4x4-style matrix

Omit `model` or set `model: legacy`. Uses pyblackbird over serial or host.

```yaml
media_player:
  - platform: blackbird_matrix
    port: /dev/ttyUSB0
    # model: legacy   # optional, default
    zones: { ... }
    sources: { ... }
```

## Dashboard setup

Because the source dropdown in media-control cards is currently broken (see above), the recommended dashboard setup uses explicit button cards for source selection alongside the media-control card.

### Step 1 — Add template binary sensors to `configuration.yaml`

Add one binary sensor per zone × source. Each sensor is `on` when that zone's current source matches, which makes the corresponding button highlight automatically.

```yaml
template:
  - binary_sensor:
      # Example for one zone with three sources — repeat for each zone
      - name: "Great Room Xbox"
        unique_id: blackbird_great_room_xbox
        state: "{{ state_attr('media_player.great_room', 'source') == 'Xbox' }}"
      - name: "Great Room Xfinity"
        unique_id: blackbird_great_room_xfinity
        state: "{{ state_attr('media_player.great_room', 'source') == 'Xfinity' }}"
      - name: "Great Room Switch"
        unique_id: blackbird_great_room_switch
        state: "{{ state_attr('media_player.great_room', 'source') == 'Switch' }}"
```

### Step 2 — Add the Lovelace card

```yaml
type: vertical-stack
cards:
  - type: media-control
    entity: media_player.great_room
  - type: horizontal-stack
    cards:
      - type: button
        entity: binary_sensor.great_room_xbox
        name: Xbox
        icon: mdi:microsoft-xbox
        state_color: true
        tap_action:
          action: call-service
          service: media_player.select_source
          service_data:
            entity_id: media_player.great_room
            source: Xbox
      - type: button
        entity: binary_sensor.great_room_xfinity
        name: Xfinity
        icon: mdi:television-play
        state_color: true
        tap_action:
          action: call-service
          service: media_player.select_source
          service_data:
            entity_id: media_player.great_room
            source: Xfinity
      - type: button
        entity: binary_sensor.great_room_switch
        name: Switch
        icon: mdi:nintendo-switch
        state_color: true
        tap_action:
          action: call-service
          service: media_player.select_source
          service_data:
            entity_id: media_player.great_room
            source: Switch
```

The active source button lights up in your theme's primary color. Duplicate the card block for each zone, updating the entity IDs accordingly.

## Requirements

- **44568**: Serial port only; default **115200** 8N1. No extra Python deps beyond `pyserial`.
- **39670**: Serial port only; default 9600 8N1. No extra Python deps beyond `pyserial`.
- **Legacy**: `pyblackbird==0.6` (installed automatically). Serial or TCP host.

## Notes

- **44568** uses the protocol from the [PN 44568 manual](https://downloads.monoprice.com/files/manuals/44568_Manual_230712.pdf) (`s in x av out y!`, `r av out 0!`, `s hdmi y stream z!`, etc.).
- **39670** uses the [39670 RS-232 guide](https://downloads.monoprice.com/files/manuals/39670_RS-232_210210.pdf) (`OUTxx:yy`, `@OUTxx`, `$OUTxx`, `STA_VIDEO`, `STA_POUT`).
- Use **`platform: blackbird_matrix`** so config validation accepts `model` and `baud`. The core **blackbird** integration remains available if you use `platform: blackbird` (without `model`).

## Repository layout

The **entire** HACS/repository content lives under this repository root: `custom_components/blackbird_matrix/`, `hacs.json`, `README.md`. There is no other copy of the integration in this repo. For local development, symlink your Home Assistant config's `custom_components/blackbird_matrix` to `blackbird-44568-hacs/custom_components/blackbird_matrix`.

## Updating

In HACS, find **Monoprice Blackbird Matrix Switch**, click the three-dot menu, and choose **Update** (or **Redownload**). HACS installs directly from the `main` branch — no zip file or release asset is required.
