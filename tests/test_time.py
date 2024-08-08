import asyncio
import datetime
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    SCHEDULE_DISABLED_VALUE,
    PortControlKey,
)
from custom_components.ac_infinity.time import (
    ACInfinityPortTimeEntity,
    async_setup_entry,
)
from tests import ACTestObjects, execute_and_get_port_entity, setup_entity_mocks
from tests.data_models import DEVICE_ID, MAC_ADDR


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestTimes:
    set_data_mode_value = 0

    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 8

    @pytest.mark.parametrize(
        "key", [PortControlKey.SCHEDULED_START_TIME, PortControlKey.SCHEDULED_END_TIME]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_schedule_end_time_created_for_each_port(
        self, setup, key, port
    ):
        """Setting for scheduled end time created on setup"""

        entity = await execute_and_get_port_entity(setup, async_setup_entry, port, key)

        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "setting",
        [PortControlKey.SCHEDULED_START_TIME, PortControlKey.SCHEDULED_END_TIME],
    )
    @pytest.mark.parametrize(
        "value,expected_hour,expected_minute",
        [(750, 12, 30), (0, 0, 0)],  # make sure midnight is not represented as None
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_value_correct(
        self,
        setup,
        setting,
        value,
        expected_hour,
        expected_minute,
        port,
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortTimeEntity)
        assert entity.native_value
        assert entity.native_value.hour == expected_hour
        assert entity.native_value.minute == expected_minute
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting",
        [PortControlKey.SCHEDULED_START_TIME, PortControlKey.SCHEDULED_END_TIME],
    )
    @pytest.mark.parametrize("value", [None, 1441, 65535])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_value_represents_disabled_correct(
        self, setup, setting, value, port
    ):
        """Reported sensor value is None (disabled) if the number of minutes is None or greater than 24 hours"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortTimeEntity)
        assert entity.native_value is None
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "value, expected",
        [(None, SCHEDULE_DISABLED_VALUE), (datetime.time(12, 30), 750)],
    )
    @pytest.mark.parametrize(
        "setting",
        [PortControlKey.SCHEDULED_START_TIME, PortControlKey.SCHEDULED_END_TIME],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value(
        self, setup, setting, value: datetime.time, expected: int, port
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup

        entity = await execute_and_get_port_entity(
            setup, async_setup_entry, port, setting
        )

        assert isinstance(entity, ACInfinityPortTimeEntity)
        await entity.async_set_value(value)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()
