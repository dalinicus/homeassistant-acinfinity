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
    ACInfinityControllerSelectEntity,
    ACInfinityPortSelectEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
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

        assert len(test_objects.entities._added_entities) == 22

    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE,
            AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE,
        ],
    )
    async def test_async_setup_outside_climate_created(self, setup, setting):
        """Sensor for device port mode created on setup"""

        entity = await execute_and_get_controller_entity(
            setup,
            async_setup_entry,
            setting,
        )

        assert isinstance(entity, ACInfinityControllerSelectEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_{setting}"

        assert entity.entity_description.options is not None
        assert len(entity.entity_description.options) == 3
        assert entity.device_info is not None

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
        "value,expected",
        [(None, "Neutral"), (0, "Neutral"), (1, "Lower"), (2, "Higher")],
    )
    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE,
            AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE,
        ],
    )
    async def test_async_update_outside_climate_value_correct(
        self, setup, value, expected, setting
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup,
            async_setup_entry,
            setting,
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), 0)][setting] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSelectEntity)
        assert entity.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,value",
        [(0, "Neutral"), (1, "Lower"), (2, "Higher")],
    )
    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE,
            AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE,
        ],
    )
    async def test_async_set_native_value_outside_climate(
        self, setup, value, expected, setting
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup,
            async_setup_entry,
            setting,
        )

        assert isinstance(entity, ACInfinityControllerSelectEntity)
        await entity.async_select_option(value)

        test_objects.controller_set_mock.assert_called_with(
            str(DEVICE_ID), setting, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "at_type,expected",
        [
            (None, "Off"),
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
            (None, "Transition"),
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

        test_objects.port_setting_set_mock.assert_called_with(
            str(DEVICE_ID), port, AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "load_type,expected",
        [
            (None, "Grow Light"),
            (1, "Grow Light"),
            (2, "Humidifier"),
            (3, "Unknown Device Type"),
            (4, "Heater"),
            (5, "AC"),
            (6, "Fan"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_load_type_value_correct(
        self, setup, load_type, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            AdvancedSettingsKey.DEVICE_LOAD_TYPE
        ] = load_type
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSelectEntity)
        assert entity.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,load_type_string",
        [
            (1, "Grow Light"),
            (2, "Humidifier"),
            (4, "Heater"),
            (5, "AC"),
            (6, "Fan"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_load_type(
        self, setup, load_type_string, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        )

        assert isinstance(entity, ACInfinityPortSelectEntity)
        await entity.async_select_option(load_type_string)

        test_objects.port_setting_set_mock.assert_called_with(
            str(DEVICE_ID), port, AdvancedSettingsKey.DEVICE_LOAD_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_load_type_unknown_device_type(
        self, setup, port
    ):
        """Error is thrown if device type is updated to an unknown value"""
        future: Future = asyncio.Future()
        future.set_result(None)

        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        )

        assert isinstance(entity, ACInfinityPortSelectEntity)
        with pytest.raises(ValueError):
            await entity.async_select_option("Pizza")

    @pytest.mark.parametrize(
        "setting", [PortControlKey.AUTO_SETTINGS_MODE, PortControlKey.VPD_SETTINGS_MODE]
    )
    @pytest.mark.parametrize(
        "setting_mode,expected",
        [
            (None, "Auto"),
            (0, "Auto"),
            (1, "Target"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_settings_mode_value_correct(
        self, setup, setting_mode, expected, port, setting
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        test_objects.ac_infinity._port_controls[(str(DEVICE_ID), port)][
            setting
        ] = setting_mode
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityPortSelectEntity)
        assert entity.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "setting", [PortControlKey.AUTO_SETTINGS_MODE, PortControlKey.VPD_SETTINGS_MODE]
    )
    @pytest.mark.parametrize(
        "expected,setting_mode_string",
        [
            (0, "Auto"),
            (1, "Target"),
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_setting_mode(
        self, setup, setting_mode_string, expected, port, setting
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_port_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityPortSelectEntity)
        await entity.async_select_option(setting_mode_string)

        test_objects.port_control_set_mock.assert_called_with(
            str(DEVICE_ID), port, setting, expected
        )
        test_objects.refresh_mock.assert_called()
