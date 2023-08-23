# homeassistant-acinfinity
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for [AC Infinity](https://acinfinity.com/) grow tent devices within the [Smart UIS Controller](https://acinfinity.com/smart-controllers/) ecosystem

## Data Available

This integration will create the following sensors for each AC Infinity Controller on the configured user account
- Humidity
- Air Temperature
- Vaper Pressure Deficit (VPD)

![Sensors](/images/controller-sensors.png)


Sensors will also be created for each ***PORT*** on a controller, even if no device is attached.  The UIS protocol is device type agnostic, so each port will be treated the same regardless of what is plugged (or not plugged) into it.

- Power - Is there a device on that port
- Intensity - Power supplied to the connected device

![Sensors](/images/port-sensors.png)

Integration is currently only read only, but triggering state changes on connected devices is planned.

## Installation

### HACS
Follow [this guide](https://hacs.xyz/docs/faq/custom_repositories/) to add this git repository as a custom HACS repository. Then install from HACS as normal.

### Manual Installation
Copy `custom_components/acinfinity` into your Home Assistant `$HA_HOME/config` directory, then restart Home Assistant

## Configuration

Once installed, install the integration as normal.  The only configuration you'll need to provide is your account's API key.

### Obtaining your API Key
In order to obtain your API key, you'll need to intercept traffic from the AC Infinity app.  I recommend downloading Telerek's Fiddler and starting a free trial.  You can follow this guide to proxy your phone's internet traffic (The guide is for iOS, but the fiddler setup would be the same for android)

https://www.telerik.com/blogs/how-to-capture-ios-traffic-with-fiddler

Once you have your phone connected to fiddler, open the AC Infinity app (make sure you're already logged in).  Look for a request to www.acinfinityserver.com, open up the request headers, and find a value labeled "token".  This is your API token.

![Screen Shot](/images/fiddler.png)
