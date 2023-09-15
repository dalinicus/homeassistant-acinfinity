import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_ACTIVE_TIMER_OFF,
    SETTING_KEY_ACTIVE_TIMER_ON,
)
from custom_components.ac_infinity.text import (
    ACInfinityPortTimerEntity,
    async_setup_entry,
)
from tests import ACTestObjects, execute_and_get_port_entity, setup_entity_mocks
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestText:
    set_data_mode_value = 0

    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.configEntry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 8

    @pytest.mark.parametrize(
        "key", [SETTING_KEY_ACTIVE_TIMER_ON, SETTING_KEY_ACTIVE_TIMER_OFF]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_schedule_end_time_created_for_each_port(
        self, setup, key, port
    ):
        """Setting for scheduled end time created on setup"""

        sensor: ACInfinityPortTimerEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, key
        )

        assert "Minutes to" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"

    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_ACTIVE_TIMER_ON, SETTING_KEY_ACTIVE_TIMER_OFF]
    )
    @pytest.mark.parametrize(
        "value,expected",
        [(86400, "1440"), (1440, "24"), (0, "0")],  # minutes to seconds
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
        sensor: ACInfinityPortTimerEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][setting] = value
        sensor._handle_coordinator_update()

        assert sensor._attr_native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,field_value",
        [(86400, "1440"), (1440, "24"), (0, "0")],  # minutes to seconds
    )
    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_ACTIVE_TIMER_ON, SETTING_KEY_ACTIVE_TIMER_OFF]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value(
        self, setup, setting, expected: int, port, field_value
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        sensor: ACInfinityPortTimerEntity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )
        await sensor.async_set_value(field_value)

        test_objects.set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
