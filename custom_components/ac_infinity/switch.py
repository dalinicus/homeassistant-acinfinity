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

from custom_components.ac_infinity.const import (
    DOMAIN,
    SCHEDULE_DISABLED_VALUE,
    SCHEDULE_EOD_VALUE,
    SCHEDULE_MIDNIGHT_VALUE,
    PortSettingKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
    get_value_fn_port_setting_default,
    set_value_fn_port_setting_default,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinitySwitchOnOffValuesMixin:
    """Adds on_value and off_value to track what values the AC Infinity API considers
    onn and off for the field the entity is responsible for
    """

    on_value: int
    off_value: int


@dataclass
class ACInfinitySwitchEntityDescription(SwitchEntityDescription):
    """Describes ACInfinity Switch Entities."""

    key: str
    device_class: SwitchDeviceClass | None
    icon: str | None
    translation_key: str | None


@dataclass
class ACInfinityPortSwitchEntityDescription(
    ACInfinitySwitchEntityDescription,
    ACInfinityPortReadWriteMixin,
    ACInfinitySwitchOnOffValuesMixin,
):
    """Describes ACInfinity Switch Entities."""


def __get_value_fn_schedule_enabled(entity: ACInfinityEntity, port: ACInfinityPort):
    return (
        entity.ac_infinity.get_port_setting(
            port.controller.device_id, port.port_index, entity.entity_description.key
        )
        < SCHEDULE_EOD_VALUE + 1
    )


PORT_DESCRIPTIONS: list[ACInfinityPortSwitchEntityDescription] = [
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.VPD_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="vpd_mode_high_enabled",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.VPD_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="vpd_mode_low_enabled",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.AUTO_TEMP_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_temp_high_enabled",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.AUTO_TEMP_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_temp_low_enabled",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.AUTO_HUMIDITY_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_humidity_high_enabled",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.AUTO_HUMIDITY_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_humidity_low_enabled",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.SCHEDULED_START_TIME,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=SCHEDULE_MIDNIGHT_VALUE,
        off_value=SCHEDULE_DISABLED_VALUE,
        icon=None,  # default
        translation_key="schedule_mode_on_time_enabled",
        get_value_fn=__get_value_fn_schedule_enabled,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortSwitchEntityDescription(
        key=PortSettingKey.SCHEDULED_END_TIME,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=SCHEDULE_EOD_VALUE,
        off_value=SCHEDULE_DISABLED_VALUE,
        icon=None,  # default
        translation_key="schedule_mode_off_time_enabled",
        get_value_fn=__get_value_fn_schedule_enabled,
        set_value_fn=set_value_fn_port_setting_default,
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
        return self.entity_description.get_value_fn(self, self.port)

    async def async_turn_on(self) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "On"', self.unique_id
        )
        await self.entity_description.set_value_fn(
            self, self.port, self.entity_description.on_value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "Off"', self.unique_id
        )
        await self.entity_description.set_value_fn(
            self, self.port, self.entity_description.off_value
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""
    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

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
