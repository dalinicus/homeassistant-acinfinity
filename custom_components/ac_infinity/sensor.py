import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityDeviceEntity,
    ACInfinityPortPropertyEntity,
    ACInfinityPortSettingEntity,
)
from custom_components.ac_infinity.ac_infinity import (
    ACInfinityDevice,
    ACInfinityDevicePort,
)

from .const import (
    DOMAIN,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_KEY_VPD,
    SENSOR_PORT_KEY_SPEAK,
    SENSOR_SETTING_KEY_SURPLUS,
)

_LOGGER = logging.getLogger(__name__)


class ACInfinitySensorEntity(ACInfinityDeviceEntity, SensorEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        data_key: str,
        label: str,
        device_class: str,
        unit: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device, data_key, label, icon)

        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = self.__get_property_value_correct_precision()

    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.__get_property_value_correct_precision()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )

    def __get_property_value_correct_precision(self):
        # device sensors are all integers representing float values with 2 digit decimal precision
        return self.get_property_value() / 100


class ACInfinityPortSensorEntity(ACInfinityPortPropertyEntity, SensorEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        device_class: str,
        unit: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)

        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = self.get_property_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.get_property_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )


class ACInfinityPortSettingSensorEntity(ACInfinityPortSettingEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        device_class: str,
        unit: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)

        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = self.get_setting_value(default=0)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.get_setting_value(default=0)
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

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
        }
    }

    port_setting_sensors = {
        SENSOR_SETTING_KEY_SURPLUS: {
            "label": "Remaining Time",
            "deviceClass": SensorDeviceClass.DURATION,
            "unit": UnitOfTime.SECONDS,
            "icon": None,  # default
        },
    }

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        # device sensors
        for key, descr in device_sensors.items():
            entities.append(
                ACInfinitySensorEntity(
                    coordinator,
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
                entities.append(
                    ACInfinityPortSensorEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["deviceClass"],
                        descr["unit"],
                        descr["icon"],
                    )
                )

            for key, descr in port_setting_sensors.items():
                entities.append(
                    ACInfinityPortSettingSensorEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["deviceClass"],
                        descr["unit"],
                        descr["icon"],
                    )
                )

    add_entities_callback(entities)
