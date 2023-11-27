import logging
from dataclasses import dataclass

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
)
from custom_components.ac_infinity.ac_infinity import (
    ACInfinityPort,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SCHEDULE_DISABLED_VALUE,
    SCHEDULE_EOD_VALUE,
    SCHEDULE_MIDNIGHT_VALUE,
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


@dataclass
class ACInfinityPortSwitchEntityMixin:
    on_value: int
    off_value: int


@dataclass
class ACInfinityPortSwitchEntityDescription(
    SwitchEntityDescription,
    ACInfinityPortReadWriteMixin,
    ACInfinityPortSwitchEntityMixin,
):
    """Describes ACInfinity Switch Entities."""


PORT_DESCRIPTIONS: list[ACInfinityPortSwitchEntityDescription] = [
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_VPD_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="vpd_mode_high_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_VPD_HIGH_ENABLED
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_VPD_HIGH_ENABLED, value
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_VPD_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="vpd_mode_low_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_VPD_LOW_ENABLED
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_VPD_LOW_ENABLED, value
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_AUTO_TEMP_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_temp_high_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_AUTO_TEMP_HIGH_ENABLED
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_TEMP_HIGH_ENABLED,
                value,
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_AUTO_TEMP_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_temp_low_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_AUTO_TEMP_LOW_ENABLED
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_TEMP_LOW_ENABLED,
                value,
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_humidity_high_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED,
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED,
                value,
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_humidity_low_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED,
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED,
                value,
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_SCHEDULED_START_TIME,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=SCHEDULE_MIDNIGHT_VALUE,
        off_value=SCHEDULE_DISABLED_VALUE,
        icon=None,  # default
        translation_key="schedule_mode_on_time_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_SCHEDULED_START_TIME
            )
            < SCHEDULE_EOD_VALUE + 1
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_SCHEDULED_START_TIME,
                value,
            )
        ),
    ),
    ACInfinityPortSwitchEntityDescription(
        key=SETTING_KEY_SCHEDULED_END_TIME,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=SCHEDULE_EOD_VALUE,
        off_value=SCHEDULE_DISABLED_VALUE,
        icon=None,  # default
        translation_key="schedule_mode_off_time_enabled",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_SCHEDULED_END_TIME
            )
            < SCHEDULE_EOD_VALUE + 1
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_SCHEDULED_END_TIME,
                value,
            )
        ),
    ),
]


class ACInfinityPortSwitchEntity(ACInfinityPortEntity, SwitchEntity):
    entity_description: ACInfinityPortSwitchEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortSwitchEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.get_value_fn(self.ac_infinity, self.port)

    async def async_turn_on(self) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "On"', self.unique_id
        )
        await self.entity_description.set_value_fn(
            self.ac_infinity, self.port, self.entity_description.on_value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "Off"', self.unique_id
        )
        await self.entity_description.set_value_fn(
            self.ac_infinity, self.port, self.entity_description.off_value
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""
    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_device_meta_data()

    entities = []
    for controller in controllers:
        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSwitchEntity(coordinator, description, port)
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.SWITCH,
                )

    add_entities_callback(entities)
