import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ac_infinity import ACInfinity, ACInfinityDevice, ACInfinityDevicePort
from .const import (
    DEVICE_KEY_HUMIDITY,
    DEVICE_KEY_TEMPERATURE,
    DEVICE_KEY_VAPOR_PRESSURE_DEFICIT,
    DEVICE_PORT_KEY_ONLINE,
    DEVICE_PORT_KEY_SPEAK,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class ACInfinitySensor(SensorEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        uuid: str,
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

        self._attr_unique_id = f"aci_{uuid}_{device.mac_addr}_{property_key}"
        self._attr_name = f"{device.device_name} {sensor_label}"

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_native_value = self._acis.get_device_property(
            self._device.device_id, self._property_key
        )

class ACInfinityPortSensor(SensorEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        uuid: str,
        property_key: str,
        sensor_label: str,
        device_class: str,
        unit: str,
    ) -> None:
        self._acis = acis
        self._device = device
        self._port = port

        self._property_key = property_key
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

        self._attr_unique_id = f"aci_{uuid}_{device.mac_addr}_port_{port.port_id}_{property_key}"
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
        DEVICE_KEY_TEMPERATURE: {
            "label": "Temperature",
            "entityClass": SensorEntity,
            "deviceClass": SensorDeviceClass.TEMPERATURE,
            "unit": UnitOfTemperature.CELSIUS,
            "perPort": False,
        },
        DEVICE_KEY_HUMIDITY: {
            "label": "Humidity",
            "entityClass": SensorEntity,
            "deviceClass": SensorDeviceClass.HUMIDITY,
            "unit": PERCENTAGE,
            "perPort": False,
        },
        DEVICE_KEY_VAPOR_PRESSURE_DEFICIT: {
            "label": "VPD",
            "entityClass": SensorEntity,
            "deviceClass": SensorDeviceClass.PRESSURE,
            "unit": UnitOfPressure.KPA,
            "perPort": False,
        },
        DEVICE_PORT_KEY_ONLINE: {
            "label": "Online",
            "entityClass": BinarySensorEntity,
            "deviceClass": BinarySensorDeviceClass.POWER,
            "unit": None,
            "perPort": True,
        },
        DEVICE_PORT_KEY_SPEAK: {
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


def __create_sensors(acis: ACInfinity, uuid, device_id, sensorKey, descr):
    if descr["perPort"]:
        sensors = []
        for port in acis.get_device_port_ids(device_id):
            sensors.append(
                __create_sensor(
                    acis,
                    uuid,
                    device_id,
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
    device_id,
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

def __assemble_port_sensor_key(port_id: int, sensor_key: str):
    return f"{SENSOR_PORT_PREFIX}_{portNumber}_{sensorKey}"
