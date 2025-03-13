import asyncio
from asyncio import Future
from datetime import timedelta
from types import MappingProxyType
from unittest.mock import ANY

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
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
    CONF_POLLING_INTERVAL,
    CONF_UPDATE_PASSWORD,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)
from tests import ACTestObjects, setup_entity_mocks

from .data_models import EMAIL, ENTRY_ID, PASSWORD, POLLING_INTERVAL

CONFIG_FLOW_USER_INPUT = {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
OPTION_FLOW_USER_INPUT = {CONF_POLLING_INTERVAL: POLLING_INTERVAL}


@pytest.fixture
def setup_config_flow(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    mocker.patch.object(config_entries.ConfigFlow, "async_show_form")
    mocker.patch.object(config_entries.ConfigFlow, "async_create_entry")
    mocker.patch.object(config_entries.ConfigFlow, "async_set_unique_id")
    mocker.patch.object(config_entries.ConfigFlow, "_abort_if_unique_id_configured")
    mocker.patch.object(ACInfinityClient, "login", return_value=future)
    mocker.patch.object(ACInfinityClient, "get_devices_list_all", return_value=future)

    return mocker


@pytest.fixture
def setup_mocks(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.fixture
def setup_options_flow(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    mocker.patch.object(config_entries.OptionsFlow, "async_show_form")
    mocker.patch.object(config_entries.OptionsFlow, "async_show_menu")
    mocker.patch.object(config_entries.OptionsFlow, "async_create_entry")
    mocker.patch.object(ACInfinityClient, "login", return_value=future)
    mocker.patch.object(ACInfinityClient, "get_devices_list_all", return_value=future)

    return mocker


@pytest.mark.asyncio
class TestConfigFlow:
    async def test_async_step_user_form_shown(self, setup_config_flow):
        """When a user hasn't given any input yet, show the form"""

        flow = ConfigFlow()
        await flow.async_step_user()

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_shown_again_on_connect_error(
        self, setup_config_flow
    ):
        """When a connect error occurs on login, reshow the form with error message"""
        setup_config_flow.patch.object(
            ACInfinityClient, "login", side_effect=ACInfinityClientCannotConnect
        )

        flow = ConfigFlow()
        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "cannot_connect"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_shown_again_on_auth_error(
        self, setup_config_flow
    ):
        """When an auth error occurs on login, reshow the form with error message"""
        setup_config_flow.patch.object(
            ACInfinityClient, "login", side_effect=ACInfinityClientInvalidAuth
        )

        flow = ConfigFlow()
        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "invalid_auth"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_shown_again_on_unknown_error(
        self, setup_config_flow
    ):
        """When an unknown error occurs on login, reshow the form with error message"""
        setup_config_flow.patch.object(ACInfinityClient, "login", side_effect=Exception)

        flow = ConfigFlow()
        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "unknown"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_config_entry_created_on_success(
        self, setup_config_flow
    ):
        """If client successfully logs in and gets data, then commit the config"""

        flow = ConfigFlow()
        await flow.async_step_user(CONFIG_FLOW_USER_INPUT)

        flow.async_create_entry.assert_called()
        flow.async_show_form.assert_not_called()

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
        mocker = setup_options_flow
        entry = ConfigEntry(
            entry_id=ENTRY_ID,
            data={CONF_POLLING_INTERVAL: existing_value},
            domain=DOMAIN,
            minor_version=0,
            source="",
            title="",
            version=0,
            options=None,
            unique_id=None,
            discovery_keys=MappingProxyType({}),
        )

        flow = OptionsFlow()
        mocker.patch.object(OptionsFlow, "config_entry", return_value=entry)

        await flow.async_step_init()

        flow.async_show_form.assert_called_with(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_POLLING_INTERVAL, default=expected_value): int,
                    vol.Optional(CONF_UPDATE_PASSWORD): str,
                }
            ),
            errors={},
        )
        flow.async_create_entry.assert_not_called()

    async def test_options_flow_handler_show_form_uninitialized(
        self, setup_options_flow
    ):
        mocker = setup_options_flow
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
        )

        flow = OptionsFlow()
        mocker.patch.object(OptionsFlow, "config_entry", return_value=entry)

        await flow.async_step_init()

        flow.async_show_form.assert_called_with(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): int,
                    vol.Optional(CONF_UPDATE_PASSWORD): str,
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
        mocker = setup_options_flow
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
        )

        flow = OptionsFlow()
        mocker.patch.object(OptionsFlow, "config_entry", return_value=entry)

        await flow.async_step_init({CONF_POLLING_INTERVAL: user_input})

        flow.async_show_form.assert_called_with(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): int,
                    vol.Optional(CONF_UPDATE_PASSWORD): str,
                }
            ),
            errors={CONF_POLLING_INTERVAL: "invalid_polling_interval"},
        )
        flow.async_create_entry.assert_not_called()

    @pytest.mark.parametrize("user_input", [5, 600, DEFAULT_POLLING_INTERVAL])
    async def test_options_flow_handler_update_config_and_data_coordinator(
        self, setup_options_flow, user_input, setup_mocks
    ):
        """If provided polling interval is valid, update config and data coordinator with new value"""
        test_objects: ACTestObjects = setup_mocks
        flow = test_objects.options_flow

        await flow.async_step_init(
            {CONF_POLLING_INTERVAL: user_input, CONF_UPDATE_PASSWORD: "hunter2"}
        )

        flow.async_show_form.assert_not_called()
        flow.hass.config_entries.async_update_entry.assert_called_with(
            ANY,
            data={
                CONF_EMAIL: "ac_infinity-myemail@unittest.com",
                CONF_POLLING_INTERVAL: user_input,
                CONF_PASSWORD: "hunter2",
            },
        )

        assert test_objects.coordinator.update_interval == timedelta(seconds=user_input)

    async def test_restart_yes_sends_restart_signal(
        self, setup_options_flow, setup_mocks
    ):
        """The signal for restarting home assistant is called when user selects Restart Now"""
        test_objects: ACTestObjects = setup_mocks
        flow = test_objects.options_flow

        await flow.async_step_restart_yes(None)
        flow.hass.services.async_call.assert_called_with("homeassistant", "restart")

    async def test_restart_no_does_not_send_restart_signal(
        self, setup_options_flow, setup_mocks
    ):
        """The signal for restarting home assistant is called when user selects Restart Later"""
        test_objects: ACTestObjects = setup_mocks
        flow = test_objects.options_flow

        await flow.async_step_restart_no(None)
        flow.hass.services.async_call.assert_not_called()

    async def test_options_flow_handler_update_password_restart_dialog_shown(
        self, setup_options_flow, setup_mocks
    ):
        """If user changed password, show restart dialog"""
        test_objects: ACTestObjects = setup_mocks
        flow = test_objects.options_flow

        await flow.async_step_init({CONF_UPDATE_PASSWORD: "hunter2"})

        flow.async_show_menu.assert_called_with(
            step_id="notify_restart", menu_options=["restart_yes", "restart_no"]
        )
        flow.async_create_entry.assert_not_called()

    async def test_options_flow_handler_password_not_updated_restart_dialog_not_shown(
        self, setup_options_flow, setup_mocks
    ):
        """If user does not change password, don't show restart dialog"""
        test_objects: ACTestObjects = setup_mocks
        flow = test_objects.options_flow

        await flow.async_step_init({CONF_POLLING_INTERVAL: 10})

        flow.async_show_menu.assert_not_called()
        flow.async_create_entry.assert_called()

    @pytest.mark.parametrize(
        "error,expected",
        [
            (ACInfinityClientCannotConnect, "cannot_connect"),
            (ACInfinityClientInvalidAuth, "invalid_auth"),
            (ACInfinityClientRequestFailed, "unknown"),
        ],
    )
    async def test_options_flow_handler_show_form_with_error_bad_password(
        self, mocker: MockFixture, setup_options_flow, setup_mocks, error, expected
    ):
        """If provided polling interval is not valid, show form with error"""

        test_objects: ACTestObjects = setup_mocks
        flow = test_objects.options_flow

        mocker.patch.object(ACInfinityClient, "login", side_effect=error)

        await flow.async_step_init({CONF_UPDATE_PASSWORD: "hunter2"})

        flow.async_show_form.assert_called_with(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): int,
                    vol.Optional(CONF_UPDATE_PASSWORD): str,
                }
            ),
            errors={CONF_UPDATE_PASSWORD: expected},
        )
        flow.hass.config_entries.async_update_entry.assert_not_called()
        flow.async_create_entry.assert_not_called()
