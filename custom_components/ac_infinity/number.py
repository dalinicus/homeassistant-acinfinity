from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
)

from .ac_infinity import ACInfinity, ACInfinityDevice, ACInfinityDevicePort
from .utilities import get_device_port_property_name, get_device_port_property_unique_id


class ACInfinityPortNumberEntity(NumberEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        setting_key: str,
        sensor_label: str,
        device_class: str,
        min_value: int,
        max_value: int,
    ) -> None:
        self._acis = acis
        self._device = device
        self._port = port
        self._setting_key = setting_key

        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_device_info = port.device_info
        self._attr_device_class = device_class
        self._attr_unique_id = get_device_port_property_unique_id(
            device, port, setting_key
        )
        self._attr_name = get_device_port_property_name(device, port, sensor_label)

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = self._acis.get_device_port_setting(
            self._device.device_id, self._port.port_id, self._setting_key
        )

    async def async_set_native_value(self, value: int) -> None:
        await self._acis.set_device_port_setting(
            self._device.device_id, self._port.port_id, self._setting_key, value
        )
        self._attr_native_value = value


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    port_sesnors = {
        SETTING_KEY_ON_SPEED: {
            "label": "On Speed",
            "deviceClass": NumberDeviceClass.POWER_FACTOR,
            "min": 0,
            "max": 10,
        },
        SETTING_KEY_OFF_SPEED: {
            "label": "Off Speed",
            "deviceClass": NumberDeviceClass.POWER_FACTOR,
            "min": 0,
            "max": 10,
        },
    }

    await acis.update()
    devices = acis.get_all_device_meta_data()

    sensor_objects = []
    for device in devices:
        for port in device.ports:
            for key, descr in port_sesnors.items():
                sensor_objects.append(
                    ACInfinityPortNumberEntity(
                        acis,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["deviceClass"],
                        descr["min"],
                        descr["max"],
                    )
                )

    add_entities_callback(sensor_objects)
