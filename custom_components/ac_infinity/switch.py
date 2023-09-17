import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortSettingEntity,
)
from custom_components.ac_infinity.ac_infinity import (
    ACInfinityDevice,
    ACInfinityDevicePort,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED,
    SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED,
    SETTING_KEY_AUTO_TEMP_HIGH_ENABLED,
    SETTING_KEY_AUTO_TEMP_LOW_ENABLED,
    SETTING_KEY_SCHEDULED_END_TIME,
    SETTING_KEY_SCHEDULED_START_TIME,
    SETTING_KEY_VPD_HIGH_ENABLED,
    SETTING_KEY_VPD_LOW_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

DISABLED_VALUE = 65535  # Disabled
MIDNIGHT_VALUE = 0  # 12:00am
EOD_VALUE = 1439  # 11:59pm


class ACInfinityPortSwitchEntity(ACInfinityPortSettingEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        icon: str | None,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)

        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_is_on = self.get_setting_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.get_setting_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_is_on,
        )

    async def async_turn_on(self) -> None:
        await self.set_setting_value(1)
        _LOGGER.debug(
            "User switched %s.%s to On",
            self._attr_unique_id,
            self._data_key,
        )

    async def async_turn_off(self) -> None:
        await self.set_setting_value(0)
        _LOGGER.debug(
            "User switched %s.%s to Off",
            self._attr_unique_id,
            self._data_key,
        )


class ACInfinityPortScheduleSwitchEntity(ACInfinityPortSettingEntity):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        icon: str | None,
        init_value: int,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)
        self._init_value = init_value

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.__get_setting_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_native_value updated to %s",
            self._attr_unique_id,
            self._attr_is_on,
        )

    async def async_turn_on(self) -> None:
        await self.set_setting_value(self._init_value)
        _LOGGER.debug(
            "User switched %s.%s to On",
            self._attr_unique_id,
            self._data_key,
        )

    async def async_turn_off(self) -> None:
        await self.set_setting_value(DISABLED_VALUE)
        _LOGGER.debug(
            "User switched %s.%s to Off",
            self._attr_unique_id,
            self._data_key,
        )

    def __get_setting_value(self) -> bool:
        return self.get_setting_value(default=DISABLED_VALUE) <= EOD_VALUE


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""
    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    port_entities = {
        SETTING_KEY_VPD_HIGH_ENABLED: {
            "label": "VPD High Enabled",
            "icon": None,  # default
        },
        SETTING_KEY_VPD_LOW_ENABLED: {
            "label": "VPD Low Enabled",
            "icon": None,  # default
        },
        SETTING_KEY_AUTO_TEMP_HIGH_ENABLED: {
            "label": "Auto High Temp Enabled",
            "icon": None,  # default
        },
        SETTING_KEY_AUTO_TEMP_LOW_ENABLED: {
            "label": "Auto Low Temp Enabled",
            "icon": None,  # default
        },
        SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED: {
            "label": "Auto Humidity High Enabled",
            "icon": None,  # default
        },
        SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED: {
            "label": "Auto Humidity Low Enabled",
            "icon": None,  # default
        },
    }

    schedule_entities = {
        SETTING_KEY_SCHEDULED_START_TIME: {
            "label": "Schedule Start Enabled",
            "icon": None,  # default
            "init_value": MIDNIGHT_VALUE,
        },
        SETTING_KEY_SCHEDULED_END_TIME: {
            "label": "Schedule End Enabled",
            "icon": None,  # default
            "init_value": EOD_VALUE,
        },
    }

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for device in devices:
        for port in device.ports:
            for key, descr in port_entities.items():
                entities.append(
                    ACInfinityPortSwitchEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        str(descr["label"]),
                        descr["icon"],
                    )
                )
            for schKey, schDescr in schedule_entities.items():
                entities.append(
                    ACInfinityPortScheduleSwitchEntity(
                        coordinator,
                        device,
                        port,
                        schKey,
                        str(schDescr["label"]),
                        str(schDescr["icon"]),
                        int(schDescr["init_value"] or 0),
                    )
                )

    add_entities_callback(entities)
