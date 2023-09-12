import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ac_infinity import ACInfinity, ACInfinityDevice, ACInfinityDevicePort
from .const import (
    DOMAIN,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_SPEAK,
    SENSOR_SETTING_KEY_SURPLUS,
)
from .utilities import (
    get_device_port_property_name,
    get_device_port_property_unique_id,
    get_device_property_name,
    get_device_property_unique_id,
)

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
        icon: str,
    ) -> None:
        self._acis = acis
        self._device = device
        self._property_key = property_key

        self._attr_device_info = device.device_info
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = get_device_property_unique_id(device, property_key)
        self._attr_name = get_device_property_name(device, sensor_label)
        self._attr_icon = icon

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = (
            self._acis.get_device_property(self._device.device_id, self._property_key)
            / 100  # device sensors are all integers representing float values with 2 digit decimal precision
        )


class ACInfinityPortSensorEntity(SensorEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        property_key: str,
        sensor_label: str,
        device_class: str,
        unit: str,
        icon: str,
    ) -> None:
        self._acis = acis
        self._device = device
        self._port = port
        self._property_key = property_key

        self._attr_device_info = port.device_info
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = get_device_port_property_unique_id(
            device, port, property_key
        )
        self._attr_name = get_device_port_property_name(device, port, sensor_label)
        self._attr_icon = icon

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = self._acis.get_device_port_property(
            self._device.device_id, self._port.port_id, self._property_key
        )


class ACInfinityPortSettingSensorEntity(ACInfinityPortSensorEntity):
    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = self._acis.get_device_port_setting(
            self._device.device_id,
            self._port.port_id,
            self._property_key,
            default_value=0,
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    device_sensors = {
        SENSOR_KEY_TEMPERATURE: {
            "label": "Temperature",
            "deviceClass": SensorDeviceClass.TEMPERATURE,
            "unit": UnitOfTemperature.CELSIUS,
            "icon": None,  # default
        },
        SENSOR_KEY_HUMIDITY: {
            "label": "Humidity",
            "deviceClass": SensorDeviceClass.HUMIDITY,
            "unit": PERCENTAGE,
            "icon": None,  # default
        },
        SENSOR_KEY_VPD: {
            "label": "VPD",
            "deviceClass": SensorDeviceClass.PRESSURE,
            "unit": UnitOfPressure.KPA,
            "icon": None,  # default
        },
    }

    port_sensors = {
        SENSOR_PORT_KEY_SPEAK: {
            "label": "Current Speed",
            "deviceClass": SensorDeviceClass.POWER_FACTOR,
            "unit": None,
            "icon": "mdi:speedometer",
            "isSettingSensor": False,
        },
        SENSOR_SETTING_KEY_SURPLUS: {
            "label": "Remaining Time",
            "deviceClass": SensorDeviceClass.DURATION,
            "unit": UnitOfTime.SECONDS,
            "icon": None,  # default
            "isSettingSensor": True,
        },
    }

    await acis.update()
    devices = acis.get_all_device_meta_data()

    sensor_objects = []
    for device in devices:
        # device sensors
        for key, descr in device_sensors.items():
            sensor_objects.append(
                ACInfinitySensorEntity(
                    acis,
                    device,
                    key,
                    descr["label"],
                    descr["deviceClass"],
                    descr["unit"],
                    descr["icon"],
                )
            )

        # port sensors
        for port in device.ports:
            for key, descr in port_sensors.items():
                if descr["isSettingSensor"]:
                    sensor_objects.append(
                        ACInfinityPortSettingSensorEntity(
                            acis,
                            device,
                            port,
                            key,
                            descr["label"],
                            descr["deviceClass"],
                            descr["unit"],
                            descr["icon"],
                        )
                    )
                else:
                    sensor_objects.append(
                        ACInfinityPortSensorEntity(
                            acis,
                            device,
                            port,
                            key,
                            descr["label"],
                            descr["deviceClass"],
                            descr["unit"],
                            descr["icon"],
                        )
                    )

    add_entities_callback(sensor_objects)
