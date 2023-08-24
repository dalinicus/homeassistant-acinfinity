from datetime import timedelta

from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import Throttle

from .client import ACInfinityClient
from .const import (
    DEVICE_LABEL,
    DEVICE_MAC_ADDR,
    DEVICE_PORT_INDEX,
    DEVICE_PORT_LABEL,
    DEVICE_PORTS,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_INTENSITY,
    SENSOR_PORT_KEY_ONLINE,
)
from .helpers import assemble_port_sensor_key


class ACInfinity:
    MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

    def __init__(self, email: str, password: str) -> None:
        self._client = ACInfinityClient(email, password)
        self._data: dict = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self):
        try:
            if not self._client.is_logged_in():
                await self._client.login()

            devices = {}
            for device in await self._client.get_all_device_info():
                macAddr = device["devMacAddr"]

                deviceObj = {
                    SENSOR_KEY_TEMPERATURE: device["deviceInfo"]["temperature"] / 100,
                    SENSOR_KEY_HUMIDITY: device["deviceInfo"]["humidity"] / 100,
                    SENSOR_KEY_VPD: device["deviceInfo"]["vpdnums"] / 100,
                }

                for portDevice in device["deviceInfo"]["ports"]:
                    portNum = portDevice["port"]
                    deviceObj[
                        assemble_port_sensor_key(portNum, SENSOR_PORT_KEY_ONLINE)
                    ] = portDevice["online"]
                    deviceObj[
                        assemble_port_sensor_key(portNum, SENSOR_PORT_KEY_INTENSITY)
                    ] = portDevice["speak"]

                devices[macAddr] = deviceObj
            self._data = devices
        except Exception:
            raise UpdateFailed from Exception

    async def get_registered_devices(self):
        devices = []
        for device in await self._client.get_all_device_info():
            deviceObj = {
                DEVICE_MAC_ADDR: device["devMacAddr"],
                DEVICE_LABEL: device["devName"],
            }

            ports = []
            for portDevice in device["deviceInfo"]["ports"]:
                ports.append(
                    {
                        DEVICE_PORT_INDEX: portDevice["port"],
                        DEVICE_PORT_LABEL: portDevice["portName"],
                    }
                )
            deviceObj[DEVICE_PORTS] = ports
            devices.append(deviceObj)
        return devices

    def get_sensor_data(self, macAddr: str, sensorKey: str):
        if macAddr in self._data:
            return self._data[macAddr][sensorKey]
        return None
