# homeassistant-acinfinity

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![HACS/HASS](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml)

This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for [AC Infinity](https://acinfinity.com/) grow tent devices within the [Smart UIS Controller](https://acinfinity.com/smart-controllers/) cloud ecosystem.

- [Compatibility](#compatibility)
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual Installation](#manual-installation)
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
  - [General Configuration](#general-configuration)
  - [Enable / Disable Entities](#enable--disable-entities)
- [Fan Entities](#fan-entities)
- [Diagnostics](#diagnostics)

# Compatibility

This integration is compatible with the following UIS Controllers

- Controller 69 Wifi
- Controller 69 Pro
- Controller 69 Pro+
- Controller AI+
- AIRTAP AI Register Booster Fans (Wi-Fi models)
- Room to Room Fan (AC-TWT6)

AIRTAP fans have no ports; each fan shows up as its own device with the fan's mode (`AI` / `Off` / `On`), on/off power
and current power on "port 0". Timer, cycle and schedule modes can still be set from the app but cannot be driven from Home Assistant.

Room to room fans also have no ports; their inside / outside temperatures, mode, fan speed, target temperature, timer,
power, direction, backlight and keypress sound are all attached to the fan's own device.

This integration requires the controller be connected to Wi-fi, and thus is not compatible with bluetooth only devices such as Controller 67 or the base model of Controller 69, as they do not sync directly to the UIS Cloud

# Installation

## HACS

This integration is made available through the Home Assistant Community Store default feed.  Simply search for "AC Infinity" and install it directly from HACS.

Please see the [official HACS documentation](https://hacs.xyz) for information on how to install and use HACS.

## Manual Installation

Copy `custom_components/ac_infinity` into your Home Assistant `$HA_HOME/config/custom_components` directory (creating it if it doesn't exist), so that `$HA_HOME/config/custom_components/ac_infinity/manifest.json` exists, then restart Home Assistant.

Copying the files only makes the integration available; it must still be added from the integration section of the Home Assistant settings as described in [Initial Setup](#initial-setup).

# Initial Setup
Add an integration entry as normal from integration section of the home assistant settings.  You'll need the following configuration items

- `Email`: The e-mail registered with your AC Infinity account.
- `Password`: The password for this account.

You will then be asked to select which entities you'd like enabled for each controller tied to your AC Infinity app.  Please see [Enable / Disable Entities](#enable--disable-entities) section for more information.

# Configuration

The following configurations can be modified via the configuration options dialog.

## General Configuration
- `Polling Interval (Seconds)`: The time between update calls to the AC Infinity API.  Minimum allowed polling interval is 5 seconds.
- `Update Password`: When provided, updates the password used to connect to your AC Infinity account.  Requires Home Assistant restart.

## Enable / Disable Entities

This integration can provide a large number of entities for each device to accommodate for various operation modes a device may be in. Those with multiple controllers may see potential performance issues due the number of entities added. 
You can enable or disable these entities as needed.  The following options are available, depending on the device type:

- `Sensors, Controls, and Settings`: All entities are enabled
- `Sensors and Settings`: Only sensors and settings are enabled
- `Sensors and Controls`: Only sensors and controls are enabled
- `Sensors Only`: Only sensors are enabled
- `Disable`: All entities are disabled

New controllers added to the AC Infinity app will be added with `Sensors Only` by default during the next home assistant restart.

Entities disabled after initial setup will no longer be provided by this integration, but will not be automatically removed from home assistant.  They can be cleaned up manually via `https://<your-ha-instance>/config/entities`.

# Fan Entities

Every port with controls enabled also gets a regular Home Assistant `fan` entity, so it can be used with fan cards, voice
assistants and the `fan.*` services.  Turning it on or off switches the port between `On` and `Off` mode, and the speed
percentage maps to the `On Power` level (10% per step).  Any other active mode (Auto, VPD, Schedule, ...) is shown as on.

Ports whose device type is set in the AC Infinity app to something that is not a fan (grow light, heater, pump, ...) do not
get a fan entity.

# Diagnostics

The raw data the integration last received from the AC Infinity API can be downloaded from the integration's page in
Home Assistant (`⋮` → `Download diagnostics`).  E-mail, password, MAC addresses and other identifiers are redacted.
Please attach this file when reporting an issue with a device.
