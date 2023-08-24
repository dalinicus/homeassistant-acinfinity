"""Config flow for AC Infinity integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for AC Infinity."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = ACInfinityClient(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                await client.login()
                _ = await client.get_all_device_info()

            except ACInfinityClientCannotConnect:
                errors["base"] = "cannot_connect"
            except ACInfinityClientInvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"ac_infinity-{user_input[CONF_EMAIL]}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"AC Infinity ({user_input[CONF_EMAIL]})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )
