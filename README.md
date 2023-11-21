# homeassistant-acinfinity

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

[![codecov](https://codecov.io/gh/dalinicus/homeassistant-acinfinity/graph/badge.svg?token=C4TMDAU344)](https://codecov.io/gh/dalinicus/homeassistant-acinfinity)
[![Tests](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/tests.yaml)

[![HACS/HASS](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/validate.yaml)
[![Code Style](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/style.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/style.yaml)
[![CodeQL](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml/badge.svg)](https://github.com/dalinicus/homeassistant-acinfinity/actions/workflows/codeql.yaml)

This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for [AC Infinity](https://acinfinity.com/) grow tent devices within the [Smart UIS Controller](https://acinfinity.com/smart-controllers/) cloud ecosystem. 

## Compatabiliy

This integration is compatible with the following UIS Controllers

- Controller 69
- Controller 69 Pro
- Controller 69 Pro+

This integration is not compatible with bluetooth only devices such as Controller 67, as they do not sync to the UIS Cloud

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

## Data Available

This integration will create a device for each AC Infinity Controller on the configured user account. Each device will have the following sensors created.

- Humidity
- Air Temperature
- Vaper Pressure Deficit (VPD)

Sensors will also be created for each ***PORT*** on a controller, even if no device is attached.  The UIS protocol is device type agnostic, so each port will be treated the same regardless of what is plugged (or not plugged) into it.

- Status - Is there a device plugged in on that port
- Power - Current Power supplied to the connected device

![AC-Infinity](/images/ac-infinity-device.png)

## Controls

This integration adds a number of controls to modify settings via the AC Infinity API.  The following controls will be created for each ***PORT*** on a controller, even if no device is attached.  The UIS protocol is device type agnostic, so each port will be treated the same regardless of what is plugged (or not plugged) into it.  

Currently, controls can be added via the entities card.  The downside is that the controls will still be visible even if they are not applicable to the currently selected mode.  A custom lovelace card is in the works to show and hide controls based on selected mode.  ***Stay tuned!***

The mode can be changed via the mode control.  The following documentation is split into controls relevant to each mode.
- **On**: Device is always set to the on speed
- **Off**: Device is always set to the off speed
- **Auto**: Device toggled based on temperature and/or humidity triggers
- **Timer to On**: Device is turned on after a set duration
- **Timer to Off**: Device is turned off after a set duration
- **VPD**: Device is toggled based on VPD triggers
- **Cycle**: Device is toggled after set intervals
- **Schedule**: Device is toggled based on a schedule

### On Mode
- **On Speed**: The speed/intensity of the device while in on mode


### Off Mode
- **Off Speed**: The speed/intensity of the device while in off mode

### Auto Mode
- **On Speed**: The speed/intensity of the device while in on mode
- **Off Speed**: The speed/intensity of the device while in off mode
- **Auto High Temp Enabled**: Enable or disable high temp trigger while in Auto mode
- **Auto High Temp Trigger**: If trigger is enabled, device will be turned on if temp exceeds configured value.
- **Auto Low Temp Enabled**: Enable or disable low temp trigger while in Auto mode
- **Auto Low Temp Trigger**: If trigger is enabled, device will be turned on if temp drops below configured value.
- **Auto High Humidity Enabled**: Enable or disable high humidity trigger while in Auto mode
- **Auto High Humidity Trigger**: If trigger is enabled, device will be turned on if humidity exceeds configured value.
- **Auto Low Humidity Enabled**: Enable or disable low humidity trigger while in Auto mode
- **Auto Low Humidity Trigger**: If trigger is enabled, device will be turned on if humidity drops below configured value.

### Timer to On
- **On Speed**: The speed/intensity of the device while in on mode
- **Off Speed**: The speed/intensity of the device while in off mode
- **Minutes to On**: Device will be turned on after the configured number of minutes

### Timer to Off
- **On Speed**: The speed/intensity of the device while in on mode
- **Off Speed**: The speed/intensity of the device while in off mode
- **Minutes to On**: Device will be turned off after the configured number of minutes

### Cycle Mode
- **On Speed**: The speed/intensity of the device while in on mode
- **Off Speed**: The speed/intensity of the device while in off mode
- **Cycle Minutes On**: The amount of minutes the device will stay in on mode before switching to off mode
- **Cycle Minutes Off**: The amounto f minutes the device will stay in off mode before switching to on mode

### Schedule Mode
- **On Speed**: The speed/intensity of the device while in on mode
- **Off Speed**: The speed/intensity of the device while in off mode
- **Schedule Start Time**: The time that the device will switch into on mode daily
- **Schedule End Time**: The time that the device will switch into off mode daily

### VPD Mode
- **VPD High Enabled**: Enable or disable high VPD trigger while in VPD mode
- **VPD High Trigger**: If trigger is enabled, device will be turned on if VPD exceeds configured value.
- **VPD Low Enabled**: Enable or disable low VPD trigger while in VPD mode
- **VPD Low Trigger**: If trigger is enabled, device will be turned on if VPD drops below configured value.
