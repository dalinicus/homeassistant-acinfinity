import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    AdvancedSettingsKey,
    DeviceControlKey,
)
from custom_components.ac_infinity.select import (
    ACInfinityControllerSelectEntity,
    ACInfinityDeviceSelectEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
    execute_and_get_device_entity,
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

        assert len(test_objects.entities._added_entities) == 14

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
        [(DeviceControlKey.AT_TYPE, 8), (AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, 2)],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_mode_created_for_each_port(
        self, setup, port, setting, option_count
    ):
        """Sensor for device port mode created on setup"""

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            setting,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
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
            entity._controller, setting, expected
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
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.AT_TYPE,
        )

        test_objects.ac_infinity._device_controls[(str(DEVICE_ID), port)][
            DeviceControlKey.AT_TYPE
        ] = at_type
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
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
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.AT_TYPE,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        await entity.async_select_option(at_type_string)

        test_objects.port_control_set_mock.assert_called_with(
            entity._device, DeviceControlKey.AT_TYPE, expected
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
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
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
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        await entity.async_select_option(at_type_string)

        test_objects.port_setting_set_mock.assert_called_with(
            entity._device, AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize(
        "load_type,expected",
        [
            (None, "Grow Light"),
            (1, "Grow Light"),
            (2, "Humidifier"),
            (3, "Dehumidifier"),
            (4, "Heater"),
            (5, "AC"),
            (6, "Fan")
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_load_type_value_correct(
        self, setup, load_type, expected, port
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        )

        test_objects.ac_infinity._device_settings[(str(DEVICE_ID), port)][
            AdvancedSettingsKey.DEVICE_LOAD_TYPE
        ] = load_type
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        assert entity.current_option == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize(
        "expected,load_type_string",
        [
            (1, "Grow Light"),
            (2, "Humidifier"),
            (3, "Dehumidifier"),
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
        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        await entity.async_select_option(load_type_string)

        test_objects.port_setting_set_mock.assert_called_with(
            entity._device, AdvancedSettingsKey.DEVICE_LOAD_TYPE, expected
        )
        test_objects.refresh_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_load_type_unknown_device_type(
        self, setup, port
    ):
        """Error is thrown if device type is updated to an unknown value"""
        future: Future = asyncio.Future()
        future.set_result(None)

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DEVICE_LOAD_TYPE,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        with pytest.raises(ValueError):
            await entity.async_select_option("Pizza")

    @pytest.mark.parametrize(
        "setting",
        [
            AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE,
            AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE,
        ],
    )
    async def test_async_set_native_value_outside_climate_invalid_value(
        self, setup, setting
    ):
        """Error is thrown if outside climate is updated to an invalid value"""
        future: Future = asyncio.Future()
        future.set_result(None)

        entity = await execute_and_get_controller_entity(
            setup,
            async_setup_entry,
            setting,
        )

        assert isinstance(entity, ACInfinityControllerSelectEntity)
        with pytest.raises(ValueError):
            await entity.async_select_option("Invalid")

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_at_type_invalid_mode(
        self, setup, port
    ):
        """Error is thrown if mode is updated to an invalid value"""
        future: Future = asyncio.Future()
        future.set_result(None)

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            DeviceControlKey.AT_TYPE,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        with pytest.raises(ValueError):
            await entity.async_select_option("Invalid Mode")

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_set_native_value_dynamic_response_invalid_value(
        self, setup, port
    ):
        """Error is thrown if dynamic response type is updated to an invalid value"""
        future: Future = asyncio.Future()
        future.set_result(None)

        entity = await execute_and_get_device_entity(
            setup,
            async_setup_entry,
            port,
            AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE,
        )

        assert isinstance(entity, ACInfinityDeviceSelectEntity)
        with pytest.raises(ValueError):
            await entity.async_select_option("Invalid Response")


@pytest.mark.asyncio
class TestSuitableFunctions:
    """Test suitable_fn functions for select entities"""

    async def test_suitable_fn_device_setting_basic_controller_returns_true_for_non_ai(
        self, setup
    ):
        """Device setting entities should be suitable for non-AI controllers when setting exists"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        # Find a device load type entity (uses __suitable_fn_device_setting_basic_controller)
        # for the non-AI controller
        device_load_type_entities = [
            entity
            for entity in test_objects.entities.added_entities
            if MAC_ADDR in entity.unique_id
            and AdvancedSettingsKey.DEVICE_LOAD_TYPE in entity.unique_id
            and isinstance(entity, ACInfinityDeviceSelectEntity)
        ]

        # Should have 4 entities (one per port) for non-AI controller
        assert len(device_load_type_entities) == 4

    async def test_suitable_fn_device_setting_basic_controller_returns_false_for_ai(
        self, setup
    ):
        """Device setting entities should not be suitable for AI controllers"""
        from tests.data_models import AI_DEVICE_ID, AI_MAC_ADDR

        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        # Find device load type entities for the AI controller
        ai_device_load_type_entities = [
            entity
            for entity in test_objects.entities.added_entities
            if AI_MAC_ADDR in entity.unique_id
            and AdvancedSettingsKey.DEVICE_LOAD_TYPE in entity.unique_id
            and isinstance(entity, ACInfinityDeviceSelectEntity)
        ]

        # Should have 0 entities for AI controller (basic_controller suitable_fn returns False)
        assert len(ai_device_load_type_entities) == 0

    async def test_suitable_fn_device_control_default_returns_true_when_control_exists(
        self, setup
    ):
        """Device control entities should be suitable when control exists"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        # Find AT_TYPE entities (uses __suitable_fn_device_control_default)
        at_type_entities = [
            entity
            for entity in test_objects.entities.added_entities
            if MAC_ADDR in entity.unique_id
            and DeviceControlKey.AT_TYPE in entity.unique_id
            and isinstance(entity, ACInfinityDeviceSelectEntity)
        ]

        # Should have 4 entities (one per port)
        assert len(at_type_entities) == 4

    async def test_suitable_fn_controller_setting_default_returns_true_for_non_ai(
        self, setup
    ):
        """Controller setting entities should be suitable for non-AI controllers when setting exists"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        # Find outside climate entities (use __suitable_fn_controller_setting_default)
        outside_climate_entities = [
            entity
            for entity in test_objects.entities.added_entities
            if MAC_ADDR in entity.unique_id
            and (
                AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE in entity.unique_id
                or AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE in entity.unique_id
            )
            and isinstance(entity, ACInfinityControllerSelectEntity)
        ]

        # Should have 2 entities (temp and humidity) for non-AI controller
        assert len(outside_climate_entities) == 2

    async def test_suitable_fn_controller_setting_default_returns_false_for_ai(
        self, setup
    ):
        """Controller setting entities should not be suitable for AI controllers"""
        from tests.data_models import AI_MAC_ADDR

        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        # Find outside climate entities for AI controller
        ai_outside_climate_entities = [
            entity
            for entity in test_objects.entities.added_entities
            if AI_MAC_ADDR in entity.unique_id
            and (
                AdvancedSettingsKey.OUTSIDE_TEMP_COMPARE in entity.unique_id
                or AdvancedSettingsKey.OUTSIDE_HUMIDITY_COMPARE in entity.unique_id
            )
            and isinstance(entity, ACInfinityControllerSelectEntity)
        ]

        # Should have 0 entities for AI controller
        assert len(ai_outside_climate_entities) == 0
