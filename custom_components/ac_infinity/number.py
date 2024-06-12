import logging
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.const import (
    DOMAIN,
    ControllerSettingKey,
    PortSettingKey,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityControllerEntity,
    ACInfinityControllerReadWriteMixin,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntity,
    ACInfinityPort,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
    get_value_fn_controller_setting_default,
    get_value_fn_port_setting_default,
    set_value_fn_controller_setting_default,
    set_value_fn_port_setting_default,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityNumberEntityDescription(NumberEntityDescription):
    """Describes ACInfinity Number Entities"""

    key: str
    icon: str | None
    translation_key: str | None
    device_class: NumberDeviceClass | None
    mode: NumberMode | None
    native_max_value: float | None
    native_min_value: float | None
    native_step: float | None
    native_unit_of_measurement: str | None


@dataclass
class ACInfinityControllerNumberEntityDescription(
    ACInfinityNumberEntityDescription, ACInfinityControllerReadWriteMixin
):
    """Describes ACInfinity Number Controller Entities."""


@dataclass
class ACInfinityPortNumberEntityDescription(
    ACInfinityNumberEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Number Port Entities."""


def __get_value_fn_cal_temp(entity: ACInfinityEntity, controller: ACInfinityController):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, ControllerSettingKey.TEMP_UNIT
    )
    return entity.ac_infinity.get_controller_setting(
        controller.device_id,
        ControllerSettingKey.CALIBRATE_TEMP
        if temp_unit > 0
        else ControllerSettingKey.CALIBRATE_TEMP_F,
    )


def __set_value_fn_cal_temp(
    entity: ACInfinityEntity, controller: ACInfinityController, value: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, ControllerSettingKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity min/max values will still be ±20 instead of ±10
    if temp_unit > 0 and value > 10:
        value = 10
    elif temp_unit > 0 and value < -10:
        value = -10

    return entity.ac_infinity.update_controller_settings(
        controller.device_id,
        [
            (ControllerSettingKey.CALIBRATE_TEMP, value),
            (ControllerSettingKey.CALIBRATE_TEMP_F, 0),
        ]
        if temp_unit > 0
        else [
            (ControllerSettingKey.CALIBRATE_TEMP, 0),
            (ControllerSettingKey.CALIBRATE_TEMP_F, value),
        ],
    )


def __get_value_fn_vpd_leaf_temp_offset(
    entity: ACInfinityEntity, controller: ACInfinityController
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, ControllerSettingKey.TEMP_UNIT
    )
    return entity.ac_infinity.get_controller_setting(
        controller.device_id,
        ControllerSettingKey.VPD_LEAF_TEMP_OFFSET
        if temp_unit > 0
        else ControllerSettingKey.VPD_LEAF_TEMP_OFFSET_F,
    )


def __set_value_fn_vpd_leaf_temp_offset(
    entity: ACInfinityEntity, controller: ACInfinityController, value: int
):
    temp_unit = entity.ac_infinity.get_controller_setting(
        controller.device_id, ControllerSettingKey.TEMP_UNIT
    )

    # in the event that the user swaps from F to C in the ac infinity app without reloading homeassistant,
    # we need to put bounds on the value since the entity min/max values will still be ±20 instead of ±10
    if temp_unit > 0 and value > 10:
        value = 10
    elif temp_unit > 0 and value < -10:
        value = -10

    return entity.ac_infinity.update_controller_setting(
        controller.device_id,
        ControllerSettingKey.VPD_LEAF_TEMP_OFFSET
        if temp_unit > 0
        else ControllerSettingKey.VPD_LEAF_TEMP_OFFSET_F,
        value,
    )


def __get_value_fn_timer_duration(entity: ACInfinityEntity, port: ACInfinityPort):
    # value configured as minutes but stored as seconds
    return (
        entity.ac_infinity.get_port_setting(
            port.controller.device_id, port.port_index, entity.entity_description.key
        )
        / 60
    )


def __set_value_fn_timer_duration(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    # value configured as minutes but stored as seconds
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        value * 60,
    )


def __get_value_fn_vpd(entity: ACInfinityEntity, port: ACInfinityPort):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return (
        entity.ac_infinity.get_port_setting(
            port.controller.device_id, port.port_index, entity.entity_description.key
        )
        / 10
    )


def __set_value_fn_vpd(entity: ACInfinityEntity, port: ACInfinityPort, value: int):
    # value configured as percent (10.2%) but stored as tenths of a percent (102)
    return entity.ac_infinity.update_port_setting(
        port.controller.device_id,
        port.port_index,
        entity.entity_description.key,
        value * 10,
    )


def __set_value_fn_temp_auto_low(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_settings(
        port.controller.device_id,
        port.port_index,
        [
            # value is received from HA as C
            (PortSettingKey.AUTO_TEMP_LOW_TRIGGER, value),
            # degrees F must be calculated and set in addition to C
            (PortSettingKey.AUTO_TEMP_LOW_TRIGGER_F, int(round((value * 1.8) + 32, 0))),
        ],
    )


def __set_value_fn_temp_auto_high(
    entity: ACInfinityEntity, port: ACInfinityPort, value: int
):
    return entity.ac_infinity.update_port_settings(
        port.controller.device_id,
        port.port_index,
        [
            # value is received from HA as C
            (PortSettingKey.AUTO_TEMP_HIGH_TRIGGER, value),
            # degrees F must be calculated and set in addition to C
            (
                PortSettingKey.AUTO_TEMP_HIGH_TRIGGER_F,
                int(round((value * 1.8) + 32, 0)),
            ),
        ],
    )


CONTROLLER_DESCRIPTIONS: list[ACInfinityControllerNumberEntityDescription] = [
    ACInfinityControllerNumberEntityDescription(
        key=ControllerSettingKey.CALIBRATE_TEMP,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        icon="mdi:thermometer-plus",
        translation_key="temperature_calibration",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_cal_temp,
        set_value_fn=__set_value_fn_cal_temp,
    ),
    ACInfinityControllerNumberEntityDescription(
        key=ControllerSettingKey.CALIBRATE_HUMIDITY,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-10,
        native_max_value=10,
        native_step=1,
        icon="mdi:cloud-percent-outline",
        translation_key="humidity_calibration",
        native_unit_of_measurement=None,
        get_value_fn=get_value_fn_controller_setting_default,
        set_value_fn=set_value_fn_controller_setting_default,
    ),
    ACInfinityControllerNumberEntityDescription(
        key=ControllerSettingKey.VPD_LEAF_TEMP_OFFSET,
        device_class=None,
        mode=NumberMode.AUTO,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
        icon="mdi:leaf",
        translation_key="vpd_leaf_temperature_offset",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_vpd_leaf_temp_offset,
        set_value_fn=__set_value_fn_vpd_leaf_temp_offset,
    ),
]

PORT_DESCRIPTIONS: list[ACInfinityPortNumberEntityDescription] = [
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.ON_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="on_power",
        native_unit_of_measurement=None,
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.OFF_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="off_power",
        native_unit_of_measurement=None,
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.TIMER_DURATION_TO_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_on",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.TIMER_DURATION_TO_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_off",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.CYCLE_DURATION_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_on",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.CYCLE_DURATION_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_off",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_timer_duration,
        set_value_fn=__set_value_fn_timer_duration,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.VPD_LOW_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_low_trigger",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_vpd,
        set_value_fn=__set_value_fn_vpd,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.VPD_HIGH_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_high_trigger",
        native_unit_of_measurement=None,
        get_value_fn=__get_value_fn_vpd,
        set_value_fn=__set_value_fn_vpd,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.AUTO_HUMIDITY_LOW_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_low_trigger",
        native_unit_of_measurement=None,
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.AUTO_HUMIDITY_HIGH_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_high_trigger",
        native_unit_of_measurement=None,
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=set_value_fn_port_setting_default,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.AUTO_TEMP_LOW_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_low_trigger",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=__set_value_fn_temp_auto_low,
    ),
    ACInfinityPortNumberEntityDescription(
        key=PortSettingKey.AUTO_TEMP_HIGH_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_high_trigger",
        get_value_fn=get_value_fn_port_setting_default,
        set_value_fn=__set_value_fn_temp_auto_high,
    ),
]


class ACInfinityControllerNumberEntity(ACInfinityControllerEntity, NumberEntity):
    entity_description: ACInfinityControllerNumberEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityControllerNumberEntityDescription,
        controller: ACInfinityController,
    ) -> None:
        super().__init__(coordinator, controller, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.get_value_fn(self, self.controller)

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self, self.controller, value)
        await self.coordinator.async_request_refresh()


class ACInfinityPortNumberEntity(ACInfinityPortEntity, NumberEntity):
    entity_description: ACInfinityPortNumberEntityDescription

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        description: ACInfinityPortNumberEntityDescription,
        port: ACInfinityPort,
    ) -> None:
        super().__init__(coordinator, port, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.get_value_fn(self, self.port)

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self, self.port, value)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback
) -> None:
    """Set up the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
    controllers = coordinator.ac_infinity.get_all_controller_properties()

    entities = []
    for controller in controllers:
        temp_unit = coordinator.ac_infinity.get_controller_setting(
            controller.device_id, ControllerSettingKey.TEMP_UNIT
        )
        for description in CONTROLLER_DESCRIPTIONS:
            entity = ACInfinityControllerNumberEntity(
                coordinator, description, controller
            )
            if temp_unit > 0 and (
                description.key == ControllerSettingKey.CALIBRATE_TEMP
                or ControllerSettingKey.VPD_LEAF_TEMP_OFFSET
            ):
                # Celsius is restricted to ±10C versus Fahrenheit which is restricted to ±20C
                entity.entity_description.native_min_value = -10
                entity.entity_description.native_max_value = 10

            entities.append(entity)
            _LOGGER.info(
                'Initializing entity "%s" for platform "%s".',
                entity.unique_id,
                Platform.NUMBER,
            )
        for port in controller.ports:
            for description in PORT_DESCRIPTIONS:
                entity = ACInfinityPortNumberEntity(coordinator, description, port)
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.NUMBER,
                )

    add_entities_callback(entities)
