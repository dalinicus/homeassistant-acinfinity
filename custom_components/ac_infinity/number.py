import logging
from typing import Tuple

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortSettingEntity,
    ACInfinityPortTupleSettingEntity,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER,
    SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER,
    SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER,
    SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER_F,
    SETTING_KEY_AUTO_TEMP_LOW_TRIGGER,
    SETTING_KEY_AUTO_TEMP_LOW_TRIGGER_F,
    SETTING_KEY_CYCLE_DURATION_OFF,
    SETTING_KEY_CYCLE_DURATION_ON,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
    SETTING_KEY_TIMER_DURATION_TO_OFF,
    SETTING_KEY_TIMER_DURATION_TO_ON,
    SETTING_KEY_VPD_HIGH_TRIGGER,
    SETTING_KEY_VPD_LOW_TRIGGER,
)

from .ac_infinity import ACInfinityDevice, ACInfinityDevicePort

_LOGGER = logging.getLogger(__name__)


class ACInfinityPortNumberEntity(ACInfinityPortSettingEntity, NumberEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        icon: str,
        device_class: str,
        min_value: float,
        max_value: float,
        step_value: float,
        mode: str,
        data_factor: int,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)
        self._data_facotr = data_factor

        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step_value
        self._attr_mode = mode
        self._attr_device_class = device_class
        self._attr_native_value = self.__get_setting_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.__get_setting_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )

    async def async_set_native_value(self, value: int) -> None:
        await self.set_setting_value(value * self._data_facotr)
        _LOGGER.debug(
            "User updated value of %s.%s to %s",
            self._attr_unique_id,
            self._data_key,
            value,
        )

    def __get_setting_value(self):
        return self.get_setting_value() / self._data_facotr


class ACInfinityPortTempTriggerEntity(ACInfinityPortTupleSettingEntity, NumberEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        tuple_key: Tuple[str, str],
        label: str,
    ) -> None:
        super().__init__(coordinator, device, port, tuple_key, label, None)

        self._attr_native_min_value = 0
        self._attr_native_max_value = 90
        self._attr_native_step = 1
        self._attr_mode = NumberMode.AUTO
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_native_value, _ = self.get_setting_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value, _ = self.get_setting_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )

    async def async_set_native_value(self, value: int) -> None:
        f = round((value * 1.8) + 32, 0)
        await self.set_setting_value((value, int(f)))
        _LOGGER.debug(
            "User updated value of %s.%s to %s",
            self._attr_unique_id,
            self._data_key,
            value,
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    port_entities = {
        SETTING_KEY_ON_SPEED: {
            "label": "On Speed",
            "icon": "mdi:knob",
            "deviceClass": NumberDeviceClass.POWER_FACTOR,
            "min": 0,
            "max": 10,
            "step": 1,
            "mode": NumberMode.AUTO,
            "data_factor": 1,
        },
        SETTING_KEY_OFF_SPEED: {
            "label": "Off Speed",
            "icon": "mdi:knob",
            "deviceClass": NumberDeviceClass.POWER_FACTOR,
            "min": 0,
            "max": 10,
            "step": 1,
            "mode": NumberMode.AUTO,
            "data_factor": 1,
        },
        SETTING_KEY_TIMER_DURATION_TO_ON: {
            "label": "Minutes to On",
            "icon": None,  # default
            "deviceClass": NumberDeviceClass.DURATION,
            "min": 0,
            "max": 1440,
            "step": 1,
            "mode": NumberMode.BOX,
            "data_factor": 60,
        },
        SETTING_KEY_TIMER_DURATION_TO_OFF: {
            "label": "Minutes to Off",
            "icon": None,  # default
            "deviceClass": NumberDeviceClass.DURATION,
            "min": 0,
            "max": 1440,
            "step": 1,
            "mode": NumberMode.BOX,
            "data_factor": 60,
        },
        SETTING_KEY_CYCLE_DURATION_ON: {
            "label": "Cycle Minutes On",
            "icon": None,  # default
            "deviceClass": NumberDeviceClass.DURATION,
            "min": 0,
            "max": 1440,
            "step": 1,
            "mode": NumberMode.BOX,
            "data_factor": 60,
        },
        SETTING_KEY_CYCLE_DURATION_OFF: {
            "label": "Cycle Minutes Off",
            "icon": None,  # default
            "deviceClass": NumberDeviceClass.DURATION,
            "min": 0,
            "max": 1440,
            "step": 1,
            "mode": NumberMode.BOX,
            "data_factor": 60,
        },
        SETTING_KEY_VPD_LOW_TRIGGER: {
            "label": "VPD Low Trigger",
            "icon": "mdi:water-thermometer-outline",
            "deviceClass": NumberDeviceClass.PRESSURE,
            "min": 0,
            "max": 9.9,
            "step": 0.1,
            "mode": NumberMode.BOX,
            "data_factor": 10,
        },
        SETTING_KEY_VPD_HIGH_TRIGGER: {
            "label": "VPD High Trigger",
            "icon": "mdi:water-thermometer-outline",
            "deviceClass": NumberDeviceClass.PRESSURE,
            "min": 0,
            "max": 9.9,
            "step": 0.1,
            "mode": NumberMode.BOX,
            "data_factor": 10,
        },
        SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER: {
            "label": "VPD Low Trigger",
            "icon": "mdi:water-thermometer-outline",
            "deviceClass": NumberDeviceClass.PRESSURE,
            "min": 0,
            "max": 9.9,
            "step": 0.1,
            "mode": NumberMode.BOX,
            "data_factor": 10,
        },
        SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER: {
            "label": "VPD High Trigger",
            "icon": "mdi:water-thermometer-outline",
            "deviceClass": NumberDeviceClass.PRESSURE,
            "min": 0,
            "max": 9.9,
            "step": 0.1,
            "mode": NumberMode.BOX,
            "data_factor": 10,
        },
    }

    tuple_entities = {
        (SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER, SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER_F): {
            "label": "Auto High Temp Trigger",
        },
        (SETTING_KEY_AUTO_TEMP_LOW_TRIGGER, SETTING_KEY_AUTO_TEMP_LOW_TRIGGER_F): {
            "label": "Auto Low Temp Trigger",
        },
    }

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for key, descr in port_entities.items():
                entities.append(
                    ACInfinityPortNumberEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["icon"],
                        descr["deviceClass"],
                        descr["min"],
                        descr["max"],
                        descr["step"],
                        descr["mode"],
                        descr["data_factor"],
                    )
                )
            for tupleKey, descr in tuple_entities.items():
                entities.append(
                    ACInfinityPortTempTriggerEntity(
                        coordinator,
                        device,
                        port,
                        tupleKey,
                        descr["label"],
                    )
                )

    add_entities_callback(entities)
