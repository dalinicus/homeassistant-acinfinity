import asyncio
from asyncio import Future

import pytest
from homeassistant.components.number import NumberDeviceClass
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
    SETTING_KEY_TIMER_DURATION_TO_OFF,
    SETTING_KEY_TIMER_DURATION_TO_ON,
    SETTING_KEY_VPD_HIGH_ENABLED,
    SETTING_KEY_VPD_HIGH_TRIGGER,
    SETTING_KEY_VPD_LOW_ENABLED,
    SETTING_KEY_VPD_LOW_TRIGGER,
)
from custom_components.ac_infinity.number import (
    ACInfinityPortNumberEntity,
    async_setup_entry,
)
from tests import ACTestObjects, execute_and_get_port_entity, setup_entity_mocks
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities: list[ACInfinityPortNumberEntity] = []

    def add_entities_callback(
        self,
        new_entities: list[ACInfinityPortNumberEntity],
        update_before_add: bool = False,
    ):
        self._added_entities = new_entities


@pytest.mark.asyncio
class TestNumbers:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.configEntry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 24

    @pytest.mark.parametrize(
        "setting", [(SETTING_KEY_OFF_SPEED), (SETTING_KEY_ON_SPEED)]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_speed_created_for_each_port(
        self, setup, setting, port
    ):
        """Sensor for device port intensity created on setup"""

        entity: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert "Speed" in entity._attr_name
        assert entity._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert entity._attr_device_class == NumberDeviceClass.POWER_FACTOR
        assert entity._attr_native_min_value == 0
        assert entity._attr_native_max_value == 10

    @pytest.mark.parametrize(
        "setting,expected", [(SETTING_KEY_OFF_SPEED, 0), (SETTING_KEY_ON_SPEED, 5)]
    )
    async def test_async_update_current_speed_value_Correct(
        self, setup, setting, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        entity: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, 1, setting
        )
        entity._handle_coordinator_update()

        assert entity._attr_native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("setting", [SETTING_KEY_OFF_SPEED, SETTING_KEY_ON_SPEED])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value(
        self, setup, setting, port, mocker: MockFixture
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        await entity.async_set_native_value(4)

        test_objects.set_mock.assert_called_with(str(DEVICE_ID), port, setting, 4)

    @pytest.mark.parametrize(
        "key", [SETTING_KEY_TIMER_DURATION_TO_ON, SETTING_KEY_TIMER_DURATION_TO_OFF]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_schedule_end_time_created_for_each_port(
        self, setup, key, port
    ):
        """Setting for scheduled end time created on setup"""

        sensor: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, key
        )

        assert "Minutes to" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"

    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_TIMER_DURATION_TO_ON, SETTING_KEY_TIMER_DURATION_TO_OFF]
    )
    @pytest.mark.parametrize(
        "value,expected",
        [(86400, 1440), (1440, 24), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_value_Correct(
        self,
        setup,
        setting,
        value,
        expected,
        port,
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][setting] = value
        sensor._handle_coordinator_update()

        assert sensor._attr_native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,field_value",
        [(86400, 1440), (1440, 24), (0, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_TIMER_DURATION_TO_ON, SETTING_KEY_TIMER_DURATION_TO_OFF]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_timer(
        self, setup, setting, expected: int, port, field_value
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        sensor: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )
        await sensor.async_set_native_value(field_value)

        test_objects.set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )

    @pytest.mark.parametrize(
        "key,label",
        [(SETTING_KEY_VPD_HIGH_TRIGGER, "High"), (SETTING_KEY_VPD_LOW_TRIGGER, "Low")],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_vpd_trigger_setup_for_each_port(
        self, setup, key, port, label
    ):
        """Setting for vpd trigger setup for each port"""

        sensor: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, key
        )

        assert f"VPD {label} Trigger" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"

    @pytest.mark.parametrize(
        "setting,enabled_setting",
        [
            (SETTING_KEY_VPD_LOW_TRIGGER, SETTING_KEY_VPD_LOW_ENABLED),
            (SETTING_KEY_VPD_HIGH_TRIGGER, SETTING_KEY_VPD_HIGH_ENABLED),
        ],
    )
    @pytest.mark.parametrize(
        "value,enabled,expected",
        [(55, 1, 5.5), (55, 0, 0), (0, 0, 0), (0, 1, 0)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_value_vpd(
        self, setup, setting, value, expected, port, enabled, enabled_setting
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][
            enabled_setting
        ] = enabled
        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][setting] = value
        sensor._handle_coordinator_update()

        assert sensor._attr_native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting, enabled",
        [
            (SETTING_KEY_VPD_LOW_TRIGGER, SETTING_KEY_VPD_LOW_ENABLED),
            (SETTING_KEY_VPD_HIGH_TRIGGER, SETTING_KEY_VPD_HIGH_ENABLED),
        ],
    )
    @pytest.mark.parametrize(
        "expected,value,prev_value",
        [((55, 1), 5.5, 45), ((45, 0), 0, 45)],  # minutes to seconds
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_vpd(
        self, setup, setting, value, expected, port, prev_value, enabled
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][
            setting
        ] = prev_value
        sensor: ACInfinityPortNumberEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )
        await sensor.async_set_native_value(value)

        leftValue, rightValue = expected

        test_objects.sets_mock.assert_called_with(
            str(DEVICE_ID), port, [(setting, leftValue), (enabled, rightValue)]
        )
