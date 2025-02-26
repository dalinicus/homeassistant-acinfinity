import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    ControllerType,
    PortControlKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadWriteMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntities,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinitySelectEntityDescription(SelectEntityDescription):
    """Describes ACInfinity Select Entities."""

    key: str
    translation_key: str | None
    options: list[str] | None


@dataclass
class ACInfinityControllerSelectEntityDescription(
    ACInfinitySelectEntityDescription, ACInfinityControllerReadWriteMixin
):
    """Describes ACInfinity Select Controller Entities."""


@dataclass
class ACInfinityPortSelectEntityDescription(
    ACInfinitySelectEntityDescription, ACInfinityPortReadWriteMixin
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

DEVICE_LOAD_TYPE_OPTIONS = {
    1: "Grow Light",
    2: "Humidifier",
    4: "Heater",
    5: "AC",
    6: "Fan",
}

SETTINGS_MODE_OPTIONS = [
    "Auto",
    "Target",
]


def __suitable_fn_controller_setting_default(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return entity.ac_infinity.get_controller_setting_exists(
        controller.device_id, entity.entity_description.key
    )


def __suitable_fn_port_control_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_control_exists(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def __suitable_fn_port_setting_default(entity: ACInfinityEntity, port: ACInfinityPort):
    return entity.ac_infinity.get_port_setting_exists(
        port.controller.device_id, port.port_index, entity.entity_description.key
    )


def __get_value_fn_outside_climate(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    return OUTSIDE_CLIMATE_OPTIONS[
        entity.ac_infinity.get_controller_setting(
            controller.device_id, entity.entity_description.key, 0
        )
    ]


def __get_value_fn_setting_mode(entity: ACInfinityEntity, port: ACInfinityPort):
    return SETTINGS_MODE_OPTIONS[
        entity.ac_infinity.get_port_control(
            port.controller.device_id, port.port_index, entity.entity_description.key, 0
        )
    ]


def __get_value_fn_active_mode(entity: ACInfinityEntity, port: ACInfinityPort):
    return MODE_OPTIONS[
        # data is 1 based.  Adjust to 0 based enum by subtracting 1
        entity.ac_infinity.get_port_control(
            port.controller.device_id, port.port_index, PortControlKey.AT_TYPE, 1
        )
        - 1
    ]


def __get_value_fn_dynamic_response_type(
    entity: ACInfinityEntity, port: ACInfinityPort
):
    return DYNAMIC_RESPONSE_OPTIONS[
        entity.ac_infinity.get_port_setting(
            port.controller.device_id,
            port.port_index,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
            0,
        )
    ]


def __get_value_fn_device_load_type(entity: ACInfinityEntity, port: ACInfinityPort):
    value = entity.ac_infinity.get_port_setting(
        port.controller.device_id,
        port.port_index,
        AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        1,
    )

    return DEVICE_LOAD_TYPE_OPTIONS.get(value, "Unknown Device Type")


def __set_value_fn_outside_climate(
    entity: ACInfinityEntity, controller: ACInfinityController, value: str
):
    return entity.ac_infinity.update_controller_setting(
        controller.device_id,
        entity.entity_description.key,
        OUTSIDE_CLIMATE_OPTIONS.index(value),
    )


def __set_value_fn_setting_mode(
    entity: ACInfinityEntity, port: ACInfinityPort, value: str
):
    return entity.ac_infinity.update_port_control(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        SETTINGS_MODE_OPTIONS.index(value),
    )


def __set_value_fn_active_mode(
    entity: ACInfinityEntity, port: ACInfinityPort, value: str
):
    return entity.ac_infinity.update_port_control(
        port.controller.device_id,
        port.port_index,
        PortControlKey.AT_TYPE,
        # data is 1 based.  Adjust from 0 based enum by adding 1
        MODE_OPTIONS.index(value) + 1,
    )


def __set_value_fn_dynamic_response_type(
    entity: ACInfinityEntity, port: ACInfinityPort, value: str
):
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id,
        port.port_index,
        AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        DYNAMIC_RESPONSE_OPTIONS.index(value),
    )


def __set_value_fn_device_load_type(
    entity: ACInfinityEntity, port: ACInfinityPort, value: str
):
    for key, val in DEVICE_LOAD_TYPE_OPTIONS.items():
        if val == value:
            return entity.ac_infinity.update_port_setting(
                port.controller.device_id,
                port.port_index,
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
        get_value_fn=__get_value_fn_outside_climate,
        set_value_fn=__set_value_fn_outside_climate,
    ),
    ACInfinityControllerSelectEntityDescription(
        key=AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE,
        translation_key="outside_climate_humidity",
        options=OUTSIDE_CLIMATE_OPTIONS,
        suitable_fn=__suitable_fn_controller_setting_default,
        get_value_fn=__get_value_fn_outside_climate,
        set_value_fn=__set_value_fn_outside_climate,
    ),
]

PORT_DESCRIPTIONS: list[ACInfinityPortSelectEntityDescription] = [
    ACInfinityPortSelectEntityDescription(
        key=PortControlKey.AT_TYPE,
        translation_key="active_mode",
        options=MODE_OPTIONS,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_active_mode,
        set_value_fn=__set_value_fn_active_mode,
    ),
    ACInfinityPortSelectEntityDescription(
        key=PortControlKey.AUTO_SETTINGS_MODE,
        translation_key="auto_settings_mode",
        options=SETTINGS_MODE_OPTIONS,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_setting_mode,
        set_value_fn=__set_value_fn_setting_mode,
    ),
    ACInfinityPortSelectEntityDescription(
        key=PortControlKey.VPD_SETTINGS_MODE,
        translation_key="vpd_settings_mode",
        options=SETTINGS_MODE_OPTIONS,
        suitable_fn=__suitable_fn_port_control_default,
        get_value_fn=__get_value_fn_setting_mode,
        set_value_fn=__set_value_fn_setting_mode,
    ),
    ACInfinityPortSelectEntityDescription(
        key=AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        translation_key="device_load_type",
        options=list(DEVICE_LOAD_TYPE_OPTIONS.values()),
        suitable_fn=__suitable_fn_port_setting_default,
        get_value_fn=__get_value_fn_device_load_type,
        set_value_fn=__set_value_fn_device_load_type,
    ),
    ACInfinityPortSelectEntityDescription(
        key=AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        translation_key="dynamic_response_type",
        options=DYNAMIC_RESPONSE_OPTIONS,
        suitable_fn=__suitable_fn_port_setting_default,
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


class ACInfinityPortSelectEntity(ACInfinityPortEntity, SelectEntity):
    entity_description: ACInfinityPortSelectEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortSelectEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(
            coordinator, port, description.suitable_fn, description.key, Platform.SELECT
        )
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        return self.entity_description.get_value_fn(self, self.port)

    async def async_select_option(self, option: str) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"',
            self.unique_id,
            option,
        )
        await self.entity_description.set_value_fn(self, self.port, option)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = ACInfinityEntities()
    for controller in controllers:
        if controller.device_type == ControllerType.UIS_89_AI_PLUS:
            # controls and settings not yet supported for the AI controller
            continue

        for description in CONTROLLER_DESCRIPTIONS:
            entity = ACInfinityControllerSelectEntity(
                coordinator, description, controller
            )
            entities.append_if_suitable(entity)

        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortSelectEntity(coordinator, description, port)
                entities.append_if_suitable(entity)

    add_entities_callback(entities)
