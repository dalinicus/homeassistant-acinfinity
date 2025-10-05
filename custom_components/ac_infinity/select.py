import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import (
    ControllerPropertyKey, ControllerType, DOMAIN, AdvancedSettingsKey, DeviceControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadWriteMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityDevice,
    ACInfinityDeviceEntity,
    ACInfinityDeviceReadWriteMixin, enabled_fn_setting, enabled_fn_control,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ACInfinitySelectEntityDescription(SelectEntityDescription):
    """Describes ACInfinity Select Entities."""

    key: str
    translation_key: str | None
    options: list[str] | None


@dataclass(frozen=True)
class ACInfinityControllerSelectEntityDescription(
    ACInfinitySelectEntityDescription, ACInfinityControllerReadWriteMixin
):
    """Describes ACInfinity Select Controller Entities."""


@dataclass(frozen=True)
class ACInfinityDeviceSelectEntityDescription(
    ACInfinitySelectEntityDescription, ACInfinityDeviceReadWriteMixin
):
    """Describes ACInfinity Select Port Entities."""


MODE_OPTIONS = [
    "Off",
    "On",
    "Auto",
    "Timer to On",
    "Timer to Off",
    "Cycle",
    "Schedule",
    "VPD",
]

DYNAMIC_RESPONSE_OPTIONS = ["Transition", "Buffer"]

OUTSIDE_CLIMATE_OPTIONS = ["Neutral", "Lower", "Higher"]

STANDARD_DEVICE_LOAD_TYPE_OPTIONS = {
    1: "Grow Light",
    2: "Humidifier",
    3: "Dehumidifier",
    4: "Heater",
    5: "AC",
    6: "Fan",
    8: "Water Pump"
}

AI_DEVICE_LOAD_TYPE_OPTIONS = {
    128: "Outlet",
    129: "Grow Light",
    130: "Humidifier",
    131: "Dehumidifier",
    132: "Heater",
    133: "AC",
    134: "Circulation Fan",
    135: "Ventilation Fan",
    136: "Peristaltic Pump",
    137: "Water Pump",
    138: "CO2 Regulator"
}

DEVICE_LOAD_TYPE_OPTIONS = STANDARD_DEVICE_LOAD_TYPE_OPTIONS | AI_DEVICE_LOAD_TYPE_OPTIONS


def __suitable_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_setting_exists(
        controller.controller_id, entity.data_key
    )


def __suitable_fn_device_control_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_control_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __suitable_fn_device_setting_default(entity: ACInfinityEntity, device: ACInfinityDevice):
    return entity.ac_infinity.get_device_setting_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __suitable_fn_device_setting_basic_controller(entity: ACInfinityEntity, device: ACInfinityDevice):
    controller_type = entity.ac_infinity.get_controller_property(device.controller.controller_id, ControllerPropertyKey.DEVICE_TYPE)
    return not ControllerType.is_ai_controller(controller_type) and entity.ac_infinity.get_device_setting_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __suitable_fn_device_setting_ai_controller(entity: ACInfinityEntity, device: ACInfinityDevice):
    controller_type = entity.ac_infinity.get_controller_property(device.controller.controller_id, ControllerPropertyKey.DEVICE_TYPE)
    return ControllerType.is_ai_controller(controller_type) and entity.ac_infinity.get_device_setting_exists(
        device.controller.controller_id, device.device_port, entity.data_key
    )


def __get_value_fn_outside_climate(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return OUTSIDE_CLIMATE_OPTIONS[
        entity.ac_infinity.get_controller_setting(
            controller.controller_id, entity.data_key, 0
        )
    ]


def __get_value_fn_active_mode(entity: ACInfinityEntity, device: ACInfinityDevice):
    return MODE_OPTIONS[
        # data is 1 based.  Adjust to 0 based enum by subtracting 1
        entity.ac_infinity.get_device_control(
            device.controller.controller_id, device.device_port, DeviceControlKey.AT_TYPE, 1
        )
        - 1
    ]


def __get_value_fn_dynamic_response_type(
    entity: ACInfinityEntity, device: ACInfinityDevice
):
    return DYNAMIC_RESPONSE_OPTIONS[
        entity.ac_infinity.get_device_setting(
            device.controller.controller_id,
            device.device_port,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
            0,
        )
    ]


def __get_value_fn_device_load_type(entity: ACInfinityEntity, device: ACInfinityDevice):
    value = entity.ac_infinity.get_device_setting(
        device.controller.controller_id,
        device.device_port,
        AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        1,
    )

    return DEVICE_LOAD_TYPE_OPTIONS.get(value, "Unknown Device Type")


def __set_value_fn_outside_climate(
    entity: ACInfinityEntity, controller: ACInfinityController, value: str
):
    return entity.ac_infinity.update_controller_setting(
        controller.controller_id,
        entity.data_key,
        OUTSIDE_CLIMATE_OPTIONS.index(value),
    )


def __set_value_fn_active_mode(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: str
):
    return entity.ac_infinity.update_device_control(
        device.controller.controller_id,
        device.device_port,
        DeviceControlKey.AT_TYPE,
        # data is 1 based.  Adjust from 0 based enum by adding 1
        MODE_OPTIONS.index(value) + 1,
    )


def __set_value_fn_dynamic_response_type(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: str
):
    return entity.ac_infinity.update_device_setting(
        device.controller.controller_id,
        device.device_port,
        AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        DYNAMIC_RESPONSE_OPTIONS.index(value),
    )


def __set_value_fn_device_load_type(
    entity: ACInfinityEntity, device: ACInfinityDevice, value: str
):
    for key, val in DEVICE_LOAD_TYPE_OPTIONS.items():
        if val == value:
            return entity.ac_infinity.update_device_setting(
                device.controller.controller_id,
                device.device_port,
                AdvancedSettingsKey.DEVICE_LOAD_TYPE,
                key,
            )

    raise ValueError(f"Unknown Device Type: {value}")


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerSelectEntityDescription] = [
    ACInfinityControllerSelectEntityDescription(
        key=AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE,
        translation_key="outside_climate_temperature",
        options=OUTSIDE_CLIMATE_OPTIONS,
        suitable_fn=__suitable_fn_controller_setting_default,
        enabled_fn=enabled_fn_setting,
        get_value_fn=__get_value_fn_outside_climate,
        set_value_fn=__set_value_fn_outside_climate,
    ),
    ACInfinityControllerSelectEntityDescription(
        key=AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE,
        translation_key="outside_climate_humidity",
        options=OUTSIDE_CLIMATE_OPTIONS,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_controller_setting_default,
        get_value_fn=__get_value_fn_outside_climate,
        set_value_fn=__set_value_fn_outside_climate,
    ),
]

DEVICE_DESCRIPTIONS: list[ACInfinityDeviceSelectEntityDescription] = [
    ACInfinityDeviceSelectEntityDescription(
        key=DeviceControlKey.AT_TYPE,
        translation_key="active_mode",
        options=MODE_OPTIONS,
        enabled_fn=enabled_fn_control,
        suitable_fn=__suitable_fn_device_control_default,
        get_value_fn=__get_value_fn_active_mode,
        set_value_fn=__set_value_fn_active_mode,
    ),
    ACInfinityDeviceSelectEntityDescription(
        key=AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        translation_key="device_load_type",
        options=list(STANDARD_DEVICE_LOAD_TYPE_OPTIONS.values()),
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_basic_controller,
        get_value_fn=__get_value_fn_device_load_type,
        set_value_fn=__set_value_fn_device_load_type,
    ),
    ACInfinityDeviceSelectEntityDescription(
        key=AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        translation_key="device_load_type",
        options=list(AI_DEVICE_LOAD_TYPE_OPTIONS.values()),
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_ai_controller,
        get_value_fn=__get_value_fn_device_load_type,
        set_value_fn=__set_value_fn_device_load_type,
    ),
    ACInfinityDeviceSelectEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        translation_key="dynamic_response_type",
        options=DYNAMIC_RESPONSE_OPTIONS,
        enabled_fn=enabled_fn_setting,
        suitable_fn=__suitable_fn_device_setting_default,
        get_value_fn=__get_value_fn_dynamic_response_type,
        set_value_fn=__set_value_fn_dynamic_response_type,
    ),
]


class ACInfinityControllerSelectEntity(ACInfinityControllerEntity, SelectEntity):
    entity_description: ACInfinityControllerSelectEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityControllerSelectEntityDescription,
        controller: ACInfinityController,
    ) -> None:
        super().__init__(
            coordinator,
            controller,
            description.enabled_fn,
            description.suitable_fn,
            description.key,
            Platform.SELECT,
        )
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        return self.entity_description.get_value_fn(self, self.controller)

    async def async_select_option(self, option: str) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"',
            self.unique_id,
            option,
        )
        await self.entity_description.set_value_fn(self, self.controller, option)
        await self.coordinator.async_request_refresh()


class ACInfinityDeviceSelectEntity(ACInfinityDeviceEntity, SelectEntity):
    entity_description: ACInfinityDeviceSelectEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityDeviceSelectEntityDescription,
        device: ACInfinityDevice,
    ) -> None:
        super().__init__(coordinator, device, description.enabled_fn, description.suitable_fn, description.key, Platform.SELECT)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        return self.entity_description.get_value_fn(self, self.device_port)

    async def async_select_option(self, option: str) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"',
            self.unique_id,
            option,
        )
        await self.entity_description.set_value_fn(self, self.device_port, option)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities(config)
    for controller in controllers:

        for controller_description in CONTROLLER_DESCRIPTIONS:
            controller_entity = ACInfinityControllerSelectEntity(
                coordinator, controller_description, controller
            )
            entities.append_if_suitable(controller_entity)

        for device in controller.devices:
            for device_description in DEVICE_DESCRIPTIONS:
                device_entity = ACInfinityDeviceSelectEntity(
                    coordinator, device_description, device
                )
                entities.append_if_suitable(device_entity)

    add_entities_callback(entities)
