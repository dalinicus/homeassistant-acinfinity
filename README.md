# AC Infinity Integration for Home Assistant

Early work in progress integration for AC Infinity Grow devices using the v69 Wifi Enabled Controller 

## Installation

### HACS
This integration is a very early work in progress, and only contains basic functionality.  As such, it is not in the default HACS repository.  You'll need to add this repository as a custom repository, and install it from there.

## Configuration

Once installed, install the integration as normal.  The only configuration you'll need to provide is your account's API key.

### Obtaining your API Key
In order to optain your API key, you'll need to intercept traffic from the AC Infinity app.  I recommend downloading Telerek's Fiddler and starting a free trial.  You can follow this guide to proxy your phone's internet traffic (The guide is for iOS, but the fiddler setup would be the same for android)

https://www.telerik.com/blogs/how-to-capture-ios-traffic-with-fiddler

Once you have your phone connected to fiddler, open the AC Infinity app (make sure you're already logged in).  Look for a request to www.acinfinityserver.com, open up the request headers, and find a value labeled "token".  This is your API token.

![Screen Shot](/images/fiddler.png)

## Data Available
This integration will create the following sensors for each AC Infinity Controller on your user account
- Temperature
- Humidity
- VPD
- Sensors for each of the ports on the controller
    - Power: Is there a device on that port
    - Intensity: Power supplied to the connected device

Integration is currently only read only, but triggering state changes on connected devices is planned.