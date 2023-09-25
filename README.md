# homeassistant-acinfinity

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

[![codecov](https://codecov.io/gh/dalinicus/homeassistant-acinfinity/graph/badge.svg?token=C4TMDAU344)](https://codecov.io/gh/dalinicus/homeassistant-acinfinity)
[![Tests](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml)

[![HACS/HASS](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml)
[![Code Style](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/style.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/style.yaml)
[![CodeQL](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml)

This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for [AC Infinity](https://acinfinity.com/) grow tent devices within the [Smart UIS Controller](https://acinfinity.com/smart-controllers/) ecosystem

## Data Available

This integration will create a device for each AC Infinity Controller on the configured user account. Each device will have the following sensors created.

- Humidity
- Air Temperature
- Vaper Pressure Deficit (VPD)

Sensors will also be created for each ***PORT*** on a controller, even if no device is attached.  The UIS protocol is device type agnostic, so each port will be treated the same regardless of what is plugged (or not plugged) into it.

- Status - Is there a device plugged in on that port
- Power - Current Power supplied to the connected device

![AC-Infinity](/images/ac-infinity-device.png)

Integration is currently only read only, but triggering state changes on connected devices is planned.

## Installation

### HACS

Follow [this guide](https://hacs.xyz/docs/faq/custom_repositories/) to add this git repository as a custom HACS repository. Then install from HACS as normal.

### Manual Installation

Copy `custom_components/acinfinity` into your Home Assistant `$HA_HOME/config` directory, then restart Home Assistant

## Initial Setup
Add an integration entry as normal from integration section of the home assistant settings.  You'll need the following configuration items

- **Email**: The e-mail registered with your AC Infinity account.
- **Password**: The password for this account.

![Initial-Setup](/images/initial-setup.png)

## Additional Configuration

After adding an integration entry, the following additional configurations can be modified via the configuration options dialog.

- **Polling Interval (Seconds)**: The time between update calls to the AC Infinity API.  Minimum allowed polling interval is 5 seconds.

![Additional-Configuration](/images/additional-configuration.png)
