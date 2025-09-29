import logging
from dataclasses import dataclass
from typing import Any

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
    AdvancedSettingsKey,
    ControllerType,
    DeviceControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityDevice,
    ACInfinityDeviceEntity,
    ACInfinityDeviceReadWriteMixin, enabled_fn_control, enabled_fn_setting,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ACInfinitySwitchOnOffValuesMixin:
    """Adds on_value and off_value to track what values the AC Infinity API considers
    onn and off for the field the entity is responsible for
    """

    on_value: int
    off_value: int


@dataclass(frozen=True)
class ACInfinitySwitchEntityDescription(SwitchEntityDescription):
    """Describes ACInfinity Switch Entities."""

    key: str
    device_class: SwitchDeviceClass | None
    icon: str | None
    translation_key: str | None


@dataclass(frozen=True)
class ACInfinityDeviceSwitchEntityDescription(
    ACInfinitySwitchEntityDescription,
    ACInfinityDeviceReadWriteMixin,
    ACInfinitySwitchOnOffValuesMixin,
):
    """Describes ACInfinity Switch Entities."""


def __suitable_fn_device_setting_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_setting_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __suitable_fn_device_control_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_control_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __get_value_fn_device_control_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_control(
        device.controller.controller_id, device.device_port, entity.data_key, 0
    )


def __get_value_fn_device_setting_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_setting(
        device.controller.controller_id, device.device_port, entity.data_key, 0
    )


def __get_value_fn_schedule_enabled(entity: ACInfinityEntity, device: ACInfinityDevice):
    return (
        entity.ac_infinity.get_device_control(
            device.controller.controller_id,
            device.device_port,
            entity.data_key,
            SCHEDULE_DISABLED_VALUE,
        )
        < SCHEDULE_EOD_VALUE + 1
    )


def __set_value_fn_device_control_default(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: int
):
    return entity.ac_infinity.update_device_control(
        device.controller.controller_id, device.device_port, entity.data_key, value
    )


def __set_value_fn_device_setting_default(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: int
):
    return entity.ac_infinity.update_device_setting(
        device.controller.controller_id, device.device_port, entity.data_key, value
    )


DEVICE_DESCRIPTIONS: list[ACInfinityDeviceSwitchEntityDescription] = [
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.VPD_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="vpd_mode_high_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.VPD_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="vpd_mode_low_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.VPD_TARGET_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="target_vpd_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.AUTO_TEMP_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_temp_high_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.AUTO_TEMP_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_temp_low_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.AUTO_HUMIDITY_HIGH_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_humidity_high_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.AUTO_HUMIDITY_LOW_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="auto_mode_humidity_low_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.AUTO_TARGET_TEMP_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="target_temp_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.AUTO_TARGET_HUMIDITY_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="target_humidity_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_device_control_default,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.SCHEDULED_START_TIME,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=SCHEDULE_MIDNIGHT_VALUE,
        off_value=SCHEDULE_DISABLED_VALUE,
        icon=None,  # default
        translation_key="schedule_mode_on_time_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_schedule_enabled,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=DeviceControlKey.SCHEDULED_END_TIME,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=SCHEDULE_EOD_VALUE,
        off_value=SCHEDULE_DISABLED_VALUE,
        icon=None,  # default
        translation_key="schedule_mode_off_time_enabled",
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_schedule_enabled,
        set_value_fn=__set_value_fn_device_control_default,
    ),
    ACInfinityDeviceSwitchEntityDescription(
        key=AdvancedSettingsKey.SUNRISE_TIMER_ENABLED,
        device_class=SwitchDeviceClass.SWITCH,
        on_value=1,
        off_value=0,
        icon=None,  # default
        translation_key="sunrise_timer_enabled",
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_device_setting_default,
        set_value_fn=__set_value_fn_device_setting_default,
    ),
]


class ACInfinityDeviceSwitchEntity(ACInfinityDeviceEntity, SwitchEntity):
    entity_description: ACInfinityDeviceSwitchEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityDeviceSwitchEntityDescription,
        device: ACInfinityDevice,
    ) -> None:
        super().__init__(
            coordinator, device, description.enabled_fn, description.suitable_fn, description.key, Platform.SWITCH
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.get_value_fn(self, self.device_port)

    async def async_turn_on(self, **kwargs: Any) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "On"', self.unique_id
        )
        await self.entity_description.set_value_fn(
            self, self.device_port, self.entity_description.on_value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "Off"', self.unique_id
        )
        await self.entity_description.set_value_fn(
            self, self.device_port, self.entity_description.off_value
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""
    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities(config)
    for controller in controllers:
        if controller.controller_type == ControllerType.UIS_89_AI_PLUS:
            # controls and settings not yet supported for the AI controller
            continue

        for device in controller.devices:
            for description in DEVICE_DESCRIPTIONS:
                entity = ACInfinityDeviceSwitchEntity(coordinator, description, device)
                entities.append_if_suitable(entity)

    add_entities_callback(entities)
