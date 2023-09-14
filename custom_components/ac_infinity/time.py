import datetime
import logging
from datetime import time

from homeassistant.components.time import TimeEntity
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
    SETTING_KEY_SCHEDULED_END_TIME,
    SETTING_KEY_SCHEDULED_START_TIME,
)

DEFAULT_TIME = datetime.time(0, 0)

_LOGGER = logging.getLogger(__name__)


class ACInfinityPortTimeEntity(ACInfinityPortEntity, TimeEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, "")

        self._attr_native_value = self.__get_time_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.__get_time_value()

        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_native_value,
        )

    def __get_time_value(self):
        total_minutes = self.get_setting_value()

        # UIS stores a schedule value as minutes from midnight. A value of 0 is midnight.
        # Both 65535 and None could represent a value of "disabled"
        if total_minutes is not None and total_minutes // 60 <= 23:
            return datetime.time(hour=total_minutes // 60, minute=total_minutes % 60)

        return None

    async def async_set_value(self, value: time) -> None:
        total_minutes = None if value is None else (value.hour * 60) + value.minute
        await self.set_setting_value(total_minutes)
        _LOGGER.debug(
            "User updated value of %s.%s %s",
            self._attr_unique_id,
            self._data_key,
            self._attr_native_value,
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    select_entities = {
        SETTING_KEY_SCHEDULED_START_TIME: {"label": "Scheduled Start Time"},
        SETTING_KEY_SCHEDULED_END_TIME: {"label": "Scheduled End Time"},
    }

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for key, descr in select_entities.items():
                entities.append(
                    ACInfinityPortTimeEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        str(descr["label"]),
                    )
                )

    add_entities_callback(entities)
