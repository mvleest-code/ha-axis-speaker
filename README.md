# Axis Speaker for Home Assistant

Custom integration for AXIS network speakers over VAPIX, built and verified
against a real **AXIS C1410 Network Mini Speaker** (AXIS OS 11.11.192). It
replaces the ad hoc `rest_command` + `script` + `input_number` setup with a
proper config-flow-based integration: one device entry, auto-discovered
clip buttons, a volume control, and diagnostic sensors.

## What it does

- **Config flow** - add via Settings → Devices & Services → Add Integration
  → "Axis Speaker". Asks for host, username, password, and whether to
  verify the (usually self-signed) SSL certificate.
- **One button per clip already configured on the speaker** - clips are
  read dynamically from the device (`param.cgi?group=MediaClip`), so if you
  upload/rename clips on the speaker itself, they show up after an
  integration reload. No more hardcoding clip IDs in YAML.
- **Stop button.**
- **Volume number entity (0-100)** - used for the next clip play. The
  speaker has no persistent device-side volume; this mirrors the previous
  `input_number.axis_speaker_volume` behaviour.
- **Diagnostic sensors**: firmware version, and the connection status of
  the speaker's built-in MQTT client.
- **`axis_speaker.configure_mqtt` service** - points the speaker's own
  MQTT client at a broker (host/port/user/pass/TLS) and connects it. This
  wasn't exposed anywhere before; the device has a working MQTT client
  (confirmed via `getClientStatus`) that was just sitting unconfigured.

## What it does *not* do (yet)

- **SIP / two-way calling.** The device reports SIP capability
  (`Properties.API.SIP.SIP=yes`, VAPIX "Call service API" v2.2) and has a
  real hardware feature tied to it (an LED profile that lights up while a
  SIP call is active), so the hardware can clearly participate in a live
  call. No working VAPIX endpoint to dial/answer/hang up could be found
  under either `axis-cgi/` or `config/rest/` during development - this
  needs either Axis's account-gated VAPIX documentation for this exact
  product, or hands-on inspection of the device's own web UI network
  traffic while placing a test call. Not implemented to avoid guessing at
  an unverified API shape.
- **`configure_mqtt` is implemented but not exercised against a real
  broker.** The request payload mirrors the `config` object the device
  itself returns from `getClientStatus`, which gives reasonable confidence,
  but test it against a real (or throwaway) broker before depending on it.

## Installation

### As a HACS custom repository

1. HACS → the three-dot menu → Custom repositories.
2. Add this repo's URL, category "Integration".
3. Install "Axis Speaker", restart Home Assistant.

### Manual

Copy `custom_components/axis_speaker` into your Home Assistant `config/custom_components/` directory and restart.

## Migrating from the old YAML setup

The previous `rest_command.axis_speaker_play`/`axis_speaker_stop`,
`script.axis_speaker_play_clip`/`axis_speaker_stop`, and
`input_number.axis_speaker_volume` are **not removed** by installing this
integration - existing automations (PIR trigger, QR-tag trigger) keep
working unchanged. Migrate them to call the new `button.play_*` entities
whenever convenient, then remove the old YAML.
