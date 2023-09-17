import logging
from typing import Tuple

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortSettingEntity,
    ACInfinityPortTupleSettingEntity,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_CYCLE_DURATION_OFF,
    SETTING_KEY_CYCLE_DURATION_ON,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
    SETTING_KEY_TIMER_DURATION_TO_OFF,
    SETTING_KEY_TIMER_DURATION_TO_ON,
    SETTING_KEY_VPD_HIGH_ENABLED,
    SETTING_KEY_VPD_HIGH_TRIGGER,
    SETTING_KEY_VPD_LOW_ENABLED,
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


class ACInfinityPortNumberTupleEntity(ACInfinityPortTupleSettingEntity, NumberEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        tuple_key: Tuple[str, str],
        label: str,
        icon: str,
        device_class: str,
        min_value: float,
        max_value: float,
        step_value: float,
        mode: int,
        data_factor: int,
    ) -> None:
        super().__init__(coordinator, device, port, tuple_key, label, icon)
        self._data_factor = data_factor

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
        if value <= 0:
            (previous, _) = self.get_setting_value()
            await self.set_setting_value(
                (previous, 0)
            )  # update enabled to 0, leave trigger as is
        else:
            value_adjusted: int = self.__adjust_value_from_ha(value)
            await self.set_setting_value(
                (value_adjusted, 1)
            )  # update enabled to 1, update trigger to user value
        _LOGGER.debug(
            "User updated value of %s.%s to %s",
            self._attr_unique_id,
            self._data_key,
            value,
        )

    def __get_setting_value(self):
        (value, enabled) = self.get_setting_value()
        if not enabled:
            return 0
        return self.__adjust_value_from_data(value)

    def __adjust_value_from_data(self, value: float) -> float:
        return value / self._data_factor

    def __adjust_value_from_ha(self, value: float) -> int:
        return int(value * self._data_factor)


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
    }

    tuple_entities = {
        (SETTING_KEY_VPD_LOW_TRIGGER, SETTING_KEY_VPD_LOW_ENABLED): {
            "label": "VPD Low Trigger",
            "icon": "mdi:water-thermometer-outline",
            "deviceClass": NumberDeviceClass.PRESSURE,
            "min": 0,
            "max": 9.9,
            "step": 0.1,
            "mode": NumberMode.BOX,
            "data_factor": 10,
        },
        (SETTING_KEY_VPD_HIGH_TRIGGER, SETTING_KEY_VPD_HIGH_ENABLED): {
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
                    ACInfinityPortNumberTupleEntity(
                        coordinator,
                        device,
                        port,
                        tupleKey,
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

    add_entities_callback(entities)
