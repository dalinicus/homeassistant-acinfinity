import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    PortControlKey,
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
class TestSelectors:
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
        "setting,option_count",
        [(PortControlKey.AT_TYPE, 8), (AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, 2)],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_mode_created_for_each_port(
        self, setup, port, setting, option_count
    ):
        """Sensor for device port mode created on setup"""

        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityPortSelectEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{setting}"

        assert entity.entity_description.options is not None
        assert len(entity.entity_description.options) == option_count
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "at_type,expected",
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
    async def test_async_update_mode_value_correct(
        self, setup, at_type, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            PortControlKey.AT_TYPE,
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][
            PortControlKey.AT_TYPE
        ] = at_type
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSelectEntity)
        assert entity.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,at_type_string",
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
    async def test_async_set_native_value_at_type(
        self, setup, at_type_string, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            PortControlKey.AT_TYPE,
        )

        assert isinstance(entity, ACInfinityPortSelectEntity)
        await entity.async_select_option(at_type_string)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, PortControlKey.AT_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, "Transition"),
            (1, "Buffer"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_dynamic_response_value_correct(
        self, setup, value, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSelectEntity)
        assert entity.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,at_type_string",
        [
            (0, "Transition"),
            (1, "Buffer"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_dynamic_response(
        self, setup, at_type_string, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        )

        assert isinstance(entity, ACInfinityPortSelectEntity)
        await entity.async_select_option(at_type_string)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()
