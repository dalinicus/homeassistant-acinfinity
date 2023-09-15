import logging

from homeassistant.components.select import SelectEntity
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
from custom_components.ac_infinity.const import DOMAIN, SETTING_KEY_AT_TYPE

_LOGGER = logging.getLogger(__name__)


class ACInfinityPortSelectEntity(ACInfinityPortEntity, SelectEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        options: list[str],
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, "form-dropdown")

        self._attr_options = options
        self._attr_current_option = self.__get_option_from_setting_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_current_option = self.__get_option_from_setting_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_current_option updated to %s",
            self._attr_unique_id,
            self._attr_current_option,
        )

    async def async_select_option(self, option: str) -> None:
        index = self._attr_options.index(option)

        await self.set_setting_value(
            index + 1
        )  # data is 1 based.  Adjust from 0 based enum
        _LOGGER.debug(
            "User updated value of %s.%s to %s",
            self._attr_unique_id,
            self._data_key,
            option,
        )

    def __get_option_from_setting_value(self) -> str:
        option: int = self.get_setting_value()
        return self._attr_options[
            option - 1
        ]  # data is 1 based.  Adjust for 0 based enum


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordintator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    select_entities = {
        SETTING_KEY_AT_TYPE: {
            "label": "Mode",
            "options": [
                "Off",
                "On",
                "Auto",
                "Timer to On",
                "Timer to Off",
                "Cycle",
                "Schedule",
                "VPD",
            ],
        }
    }

    devices = coordintator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for key, descr in select_entities.items():
                entities.append(
                    ACInfinityPortSelectEntity(
                        coordintator,
                        device,
                        port,
                        key,
                        str(descr["label"]),
                        list[str](descr["options"]),
                    )
                )

    add_entities_callback(entities)
