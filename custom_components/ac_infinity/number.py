from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity.const import (
    DEVICE_PORT_KEY_SPEAK,
    DOMAIN,
)

from .ac_infinity import ACInfinity, ACInfinityDevice, ACInfinityDevicePort
from .utilities import get_device_port_property_unique_id

class ACInfinityPortNumberEntity(NumberEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        property_key: str,
        sensor_label: str,
        device_class: str,
        min_value: int,
        max_value: int
    ) -> None:
        self._acis = acis
        self._device = device
        self._port = port
        self._property_key = property_key

        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_device_class = device_class
        self._attr_unique_id = get_device_port_property_unique_id(device, port, property_key)
        self._attr_name = f"{device.device_name} {port.port_name} {sensor_label}"

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = self._acis.get_device_port_property(
            self._device.device_id, self._port.port_id, self._property_key
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    device_sensors = {
        DEVICE_PORT_KEY_SPEAK: {
            "label": "Intensity",
            "deviceClass": NumberDeviceClass.POWER_FACTOR,
            "min": 0,
            "max": 10
        },
    }

    await acis.update()
    devices = acis.get_all_device_meta_data()

    sensor_objects = []
    for device in devices:
        for port in device.ports:
            for key, descr in device_sensors.items():
                sensor_objects.append(
                    ACInfinityPortNumberEntity(
                        acis,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["deviceClass"],
                        descr["min"],
                        descr["max"]
                    )
                )

    add_entities_callback(sensor_objects)
