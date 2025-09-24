# homeassistant-acinfinity

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

[![codecov](https://codecov.io/gh/dalinicus/homeassistant-acinfinity/graph/badge.svg?token=C4TMDAU344)](https://codecov.io/gh/dalinicus/homeassistant-acinfinity)
[![Tests](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml)

[![HACS/HASS](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml)
[![CodeQL](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml)


This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for [AC Infinity](https://acinfinity.com/) grow tent devices within the [Smart UIS Controller](https://acinfinity.com/smart-controllers/) cloud ecosystem.

- [Compatibility](#compatibility)
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual Installation](#manual-installation)
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
  - [General Configuration](#general-configuration)
  - [Enable / Disable Entities](#enable--disable-entities)
- [Entities](#entities)

# Compatibility

This integration is compatible with the following UIS Controllers

- Controller 69 Wifi
- Controller 69 Pro
- Controller 69 Pro+
- Controller AI+

This integration requires the controller be connected to Wi-fi, and thus is not compatible with bluetooth only devices such as Controller 67 or the base model of Controller 69, as they do not sync directly to the UIS Cloud

# Installation

## HACS

This integration is made available through the Home Assistant Community Store default feed.  Simply search for "AC Infinity" and install it directly from HACS.

Please see the [official HACS documentation](https://hacs.xyz) for information on how to install and use HACS.

## Manual Installation

Copy `custom_components/acinfinity` into your Home Assistant `$HA_HOME/config` directory, then restart Home Assistant

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

# Entities

For more information on what entities are made available by this integration, please visit the appropriate page below for your controller.

- [Smart Controllers (69 Series)](docs/SmartControllers.md)
- [AI Controllers (89 Series)](docs/AIControllers.md)
