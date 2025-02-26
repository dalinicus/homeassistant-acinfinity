# homeassistant-acinfinity

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

[![codecov](https://codecov.io/gh/dalinicus/homeassistant-acinfinity/graph/badge.svg?token=C4TMDAU344)](https://codecov.io/gh/dalinicus/homeassistant-acinfinity)
[![Tests](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml)

[![HACS/HASS](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml)
[![Code Style](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/style.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/style.yaml)
[![CodeQL](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml)


This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for [AC Infinity](https://acinfinity.com/) grow tent devices within the [Smart UIS Controller](https://acinfinity.com/smart-controllers/) cloud ecosystem.

- [Compatibility](#compatibility)
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual Installation](#manual-installation)
- [Initial Setup](#initial-setup)
  - [Additional Configuration](#additional-configuration)
- [Terms](#terms)
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

![HACS-Install](/images/hacs-install.png)

Please see the [official HACS documentation](https://hacs.xyz) for information on how to install and use HACS.

## Manual Installation

Copy `custom_components/acinfinity` into your Home Assistant `$HA_HOME/config` directory, then restart Home Assistant

# Initial Setup
Add an integration entry as normal from integration section of the home assistant settings.  You'll need the following configuration items

- `Email`: The e-mail registered with your AC Infinity account.
- `Password`: The password for this account.

![Initial-Setup](/images/initial-setup.png)

## Additional Configuration

After adding an integration entry, the following additional configurations can be modified via the configuration options dialog.

- `Polling Interval (Seconds)`: The time between update calls to the AC Infinity API.  Minimum allowed polling interval is 5 seconds.
- `Update Password`: When provided, updates the password used to connect to your AC Infinity account.  Requires Home Assistant restart.

![Additional-Configuration](/images/additional-configuration.png)

# Entities

For more information on what entities are made available by this integration, please visit the appropriate page below for your controller.

- [Smart Controllers (69 Series)](docs/SmartControllers.md)
- [AI Controllers (89 Series)](docs/AIControllers.md)
