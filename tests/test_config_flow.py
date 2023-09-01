import asyncio
from asyncio import Future

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.ac_infinity.client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
)
from custom_components.ac_infinity.config_flow import CONFIG_SCHEMA, ConfigFlow

from .data_models import EMAIL, PASSWORD

USER_INPUT = {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}


@pytest.fixture
def setup(mocker):
    future: Future = asyncio.Future()
    future.set_result(None)

    mocker.patch.object(config_entries.ConfigFlow, "async_show_form")
    mocker.patch.object(config_entries.ConfigFlow, "async_create_entry")
    mocker.patch.object(config_entries.ConfigFlow, "async_set_unique_id")
    mocker.patch.object(config_entries.ConfigFlow, "_abort_if_unique_id_configured")
    mocker.patch.object(ACInfinityClient, "login", return_value=future)
    mocker.patch.object(ACInfinityClient, "get_all_device_info", return_value=future)

    return mocker


@pytest.mark.asyncio
class TestConfigFlow:
    async def test_async_step_user_form_shown(self, setup):
        """When a user hasn't given any input yet, show the form"""

        flow = ConfigFlow()
        await flow.async_step_user()

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_reshown_shown_on_connect_error(self, setup):
        """When a connect error occurs on login, reshow the form with error message"""
        setup.patch.object(
            ACInfinityClient, "login", side_effect=ACInfinityClientCannotConnect
        )

        flow = ConfigFlow()
        await flow.async_step_user(USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "cannot_connect"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_reshown_shown_on_auth_error(self, setup):
        """When an auth error occurs on login, reshow the form with error message"""
        setup.patch.object(
            ACInfinityClient, "login", side_effect=ACInfinityClientInvalidAuth
        )

        flow = ConfigFlow()
        await flow.async_step_user(USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "invalid_auth"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_form_reshown_shown_on_unknown_error(self, setup):
        """When an unknown error occurs on login, reshow the form with error message"""
        setup.patch.object(ACInfinityClient, "login", side_effect=Exception)

        flow = ConfigFlow()
        await flow.async_step_user(USER_INPUT)

        flow.async_show_form.assert_called_with(
            step_id="user", data_schema=CONFIG_SCHEMA, errors={"base": "unknown"}
        )
        flow.async_create_entry.assert_not_called()

    async def test_async_step_user_config_entry_created_on_success(self, setup):
        """If client successfully logs in and gets data, then commit the config"""

        flow = ConfigFlow()
        await flow.async_step_user(USER_INPUT)

        flow.async_create_entry.assert_called()
        flow.async_show_form.assert_not_called()
