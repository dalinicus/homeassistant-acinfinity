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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortEntity,
    ACInfinityPortReadWriteMixin,
)
from custom_components.ac_infinity.ac_infinity import ACInfinityPort
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER,
    SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER,
    SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER,
    SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER_F,
    SETTING_KEY_AUTO_TEMP_LOW_TRIGGER,
    SETTING_KEY_AUTO_TEMP_LOW_TRIGGER_F,
    SETTING_KEY_CYCLE_DURATION_OFF,
    SETTING_KEY_CYCLE_DURATION_ON,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
    SETTING_KEY_TIMER_DURATION_TO_OFF,
    SETTING_KEY_TIMER_DURATION_TO_ON,
    SETTING_KEY_VPD_HIGH_TRIGGER,
    SETTING_KEY_VPD_LOW_TRIGGER,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ACInfinityPortNumberEntityDescription(
    NumberEntityDescription, ACInfinityPortReadWriteMixin
):
    """Describes ACInfinity Number Entities."""


PORT_DESCRIPTIONS: list[ACInfinityPortNumberEntityDescription] = [
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_ON_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="on_power",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_ON_SPEED
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_ON_SPEED, value
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_OFF_SPEED,
        device_class=NumberDeviceClass.POWER_FACTOR,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        icon="mdi:knob",
        translation_key="off_power",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_OFF_SPEED
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_OFF_SPEED, value
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_TIMER_DURATION_TO_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_on",
        get_value_fn=lambda ac_infinity, port: (
            # value configured as minutes but stored as seconds
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_TIMER_DURATION_TO_ON
            )
            / 60
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            # value configured as minutes but stored as seconds
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_TIMER_DURATION_TO_ON,
                value * 60,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_TIMER_DURATION_TO_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="timer_mode_minutes_to_off",
        get_value_fn=lambda ac_infinity, port: (
            # value configured as minutes but stored as seconds
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_TIMER_DURATION_TO_OFF
            )
            / 60
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            # value configured as minutes but stored as seconds
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_TIMER_DURATION_TO_OFF,
                value * 60,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_CYCLE_DURATION_ON,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_on",
        get_value_fn=lambda ac_infinity, port: (
            # value configured as minutes but stored as seconds
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_CYCLE_DURATION_ON
            )
            / 60
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            # value configured as minutes but stored as seconds
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_CYCLE_DURATION_ON,
                value * 60,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_CYCLE_DURATION_OFF,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        icon=None,  # default
        translation_key="cycle_mode_minutes_off",
        get_value_fn=lambda ac_infinity, port: (
            # value configured as minutes but stored as seconds
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_CYCLE_DURATION_OFF
            )
            / 60
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            # value configured as minutes but stored as seconds
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_CYCLE_DURATION_OFF,
                value * 60,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_VPD_LOW_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_low_trigger",
        get_value_fn=lambda ac_infinity, port: (
            # value configured as percent (10.2%) but stored as tenths of a percent (102)
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_VPD_LOW_TRIGGER
            )
            / 10
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            # value configured as percent (10.2%) but stored as tenths of a percent (102)
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_VPD_LOW_TRIGGER,
                value * 10,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_VPD_HIGH_TRIGGER,
        device_class=NumberDeviceClass.PRESSURE,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=9.9,
        native_step=0.1,
        icon="mdi:water-thermometer-outline",
        translation_key="vpd_mode_high_trigger",
        get_value_fn=lambda ac_infinity, port: (
            # value configured as percent (10.2%) but stored as tenths of a percent (102)
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_VPD_HIGH_TRIGGER
            )
            / 10
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            # value configured as percent (10.2%) but stored as tenths of a percent (102)
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_VPD_HIGH_TRIGGER,
                value * 10,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_low_trigger",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER,
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_LOW_TRIGGER,
                value,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER,
        device_class=NumberDeviceClass.HUMIDITY,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        icon="mdi:water-percent",
        translation_key="auto_mode_humidity_high_trigger",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER,
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_HUMIDITY_HIGH_TRIGGER,
                value,
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_AUTO_TEMP_LOW_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_low_trigger",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id,
                port.port_id,
                SETTING_KEY_AUTO_TEMP_LOW_TRIGGER,
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_settings(
                port.parent_device_id,
                port.port_id,
                [
                    # value is received from HA as C
                    (SETTING_KEY_AUTO_TEMP_LOW_TRIGGER, value),
                    # degrees F must be calculated and set in addition to C
                    (SETTING_KEY_AUTO_TEMP_LOW_TRIGGER_F, round((value * 1.8) + 32, 0)),
                ],
            )
        ),
    ),
    ACInfinityPortNumberEntityDescription(
        key=SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.AUTO,
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        icon=None,
        translation_key="auto_mode_temp_high_trigger",
        get_value_fn=lambda ac_infinity, port: (
            ac_infinity.get_device_port_setting(
                port.parent_device_id, port.port_id, SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER
            )
        ),
        set_value_fn=lambda ac_infinity, port, value: (
            ac_infinity.set_device_port_settings(
                port.parent_device_id,
                port.port_id,
                [
                    # value is received from HA as C
                    (SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER, value),
                    # degrees F must be calculated and set in addition to C
                    (
                        SETTING_KEY_AUTO_TEMP_HIGH_TRIGGER_F,
                        round((value * 1.8) + 32, 0),
                    ),
                ],
            )
        ),
    ),
]


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
        return self.entity_description.get_value_fn(self.ac_infinity, self.port)

    async def async_set_native_value(self, value: float) -> None:
        _LOGGER.info(
            'User requesting value update of entity "%s" to "%s"', self.unique_id, value
        )
        await self.entity_description.set_value_fn(self.ac_infinity, self.port, value)
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
                entity = ACInfinityPortNumberEntity(coordinator, description, port)
                entities.append(entity)
                _LOGGER.info(
                    'Initializing entity "%s" for platform "%s".',
                    entity.unique_id,
                    Platform.NUMBER,
                )

    add_entities_callback(entities)
