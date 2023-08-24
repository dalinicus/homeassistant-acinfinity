import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .acinfinity import ACInfinity
from .const import (
    DEVICE_LABEL,
    DEVICE_MAC_ADDR,
    DEVICE_PORT_INDEX,
    DEVICE_PORT_LABEL,
    DEVICE_PORTS,
    DOMAIN,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_INTENSITY,
    SENSOR_PORT_KEY_ONLINE,
)
from .helpers import assemble_port_sensor_key

_LOGGER = logging.getLogger(__name__)


class ACInfinitySensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        acis: ACInfinity,
        uuid: str,
        deviceName: str,
        macAddr: str,
        sensorKey: str,
        sensorLabel: str,
        deviceClass: str,
        unit: str,
    ) -> None:
        self._acis = acis
        self._macAddr = macAddr
        self._sensorKey = sensorKey

        self._attr_unique_id = f"aci_{uuid}_{macAddr}_{sensorKey}"
        self._attr_device_class = deviceClass
        self._attr_native_unit_of_measurement = unit
        self._attr_name = f"{deviceName} {sensorLabel}"

    async def async_update(self) -> None:
        await self._acis.update_data()
        self._attr_native_value = self._acis.get_sensor_data(
            self._macAddr, self._sensorKey
        )

    @property
    def native_value(self) -> StateType:
        return self._attr_native_value


class ACInfinityBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        acis: ACInfinity,
        uuid: str,
        deviceName: str,
        macAddr: str,
        sensorKey: str,
        sensorLabel: str,
        deviceClass: str,
        unit: str,
    ) -> None:
        self._acis = acis
        self._macAddr = macAddr
        self._sensorKey = sensorKey

        self._attr_unique_id = f"aci_{uuid}_{macAddr}_{sensorKey}"
        self._attr_device_class = deviceClass
        self._attr_native_unit_of_measurement = unit
        self._attr_name = f"{deviceName} {sensorLabel}"

    async def async_update(self) -> None:
        await self._acis.update_data()
        value = self._acis.get_sensor_data(self._macAddr, self._sensorKey)
        self._attr_is_on = value == 1

    @property
    def is_on(self) -> bool:
        return self._attr_is_on


class ACInfinityNumberSensor(NumberEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        acis: ACInfinity,
        uuid: str,
        deviceName: str,
        macAddr: str,
        sensorKey: str,
        sensorLabel: str,
        deviceClass: str,
        unit: str,
    ) -> None:
        self._acis = acis
        self._macAddr = macAddr
        self._sensorKey = sensorKey

        self._attr_unique_id = f"aci_{uuid}_{macAddr}_{sensorKey}"
        self._attr_device_class = deviceClass
        self._attr_native_unit_of_measurement = unit
        self._attr_name = f"{deviceName} {sensorLabel}"

    async def async_update(self) -> None:
        await self._acis.update_data()
        self._attr_native_value = self._acis.get_sensor_data(
            self._macAddr, self._sensorKey
        )

    @property
    def native_value(self) -> StateType:
        return self._attr_native_value


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    device_sensors = {
        SENSOR_KEY_TEMPERATURE: {
            "label": "Temperature",
            "entityClass": SensorEntity,
            "deviceClass": SensorDeviceClass.TEMPERATURE,
            "unit": UnitOfTemperature.CELSIUS,
            "perPort": False,
        },
        SENSOR_KEY_HUMIDITY: {
            "label": "Humidity",
            "entityClass": SensorEntity,
            "deviceClass": SensorDeviceClass.HUMIDITY,
            "unit": PERCENTAGE,
            "perPort": False,
        },
        SENSOR_KEY_VPD: {
            "label": "VPD",
            "entityClass": SensorEntity,
            "deviceClass": SensorDeviceClass.PRESSURE,
            "unit": UnitOfPressure.KPA,
            "perPort": False,
        },
        SENSOR_PORT_KEY_ONLINE: {
            "label": "Online",
            "entityClass": BinarySensorEntity,
            "deviceClass": BinarySensorDeviceClass.POWER,
            "unit": None,
            "perPort": True,
        },
        SENSOR_PORT_KEY_INTENSITY: {
            "label": "Intensity",
            "entityClass": NumberEntity,
            "deviceClass": NumberDeviceClass.POWER_FACTOR,
            "unit": None,
            "perPort": True,
        },
    }

    devices = await acis.get_registered_devices()

    sensor_objects = []
    for device in devices:
        for key, descr in device_sensors.items():
            sensor_objects.extend(
                __create_sensors(acis, config.unique_id, device, key, descr)
            )

    add_entities_callback(sensor_objects)


def __create_sensors(acis: ACInfinity, uuid, device, sensorKey, descr):
    if descr["perPort"]:
        sensors = []
        for port in device[DEVICE_PORTS]:
            sensors.append(
                __create_sensor(
                    acis,
                    uuid,
                    device,
                    assemble_port_sensor_key(port[DEVICE_PORT_INDEX], sensorKey),
                    descr["entityClass"],
                    f'{port[DEVICE_PORT_LABEL]} {descr["label"]}',
                    descr["deviceClass"],
                    descr["unit"],
                )
            )

        return sensors

    return [
        __create_sensor(
            acis,
            uuid,
            device,
            sensorKey,
            descr["entityClass"],
            descr["label"],
            descr["deviceClass"],
            descr["unit"],
        )
    ]


def __create_sensor(
    acis: ACInfinity,
    uuid,
    device,
    sensorKey,
    sensorClass,
    label,
    deviceClass,
    unit,
):
    if sensorClass == SensorEntity:
        return ACInfinitySensor(
            acis,
            uuid,
            device[DEVICE_LABEL],
            device[DEVICE_MAC_ADDR],
            sensorKey,
            label,
            deviceClass,
            unit,
        )
    if sensorClass == BinarySensorEntity:
        return ACInfinityBinarySensor(
            acis,
            uuid,
            device[DEVICE_LABEL],
            device[DEVICE_MAC_ADDR],
            sensorKey,
            label,
            deviceClass,
            unit,
        )
    if sensorClass == NumberEntity:
        return ACInfinityNumberSensor(
            acis,
            uuid,
            device[DEVICE_LABEL],
            device[DEVICE_MAC_ADDR],
            sensorKey,
            label,
            deviceClass,
            unit,
        )
