import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortSettingEntity,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
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
        device_class: str,
        min_value: int,
        max_value: int,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, "mdi:knob")

        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_device_class = device_class
        self._attr_native_value = self.get_setting_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.get_setting_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )

    async def async_set_native_value(self, value: int) -> None:
        await self.set_setting_value(value)
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

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for key, descr in port_sesnors.items():
                entities.append(
                    ACInfinityPortNumberEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["deviceClass"],
                        descr["min"],
                        descr["max"],
                    )
                )

    add_entities_callback(entities)
