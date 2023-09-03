import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ac_infinity import ACInfinity, ACInfinityDevice
from .const import (
    DEVICE_KEY_HUMIDITY,
    DEVICE_KEY_TEMPERATURE,
    DEVICE_KEY_VAPOR_PRESSURE_DEFICIT,
    DOMAIN,
)
from .utilities import get_device_property_unique_id

_LOGGER = logging.getLogger(__name__)


class ACInfinitySensorEntity(SensorEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        property_key: str,
        sensor_label: str,
        device_class: str,
        unit: str,
    ) -> None:
        self._acis = acis
        self._device = device
        self._property_key = property_key

        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = get_device_property_unique_id(device, property_key)
        self._attr_name = f"{device.device_name} {sensor_label}"

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = (
            self._acis.get_device_property(self._device.device_id, self._property_key)
            / 100
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    device_sensors = {
        DEVICE_KEY_TEMPERATURE: {
            "label": "Temperature",
            "deviceClass": SensorDeviceClass.TEMPERATURE,
            "unit": UnitOfTemperature.CELSIUS,
        },
        DEVICE_KEY_HUMIDITY: {
            "label": "Humidity",
            "deviceClass": SensorDeviceClass.HUMIDITY,
            "unit": PERCENTAGE,
        },
        DEVICE_KEY_VAPOR_PRESSURE_DEFICIT: {
            "label": "VPD",
            "deviceClass": SensorDeviceClass.PRESSURE,
            "unit": UnitOfPressure.KPA,
        },
    }

    await acis.update()
    devices = acis.get_all_device_meta_data()

    sensor_objects = []
    for device in devices:
        for key, descr in device_sensors.items():
            sensor_objects.append(
                ACInfinitySensorEntity(
                    acis,
                    device,
                    key,
                    descr["label"],
                    descr["deviceClass"],
                    descr["unit"],
                )
            )

    add_entities_callback(sensor_objects)
