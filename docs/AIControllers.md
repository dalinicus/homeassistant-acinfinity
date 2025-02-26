
# AI Controller Entities

- [Terms](#terms)
- [Controller Sensors](#controller-sensors)
- [Sensor Sensors](#sensor-sensors)
  - [Controller Sensor Probe (AC-SPC24)](#controller-sensor-probe-ac-spc24)
  - [CO2 + Light Sensor (AC-COS3)](#co2--light-sensor-ac-cos3)
- [Device Sensors](#device-sensors)

The below section applies to the 89 series of AI enabled controllers. Only Read-Only Sensors are supported; Read-Write controls will be added over time in future releases.

- UIS Controller AI+ (CTR89Q)

Controller entities will be created for each AC Infinity Controller on the configured user account.

Sensor entities will be created for each sensor plugged into the UIS controller.

Device entities will be created for each ***PORT*** on each UIS controller, even if no device is attached to a given port.  The UIS protocol is device type agnostic, so each port will be treated the same regardless of what is plugged (or not plugged) into it.

# Controller Sensors
Read-Only sensors reported from the controller
- `Status`: Indicates if the controller is on and communicating with the AC Infinity API
- `Air Temperature`: The air temperature as reported by the air probe.
- `Humidity`: The humidity as reported by the air probe.
- `Vaper Pressure Deficit (VPD)`: Calculated VPD based on air probe temperature and humidity readings.

# Sensor Sensors
Read-Only sensors reported by sensors plugged into the sensor ports on the controller, grouped by supported sensor device

## Controller Sensor Probe (AC-SPC24)
- `Air Temperature`: The air temperature as reported by the air probe.
- `Humidity`: The humidity as reported by the air probe.
- `Vaper Pressure Deficit (VPD)`: Calculated VPD based on air probe temperature and humidity readings.

## CO2 + Light Sensor (AC-COS3)
- `CO2 Levels`: CO2 measurement in parts per million.
- `Light Levels`: A percentage representation of how "on" the light is, with 100% being fully on.

# Device Sensors
Read-Only sensors reported from each device
- `Status`: Indicates if a device plugged in and active on that port
- `State`: Indicates if the device is following the `On Power` or `Off Power` setting
- `Power`: Current power of the device, governed by the `On Power` and `Off Power` settings
- `Remaining Time`: Number of seconds until the next state change when using timer or schedule based modes.
- `Next State Change`: The timestamp of the next state change when using timer or schedule based modes, calculated based on the controller's configured time zone.
