import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

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
from custom_components.ac_infinity.switch import (
    SCHEDULE_DISABLED_VALUE,
    SCHEDULE_EOD_VALUE,
    SCHEDULE_MIDNIGHT_VALUE,
    ACInfinityPortSwitchEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_port_entity,
    setup_entity_mocks,
)
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestSwitch:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.configEntry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 32

    @pytest.mark.parametrize(
        "setting",
        [
            SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED,
            SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED,
            SETTING_KEY_AUTO_TEMP_HIGH_ENABLED,
            SETTING_KEY_AUTO_TEMP_LOW_ENABLED,
            SETTING_KEY_VPD_HIGH_ENABLED,
            SETTING_KEY_VPD_LOW_ENABLED,
            SETTING_KEY_SCHEDULED_START_TIME,
            SETTING_KEY_SCHEDULED_END_TIME,
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_mode_created_for_each_port(self, setup, port, setting):
        """Sensor for device port mode created on setup"""

        sensor: ACInfinityPortSwitchEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"
        assert sensor.device_info is not None

    @pytest.mark.parametrize(
        "setting,value,expected",
        [
            # enabled
            (SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED, 1, True),
            (SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED, 1, True),
            (SETTING_KEY_AUTO_TEMP_HIGH_ENABLED, 1, True),
            (SETTING_KEY_AUTO_TEMP_LOW_ENABLED, 1, True),
            (SETTING_KEY_VPD_HIGH_ENABLED, 1, True),
            (SETTING_KEY_VPD_LOW_ENABLED, 1, True),
            (SETTING_KEY_SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            (SETTING_KEY_SCHEDULED_END_TIME, SCHEDULE_MIDNIGHT_VALUE, True),
            # disabled
            (SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED, 0, False),
            (SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED, 0, False),
            (SETTING_KEY_AUTO_TEMP_HIGH_ENABLED, 0, False),
            (SETTING_KEY_AUTO_TEMP_LOW_ENABLED, 0, False),
            (SETTING_KEY_VPD_HIGH_ENABLED, 0, False),
            (SETTING_KEY_VPD_LOW_ENABLED, 0, False),
            (SETTING_KEY_SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE, False),
            (SETTING_KEY_SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE, False),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_mode_value_Correct(
        self, setup, setting, expected, port, value
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortSwitchEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][setting] = value
        sensor._handle_coordinator_update()

        assert sensor.is_on == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            # enabled
            (SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED, 1),
            (SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED, 1),
            (SETTING_KEY_AUTO_TEMP_HIGH_ENABLED, 1),
            (SETTING_KEY_AUTO_TEMP_LOW_ENABLED, 1),
            (SETTING_KEY_VPD_HIGH_ENABLED, 1),
            (SETTING_KEY_VPD_LOW_ENABLED, 1),
            (SETTING_KEY_SCHEDULED_START_TIME, SCHEDULE_MIDNIGHT_VALUE),
            (SETTING_KEY_SCHEDULED_END_TIME, SCHEDULE_EOD_VALUE),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_on(self, setup, expected, port, setting):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortSwitchEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )
        await sensor.async_turn_on()

        test_objects.set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "setting,expected",
        [
            (SETTING_KEY_AUTO_HUMIDITY_HIGH_ENABLED, 0),
            (SETTING_KEY_AUTO_HUMIDITY_LOW_ENABLED, 0),
            (SETTING_KEY_AUTO_TEMP_HIGH_ENABLED, 0),
            (SETTING_KEY_AUTO_TEMP_LOW_ENABLED, 0),
            (SETTING_KEY_VPD_HIGH_ENABLED, 0),
            (SETTING_KEY_VPD_LOW_ENABLED, 0),
            (SETTING_KEY_SCHEDULED_START_TIME, SCHEDULE_DISABLED_VALUE),
            (SETTING_KEY_SCHEDULED_END_TIME, SCHEDULE_DISABLED_VALUE),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_turn_off(self, setup, expected, port, setting):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortSwitchEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )
        await sensor.async_turn_off()

        test_objects.set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()
