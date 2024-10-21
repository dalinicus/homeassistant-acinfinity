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
- [Entities](#entities)
  - [Terms](#terms)
  - [Controller Sensors](#controller-sensors)
  - [Controller Settings](#controller-settings)
    - [Sensor / VPD Calibration](#sensor--vpd-calibration)
    - [Outside Climate](#outside-climate)
  - [Device Sensors](#device-sensors)
  - [Device Controls](#device-controls)
    - [Global](#global)
    - [On Mode](#on-mode)
    - [Off Mode](#off-mode)
    - [Auto Mode](#auto-mode)
      - [Auto Settings Mode](#auto-setting-mode)
      - [Target Settings Mode](#target-settings-mode)
    - [Timer to On Mode](#timer-to-on-mode)
    - [Timer to Off Mode](#timer-to-off-mode)
    - [Cycle Mode](#cycle-mode)
    - [Schedule Mode](#schedule-mode)
    - [VPD Mode](#vpd-mode)
      - [Auto Settings Mode](#auto-setting-mode-1)
      - [Target Settings Mode](#target-settings-mode-1)
  - [Device Settings](#device-settings)
    - [Dynamic Response](#dynamic-response)
      - [Transition Mode](#transition-mode)
      - [Buffer Mode](#buffer-mode)
      - [Sunrise / Sunset](#sunrise--sunset-duration)

# Compatibility

This integration is compatible with the following UIS Controllers

- Controller 69 Wifi
- Controller 69 Pro
- Controller 69 Pro+

This integration requires the controller be connected to Wifi, and thus is not compatible with bluetooth only devices such as Controller 67 or the base model of Controller 69, as they do not sync directly to the UIS Cloud

# Installation

## HACS

This integration is made available through the Home Assistant Community Store default feed.  Simply search for "AC Infinity" and install it directly from HACS.

![HACS-Instal](/images/hacs-install.png)

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

Controller entities will be created for each AC Infinity Controller on the configured user account.

Device entities will be created for each ***PORT*** on each UIS controller, even if no device is attached to a given port.  The UIS protocol is device type agnostic, so each port will be treated the same regardless of what is plugged (or not plugged) into it.

## Terms
- `Sensor`: A read-only measurement entity, such as temperature or humidity.
- `Control`: An entity that can change the operational state of devices, such as individual mode selections, triggers, and timer schedules.
- `Setting`: An entity that can change controller/device settings.  These correspond to fields found in the Settings section of the Android/iOS app.

## Controller Sensors
Read Only sensors reported from the controller
- `Status`: Indicates if the controller is on and communicating with the AC Infinity API
- `Air Temperature`: The air temperature as reported by the air probe.
- `Humidity`: The humidity as reported by the air probe.
- `Vaper Pressure Deficit (VPD)`: Calculated VPD based on air probe temperature and humidity readings.

## Controller Settings
These entities correspond to fields found in the `Controller` tab of the device settings in the AC Infinity App.

### Sensor / VPD Calibration

- `Calibrate Temperature`:  Adjusts the temperature reading from the sensor probe, up to ±10C or ±20F
- `Calibrate Humidity`:  Adjusts the humidity reading from the sensor probe, up to ±10%
- `VPD Leaf Temperature Offset`:  Adjusts the leaf temperature in VPD calculation, up to ±10C or ±20F

<sub>
Note: If the preferred unit of temperature is changed on the UIS Controller, a reboot of Home Assistant is required to
update the user interface controls with the correct min/max values.  That being said, these fields should still continue
to function correctly when interfacing with the UIS API, even without a reboot.
</sub>

### Outside Climate

- `Outside Temperature`: Sets whether the exterior temperature is neutral to, higher, or lower than your interior space.
- `Outside Humidity`: Sets whether the exterior humidity is neutral to, higher, or lower than your interior space.

## Device Settings
These entities correspond to fields found in the `Port` tab of the device settings in the AC Infinity App.

- `Device Type`: The type of device plugged into the port (i.e. Fan, Grow Lights, etc... )
- `On Speed`: The device will run at this level when triggered ON
- `Off Speed`: The device will run at this level even when triggered OFF

### Dynamic Response

The dynamic response type can be changed via the `Dynamic Response` setting.
- `Transition`: UIS Devices will ramp up in levels when trigger to run in AUTO and VPD Modes (see Device Controls section below).  Set a transition threshold X.  For every multiple of X that the probe temperature, humidity and VPD has surpassed your trigger points, the UIS Device will increase by one level.
- `Buffer`: UIS and Outlet Devices will have a gap created on their temperature, humidity, and VPD triggers to prevent devices from turning on and off too frequently.

#### Transition Mode
- `Transition Temperature`: Set a transition threshold X.  For every multiple of X that the probe temperature has surpassed your trigger points, the UIS Device will increase by one level.
- `Transition Humidity`: Set a transition threshold X.  For every multiple of X that the probe humidity has surpassed your trigger points, the UIS Device will increase by one level.
- `Transition VPD`: Set a transition threshold X.  For every multiple of X that the probe VPD has surpassed your trigger points, the UIS Device will increase by one level.

&nbsp;&nbsp;&nbsp;&nbsp;<sub>[Official Documentation](https://acinfinity.com/pages/controller-programming/transition-setting.html)</sub>
#### Buffer Mode

- `Buffer Temperature`: Set a buffer X. Triggers won't deactivate until the temperature falls X degrees below the trigger temperature for high triggers, or X degrees above the trigger temperature for low triggers.
- `Buffer Humidity`: Set a buffer X. Triggers won't deactivate until the humidity falls X percentage points below the trigger humidity for high triggers, or X percentage points above the trigger humidity for low triggers.
- `Buffer VPD`: Set a buffer X. Triggers won't deactivate until the VPD falls X kPa below the trigger VPD for high triggers, or X kPa above the trigger VPD for low triggers.

&nbsp;&nbsp;&nbsp;&nbsp;<sub>[Official Documentation](https://acinfinity.com/pages/controller-programming/buffer-setting.html)</sub>

### Sunrise / Sunset Duration
Only valid for Grow Light devices operating in `Cycle` or `Schedule` mode.

- `Sunrise/Sunset Enabled`: Enables or disables simulating the sun when transitioning the light between on and off states.
- `Sunrise/Sunset Minute`: Sets the time it will take to fully brighten or dim your grow lights to simulate the sun.

## Device Sensors
Read Only sensors reported from each device
- `Status`: Indicates if a device plugged in and active on that port
- `State`: Indicates if the device is following the `On Power` or `Off Power` setting
- `Power`: Current power of the device, governed by the `On Power` and `Off Power` settings
- `Remaining Time`: Number of seconds until the next state change when using timer or schedule based modes.
- `Next State Change`: The timestamp of the next state change when using timer or schedule based modes, calculated based on the controller's configured time zone.

## Device Controls
Read/Write controls that define if a device runs in an ON or OFF state.  Each control is associated to a mode, and is only relevant when the device is operating in that mode.

The mode can be changed via the `Active Mode` control, which provides the following options.
- `On`: Device is always set to the on speed
- `Off`: Device is always set to the off speed
- `Auto`: Device toggled based on temperature and/or humidity triggers
- `Timer to On`: Device is turned on after a set duration
- `Timer to Off`: Device is turned off after a set duration
- `Cycle`: Device is toggled after set intervals
- `Schedule`: Device is toggled based on a schedule
- `VPD`: Device is toggled based on VPD triggers

### Global
These settings control the power level of a device when in a given trigger state, which is shared across all modes.
- `On Power`: Go to OFF MODE to set. The device will run at this level when triggered ON
- `Off Power`: Go to ON MODE to set.  The device will run at this level even when triggered OFF

### On Mode
Device is always set to the on speed . This mode has no unique controls.

### Off Mode
Device is always set to the off speed . This mode has no unique controls.

### Auto Mode
Device toggled based on temperature and/or humidity triggers.  This mode is split into two sub modes: Auto and Target.

- `Auto Settings Mode`: Swap between `Auto` and `Target` setting mode types.  `Target` mode is not valid for some device types.

#### Auto Setting Mode

- `High Temp Enabled`: Enable or disable high temp trigger while in Auto mode
- `High Temp Trigger`: If trigger is enabled, device will be turned on if temp exceeds configured value.
- `Low Temp Enabled`: Enable or disable low temp trigger while in Auto mode
- `Low Temp Trigger`: If trigger is enabled, device will be turned on if temp drops below configured value.
- `High Humidity Enabled`: Enable or disable high humidity trigger while in Auto mode
- `High Humidity Trigger`: If trigger is enabled, device will be turned on if humidity exceeds configured value.
- `Low Humidity Enabled`: Enable or disable low humidity trigger while in Auto mode
- `Low Humidity Trigger`: If trigger is enabled, device will be turned on if humidity drops below configured value.

#### Target Settings Mode

- `Target Temp Enabled`: Enabled or disable the target temperature target. *
- `Target Temp`: If enabled, target temperature to maintain. *
- `Target Humidity Enabled`: Enable or disable the target humidity target. **
- `Target Humidity`: If enabled, the target humidity to maintain. **

<sub>* Only valid for AC or Heater devices</sub>
<sub>** Only valid for Humidifier devices</sub>

### Timer to On Mode
Device is turned on after a set duration
- `Minutes to On`: Device will be turned on after the configured number of minutes

### Timer to Off Mode
Device is turned off after a set duration
- `Minutes to On`: Device will be turned off after the configured number of minutes

### Cycle Mode
Device is toggled after set intervals
- `Cycle Minutes On`: The amount of minutes the device will stay in on mode before switching to off mode
- `Cycle Minutes Off`: The amount of minutes the device will stay in off mode before switching to on mode

### Schedule Mode
Device is toggled based on a schedule
- `Schedule Start Time`: The time that the device will switch into on mode daily
- `Schedule End Time`: The time that the device will switch into off mode daily

### VPD Mode
Device is toggled based on VPD triggers

- `VPD Settings Mode`: Swap between `Auto` and `Target` setting mode types.  `Target` mode is not valid for some device types.

#### Auto Setting Mode

- `VPD High Enabled`: Enable or disable high VPD trigger while in VPD mode
- `VPD High Trigger`: If trigger is enabled, device will be turned on if VPD exceeds configured value.
- `VPD Low Enabled`: Enable or disable low VPD trigger while in VPD mode
- `VPD Low Trigger`: If trigger is enabled, device will be turned on if VPD drops below configured value.

#### Target Settings Mode

- `Target VPD Enabled`: Enable or disable the target VPD target *
- `Target VPD`: If enabled, the target VPD to maintain *

<sub>* Only valid for AC, Heater, and Humidifier devices</sub>
