import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_AT_TYPE,
)
from custom_components.ac_infinity.select import (
    ACInfinityPortSelectEntity,
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
class TestNumbers:
    set_data_mode_value = 0

    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.configEntry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 4

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_mode_created_for_each_port(self, setup, port):
        """Sensor for device port mode created on setup"""

        sensor: ACInfinityPortSelectEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            SETTING_KEY_AT_TYPE,
        )

        assert (
            sensor.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{SETTING_KEY_AT_TYPE}"
        )
        assert len(sensor.entity_description.options) == 8

    @pytest.mark.parametrize(
        "atType,expected",
        [
            (1, "Off"),
            (2, "On"),
            (3, "Auto"),
            (4, "Timer to On"),
            (5, "Timer to Off"),
            (6, "Cycle"),
            (7, "Schedule"),
            (8, "VPD"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_mode_value_Correct(
        self, setup, mocker: MockFixture, atType, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortSelectEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            SETTING_KEY_AT_TYPE,
        )

        test_objects.ac_infinity._port_settings[str(DEVICE_ID)][port][
            SETTING_KEY_AT_TYPE
        ] = atType
        sensor._handle_coordinator_update()

        assert sensor.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,atTypeString",
        [
            (1, "Off"),
            (2, "On"),
            (3, "Auto"),
            (4, "Timer to On"),
            (5, "Timer to Off"),
            (6, "Cycle"),
            (7, "Schedule"),
            (8, "VPD"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value(
        self, mocker: MockFixture, setup, atTypeString, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        sensor: ACInfinityPortSelectEntity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            SETTING_KEY_AT_TYPE,
        )
        await sensor.async_select_option(atTypeString)

        test_objects.set_mock.assert_called_with(
            str(DEVICE_ID), port, SETTING_KEY_AT_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()
