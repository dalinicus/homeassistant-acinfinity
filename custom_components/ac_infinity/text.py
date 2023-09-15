import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortEntity,
)
from custom_components.ac_infinity.ac_infinity import (
    ACInfinityDevice,
    ACInfinityDevicePort,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_ACTIVE_TIMER_OFF,
    SETTING_KEY_ACTIVE_TIMER_ON,
)

_LOGGER = logging.getLogger(__name__)
TIMER_REGEX = r"^(0|[1-9]\d{0,2}|1[0-3]\d{2}|1440)$"  # timer minute values must be between 0 and 1440 (24 hours)


class ACInfinityPortTimerEntity(ACInfinityPortEntity, TextEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, "mdi:timer")

        self._attr_pattern = TIMER_REGEX
        self._attr_native_value = self.__get_timer_seting_value_as_str()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.__get_timer_seting_value_as_str()

        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )

    async def async_set_value(self, value: str) -> None:
        await self.set_setting_value(
            int(value) * 60
        )  # timers are stored as seconds. we configure them as minutes
        _LOGGER.debug(
            "User updated value of %s.%s to %s",
            self._attr_unique_id,
            self._data_key,
            value,
        )

    def __get_timer_seting_value_as_str(self):
        return str(
            self.get_setting_value(default=0) // 60
        )  # timers are stored as seconds. we configure them as minutes


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    select_entities = {
        SETTING_KEY_ACTIVE_TIMER_ON: {
            "label": "Minutes to On",
        },
        SETTING_KEY_ACTIVE_TIMER_OFF: {
            "label": "Minutes to Off",
        },
    }

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for key, descr in select_entities.items():
                entities.append(
                    ACInfinityPortTimerEntity(
                        coordinator, device, port, key, str(descr["label"])
                    )
                )

    add_entities_callback(entities)
