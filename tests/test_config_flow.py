import asyncio
from asyncio import Future
from datetime import timedelta
from types import MappingProxyType
from unittest.mock import ANY

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from pytest_mock import MockFixture

from custom_components.ac_infinity.client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
    ACInfinityClientRequestFailed,
)
from custom_components.ac_infinity.config_flow import (
    CONFIG_SCHEMA,
    ConfigFlow,
    OptionsFlow,
)
from custom_components.ac_infinity.const import (
    ConfigurationKey,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)
from custom_components.ac_infinity.core import ACInfinityService
from tests import ACTestObjects, setup_entity_mocks

from .data_models import (
    EMAIL, ENTRY_ID, PASSWORD, POLLING_INTERVAL, DEVICE_ID, AI_DEVICE_ID, DEVICE_NAME, DEVICE_NAME_AI,
    CONTROLLER_PROPERTIES_DATA, DEVICE_PROPERTIES_DATA, CONTROLLER_PROPERTIES, AI_CONTROLLER_PROPERTIES,
    DEVICE_PROPERTY_ONE, DEVICE_PROPERTY_TWO, DEVICE_PROPERTY_THREE, DEVICE_PROPERTY_FOUR
)

CONFIG_FLOW_USER_INPUT = {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
OPTION_FLOW_USER_INPUT = {ConfigurationKey.POLLING_INTERVAL: POLLING_INTERVAL}


@pytest.fixture(scope="function")
def setup_config_flow(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    test_objects: ACTestObjects = setup_entity_mocks(mocker)

    mocker.patch.object(config_entries.ConfigFlow, "async_show_form")
    mocker.patch.object(config_entries.ConfigFlow, "async_create_entry")
    mocker.patch.object(config_entries.ConfigFlow, "async_set_unique_id")
    mocker.patch.object(config_entries.ConfigFlow, "_abort_if_unique_id_configured")
    mocker.patch.object(ACInfinityClient, "login", return_value=future)
    mocker.patch.object(ACInfinityClient, "get_account_controllers", return_value=future)

    return mocker, test_objects


@pytest.fixture(scope="function")
def setup_options_flow(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    test_objects: ACTestObjects = setup_entity_mocks(mocker)

    mocker.patch.object(config_entries.OptionsFlow, "async_show_form")
    mocker.patch.object(config_entries.OptionsFlow, "async_show_menu")
    mocker.patch.object(config_entries.OptionsFlow, "async_create_entry")
    mocker.patch.object(ACInfinityClient, "login", return_value=future)
    mocker.patch.object(ACInfinityClient, "get_account_controllers", return_value=future)

    return mocker, test_objects


@pytest.mark.asyncio
class TestConfigFlow:
    async def test_async_step_user_form_shown(self, setup_config_flow):
        """When a user hasn't given any input yet, show the form"""

        _, test_objects = setup_config_flow
        flow = test_objects.config_flow

        await flow.async_step_user()

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_shown_again_on_connect_error(
        self, setup_config_flow
    ):
        """When a connect error occurs on login, reshow the form with error message"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        mocker.patch.object(
            ACInfinityClient, "login", side_effect=ACInfinityClientCannotConnect
        )

        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "cannot_connect"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_shown_again_on_auth_error(
        self, setup_config_flow
    ):
        """When an auth error occurs on login, reshow the form with error message"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        mocker.patch.object(
            ACInfinityClient, "login", side_effect=ACInfinityClientInvalidAuth
        )

        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "invalid_auth"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_shown_again_on_unknown_error(
        self, setup_config_flow
    ):
        """When an unknown error occurs on login, reshow the form with error message"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        mocker.patch.object(ACInfinityClient, "login", side_effect=Exception)

        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "unknown"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_successful_login_proceeds_to_enable_entities(
        self, setup_config_flow
    ):
        """When login is successful and devices are found, proceed to enable_entities step"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        # Mock the async_step_enable_entities method to return a form result
        mock_enable_entities = mocker.patch.object(
            flow, "async_step_enable_entities", return_value={"type": "form", "step_id": "enable_entities"}
        )

        # Mock ACInfinityService constructor and methods
        mock_service = mocker.MagicMock()
        mock_service.get_device_ids.return_value = [str(DEVICE_ID), str(AI_DEVICE_ID)]
        mock_service.refresh = mocker.AsyncMock()

        # Use mocker.patch instead of context manager
        mock_service_class = mocker.patch("custom_components.ac_infinity.config_flow.ACInfinityService")
        mock_service_class.return_value = mock_service

        result = await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        # Verify that enable_entities was called and its result returned
        mock_enable_entities.assert_called_once()
        assert result == {"type": "form", "step_id": "enable_entities"}

        # Verify form was not shown (successful path doesn't show user form)
        flow.async_show_form.assert_not_called()

        # Verify the service refresh was called
        mock_service.refresh.assert_called_once()

    async def test_async_step_user_successful_login_aborts_when_no_devices(
        self, setup_config_flow
    ):
        """When login is successful but no devices are found, abort with no_devices reason"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        # Mock ACInfinityService to return empty device list
        mock_service = mocker.MagicMock()
        mock_service.get_device_ids.return_value = []
        mock_service.refresh = mocker.AsyncMock()

        # Use mocker.patch instead of context manager
        mock_service_class = mocker.patch("custom_components.ac_infinity.config_flow.ACInfinityService")
        mock_service_class.return_value = mock_service

        result = await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        # Verify that the flow aborted with correct reason
        assert result["type"] == "abort"
        assert result["reason"] == "no_devices"

        # Verify form was not shown
        flow.async_show_form.assert_not_called()

        # Verify the service refresh was called
        mock_service.refresh.assert_called_once()

    async def test_config_flow_enable_entities_aborts_when_not_initialized(self, setup_config_flow):
        """When service is not initialized, enable_entities should abort"""
        _, test_objects = setup_config_flow
        flow = test_objects.config_flow

        # Don't set ac_infinity or device_ids to simulate uninitialized state
        result = await flow.async_step_enable_entities()

        assert result["type"] == "abort"
        assert result["reason"] == "not_initialized"

    async def test_config_flow_enable_entities_shows_form_without_user_input(self, setup_config_flow):
        """When called without user input, enable_entities should show form with entity options"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        # Set up the flow's internal state using getters/setters
        # Create a real ACInfinityService instance with mocked client
        mock_client = mocker.MagicMock()
        mock_service = ACInfinityService(mock_client)
        # Set up the service's internal data structures like the real service
        mock_service._controller_properties = CONTROLLER_PROPERTIES_DATA
        mock_service._device_properties = DEVICE_PROPERTIES_DATA

        flow.ac_infinity = mock_service
        flow.device_ids = [str(DEVICE_ID)]
        flow.device_index = 0
        flow.entities = {}

        await flow.async_step_enable_entities()

        # Verify the form is shown
        flow.async_show_form.assert_called_once()
        call_args = flow.async_show_form.call_args
        assert call_args[1]["step_id"] == "enable_entities"
        assert call_args[1]["errors"] == {}
        # Verify that description_placeholders contains expected device info
        placeholders = call_args[1]["description_placeholders"]
        assert placeholders["controller"] == DEVICE_NAME
        assert placeholders["device_code"] == CONTROLLER_PROPERTIES["devCode"]

    async def test_config_flow_enable_entities_continues_to_next_device(self, setup_config_flow):
        """When user provides input and more devices exist, continue to next device"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        # Set up the flow's internal state with multiple devices using getters/setters
        # Create a real ACInfinityService instance with mocked client
        mock_client = mocker.MagicMock()
        mock_service = ACInfinityService(mock_client)
        # Set up the service's internal data structures like the real service
        mock_service._controller_properties = CONTROLLER_PROPERTIES_DATA
        mock_service._device_properties = DEVICE_PROPERTIES_DATA

        flow.ac_infinity = mock_service
        flow.device_ids = [str(DEVICE_ID), str(AI_DEVICE_ID)]
        flow.device_index = 0  # First device
        flow.entities = {}

        user_input = {
            "controller": "all",
            "sensors": "sensors_only"
        }

        result = await flow.async_step_enable_entities(user_input)

        # Verify that entities were stored for the first device
        assert flow.entities[str(DEVICE_ID)] == user_input

        # Verify that device index was incremented
        assert flow.device_index == 1

        # Verify that the form is shown for the next device
        flow.async_show_form.assert_called_once()
        call_args = flow.async_show_form.call_args
        assert call_args[1]["step_id"] == "enable_entities"
        # Verify the second device's info is in placeholders (AI device)
        placeholders = call_args[1]["description_placeholders"]
        assert placeholders["controller"] == DEVICE_NAME_AI
        assert placeholders["device_code"] == AI_CONTROLLER_PROPERTIES["devCode"]

    async def test_config_flow_enable_entities_creates_entry_when_all_devices_processed(self, setup_config_flow):
        """When user provides input and all devices are processed, create config entry"""
        mocker, test_objects = setup_config_flow
        flow = test_objects.config_flow

        # Set up the flow's internal state - last device using getters/setters
        # Create a real ACInfinityService instance with mocked client
        mock_client = mocker.MagicMock()
        mock_service = ACInfinityService(mock_client)
        mocker.patch.object(mock_service, 'close', new_callable=mocker.AsyncMock)

        flow.ac_infinity = mock_service
        flow.device_ids = [str(DEVICE_ID), str(AI_DEVICE_ID)]
        flow.device_index = 1  # Last device (index 1 of 2 devices)
        flow.entities = {str(DEVICE_ID): {"controller": "all", "sensors": "sensors_only"}}
        flow.username = EMAIL
        flow.password = PASSWORD

        # Mock async_create_entry to return the expected result
        expected_result = {"type": "create_entry"}
        flow.async_create_entry.return_value = expected_result

        user_input = {
            "controller": "sensors_only",
            "sensors": "all"
        }

        result = await flow.async_step_enable_entities(user_input)

        # Verify that entities were stored for the last device
        assert flow.entities[str(AI_DEVICE_ID)] == user_input

        # Verify config entry was created
        flow.async_create_entry.assert_called_once()
        call_args = flow.async_create_entry.call_args

        # Check the title and data - title should be "AC Infinity (email)"
        assert call_args[1]["title"] == f"AC Infinity ({EMAIL})"
        config_data = call_args[1]["data"]
        assert config_data[CONF_EMAIL] == EMAIL
        assert config_data[CONF_PASSWORD] == PASSWORD
        assert config_data["entities"] == {
            str(DEVICE_ID): {"controller": "all", "sensors": "sensors_only"},
            str(AI_DEVICE_ID): {"controller": "sensors_only", "sensors": "all"}
        }

        # Verify the result type
        assert result == expected_result

    async def test_async_get_options_flow_returns_options_flow(self):
        """options flow returned from static method"""
        config_entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={},
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
        result = ConfigFlow.async_get_options_flow(config_entry)

        assert result is not None

    @pytest.mark.parametrize(
        "existing_value,expected_value",
        [(None, DEFAULT_POLLING_INTERVAL), (5, 5), (600, 600)],
    )
    async def test_options_flow_handler_show_form(
        self, setup_options_flow, existing_value, expected_value
    ):
        """If no user input provided, async_setup_init should show form with correct value"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={ConfigurationKey.POLLING_INTERVAL: existing_value},
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )

        mocker.patch.object(OptionsFlow, "config_entry", return_value=entry)

        await flow.async_step_general_config()

        flow.async_show_form.assert_called_with(
            step_id="general_config",
            data_schema=vol.Schema(
                {
                    vol.Required(ConfigurationKey.POLLING_INTERVAL, default=expected_value): int,
                    vol.Optional(ConfigurationKey.UPDATE_PASSWORD): str,
                }
            ),
            errors={},
        )
        flow.async_create_entry.assert_not_called()

    async def test_options_flow_handler_show_form_uninitialized(
        self, setup_options_flow
    ):
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        """If no user input provided, and no interval exists in settings, async_setup_init should show form with default value"""
        entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={},
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )

        mocker.patch.object(OptionsFlow, "config_entry", return_value=entry)

        await flow.async_step_general_config()

        flow.async_show_form.assert_called_with(
            step_id="general_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ConfigurationKey.POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): int,
                    vol.Optional(ConfigurationKey.UPDATE_PASSWORD): str,
                }
            ),
            errors={},
        )
        flow.async_create_entry.assert_not_called()

    @pytest.mark.parametrize("user_input", [0, -5, 4])
    async def test_options_flow_handler_show_form_with_error_polling_interval(
        self, setup_options_flow, user_input
    ):
        """If provided polling interval is not valid, show form with error"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={},
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )

        mocker.patch.object(OptionsFlow, "config_entry", return_value=entry)

        await flow.async_step_general_config({ConfigurationKey.POLLING_INTERVAL: user_input})

        flow.async_show_form.assert_called_with(
            step_id="general_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ConfigurationKey.POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): int,
                    vol.Optional(ConfigurationKey.UPDATE_PASSWORD): str,
                }
            ),
            errors={ConfigurationKey.POLLING_INTERVAL: "invalid_polling_interval"},
        )
        flow.async_create_entry.assert_not_called()

    @pytest.mark.parametrize("user_input", [5, 600, DEFAULT_POLLING_INTERVAL])
    async def test_options_flow_handler_update_config_and_data_coordinator(
        self, setup_options_flow, user_input
    ):
        """If provided polling interval is valid, update config and data coordinator with new value"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        await flow.async_step_general_config(
            {ConfigurationKey.POLLING_INTERVAL: user_input, ConfigurationKey.UPDATE_PASSWORD: "hunter2"}
        )

        flow.async_show_form.assert_not_called()
        # Verify that async_update_entry was called with the expected data including modified_at
        call_args = flow.hass.config_entries.async_update_entry.call_args
        assert call_args is not None
        assert call_args[1]['data'][CONF_EMAIL] == EMAIL
        assert call_args[1]['data'][ConfigurationKey.POLLING_INTERVAL] == user_input
        assert call_args[1]['data'][CONF_PASSWORD] == "hunter2"
        assert ConfigurationKey.MODIFIED_AT in call_args[1]['data']
        # Verify modified_at is a valid ISO timestamp
        from datetime import datetime
        datetime.fromisoformat(call_args[1]['data'][ConfigurationKey.MODIFIED_AT])

        assert test_objects.coordinator.update_interval == timedelta(seconds=user_input)

    async def test_restart_yes_sends_restart_signal(self, setup_options_flow):
        """The signal for restarting home assistant is called when user selects Restart Now"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        await flow.async_step_restart_yes(None)
        flow.hass.services.async_call.assert_called_with("homeassistant", "restart")

    async def test_restart_no_does_not_send_restart_signal(self, setup_options_flow):
        """The signal for restarting home assistant is called when user selects Restart Later"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        await flow.async_step_restart_no(None)
        flow.hass.services.async_call.assert_not_called()

    async def test_options_flow_handler_update_password_restart_dialog_shown(
        self, setup_options_flow
    ):
        """If user changed password, show restart dialog"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        await flow.async_step_general_config({ConfigurationKey.UPDATE_PASSWORD: "hunter2"})

        flow.async_show_menu.assert_called_with(
            step_id="notify_restart", menu_options=["restart_yes", "restart_no"]
        )
        flow.async_create_entry.assert_not_called()

    async def test_options_flow_handler_password_not_updated_restart_dialog_not_shown(
        self, setup_options_flow
    ):
        """If user does not change password, don't show restart dialog"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        await flow.async_step_general_config({ConfigurationKey.POLLING_INTERVAL: 10})

        flow.async_show_menu.assert_not_called()
        flow.async_create_entry.assert_called()

    async def test_options_flow_handler_preserves_existing_password_when_only_polling_interval_changed(
        self, mocker: MockFixture, setup_options_flow
    ):
        """When only polling interval is changed, existing password should be preserved"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        # Create a config entry with both email and password
        entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD, ConfigurationKey.POLLING_INTERVAL: 10},
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            state=ConfigEntryState.SETUP_IN_PROGRESS,
            subentries_data=None,
        )

        flow.config_entry = entry

        # Change only the polling interval, don't provide password
        await flow.async_step_general_config({ConfigurationKey.POLLING_INTERVAL: 15})

        # Verify the password is preserved in the updated config including modified_at
        call_args = flow.hass.config_entries.async_update_entry.call_args
        assert call_args is not None
        updated_data = call_args[1]['data']
        assert updated_data[CONF_EMAIL] == EMAIL
        assert updated_data[CONF_PASSWORD] == PASSWORD  # Original password should be preserved
        assert updated_data[ConfigurationKey.POLLING_INTERVAL] == 15
        assert ConfigurationKey.MODIFIED_AT in updated_data
        flow.async_show_menu.assert_not_called()
        flow.async_create_entry.assert_called()

    async def test_options_flow_init_shows_menu(self, setup_options_flow):
        """When async_step_init is called, it should show the options menu"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        await flow.async_step_init()

        flow.async_show_menu.assert_called_with(
            step_id="init", menu_options=["general_config", "controller_select"]
        )

    async def test_options_flow_controller_select_shows_form_with_devices(self, setup_options_flow):
        """When async_step_controller_select is called without user input, it should show form with device options"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        # Set up the service's internal data structures like the real service
        test_objects.coordinator.ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        await flow.async_step_controller_select()

        # Verify the form is shown with correct step_id
        flow.async_show_form.assert_called_once()
        call_args = flow.async_show_form.call_args
        assert call_args[1]["step_id"] == "controller_select"

        # Check that the schema contains a device_id field
        schema = call_args[1]["data_schema"]
        assert "device_id" in schema.schema

    async def test_options_flow_controller_select_aborts_when_no_devices(self, setup_options_flow):
        """When no devices are available, controller_select should abort"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        # Mock get_device_ids to return empty list
        mocker.patch.object(test_objects.coordinator.ac_infinity, "get_device_ids", return_value=[])

        result = await flow.async_step_controller_select()

        assert result["type"] == "abort"
        assert result["reason"] == "no_devices"
        flow.async_show_form.assert_not_called()

    async def test_options_flow_controller_select_proceeds_to_enable_entities_with_user_input(self, setup_options_flow):
        """When user selects a device, controller_select should proceed to enable_entities step"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        # Mock the async_step_enable_entities method
        mock_enable_entities = mocker.patch.object(flow, "async_step_enable_entities", return_value={"type": "form"})

        user_input = {"device_id": str(DEVICE_ID)}
        await flow.async_step_controller_select(user_input)

        # Verify that the device ID was stored and enable_entities was called
        assert flow.current_device_id == str(DEVICE_ID)
        mock_enable_entities.assert_called_once()

    async def test_options_flow_enable_entities_shows_form_without_user_input(self, setup_options_flow):
        """When async_step_enable_entities is called without user input, it should show form with entity options"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        # Set the current device ID
        flow.current_device_id = str(DEVICE_ID)

        # Set up the service's internal data structures like the real service
        test_objects.coordinator.ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        test_objects.coordinator.ac_infinity._device_properties = DEVICE_PROPERTIES_DATA

        await flow.async_step_enable_entities()

        # Verify the form is shown with correct step_id
        flow.async_show_form.assert_called_once()
        call_args = flow.async_show_form.call_args
        assert call_args[1]["step_id"] == "enable_entities"

        # Check that the schema contains expected fields
        schema = call_args[1]["data_schema"]
        assert "controller" in schema.schema
        assert "sensors" in schema.schema
        assert "port_1" in schema.schema
        assert "port_2" in schema.schema
        assert "port_3" in schema.schema
        assert "port_4" in schema.schema

        # Check description placeholders
        description_placeholders = call_args[1]["description_placeholders"]
        assert description_placeholders["controller"] == DEVICE_NAME
        assert description_placeholders["device_code"] == CONTROLLER_PROPERTIES["devCode"]
        assert description_placeholders["port_1"] == DEVICE_PROPERTY_ONE["portName"]
        assert description_placeholders["port_4"] == DEVICE_PROPERTY_FOUR["portName"]

    async def test_options_flow_enable_entities_creates_entities_config_if_missing(self, setup_options_flow):
        """When entities config doesn't exist in config entry, it should be created"""
        mocker, test_objects = setup_options_flow
        flow = test_objects.options_flow

        # Set the current device ID
        flow.current_device_id = str(DEVICE_ID)

        # Create a config entry without entities configuration
        from types import MappingProxyType
        entry_without_entities = ConfigEntry(
            entry_id=ENTRY_ID,
            data={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},  # No entities config
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
        flow.config_entry = entry_without_entities

        # Mock the async_step_notify_restart method
        mock_notify_restart = mocker.patch.object(flow, "async_step_notify_restart", return_value={"type": "menu"})

        user_input = {
            "controller": "all",
            "sensors": "sensors_only"
        }

        await flow.async_step_enable_entities(user_input)

        # Verify that entities config was created and populated
        call_args = flow.hass.config_entries.async_update_entry.call_args
        assert call_args is not None
        updated_data = call_args[1]['data']

        assert ConfigurationKey.ENTITIES in updated_data
        assert str(DEVICE_ID) in updated_data[ConfigurationKey.ENTITIES]
        assert updated_data[ConfigurationKey.ENTITIES][str(DEVICE_ID)] == user_input

    @pytest.mark.parametrize(
        "error,expected",
        [
            (ACInfinityClientCannotConnect, "cannot_connect"),
            (ACInfinityClientInvalidAuth, "invalid_auth"),
            (ACInfinityClientRequestFailed, "unknown"),
        ],
    )
    async def test_options_flow_handler_show_form_with_error_bad_password(
        self, mocker: MockFixture, setup_options_flow, error, expected
    ):
        """If provided polling interval is not valid, show form with error"""
        _, test_objects = setup_options_flow
        flow = test_objects.options_flow

        mocker.patch.object(ACInfinityClient, "login", side_effect=error)

        await flow.async_step_general_config({ConfigurationKey.UPDATE_PASSWORD: "hunter2"})

        flow.async_show_form.assert_called_with(
            step_id="general_config",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ConfigurationKey.POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): int,
                    vol.Optional(ConfigurationKey.UPDATE_PASSWORD): str,
                }
            ),
            errors={ConfigurationKey.UPDATE_PASSWORD: expected},
        )
        flow.hass.config_entries.async_update_entry.assert_not_called()
        flow.async_create_entry.assert_not_called()
