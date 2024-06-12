"""Config flow for AC Infinity integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from custom_components.ac_infinity import ACInfinityDataUpdateCoordinator
from custom_components.ac_infinity.client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
)

from .const import (
    CONF_POLLING_INTERVAL,
    CONF_UPDATE_PASSWORD,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    HOST,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for AC Infinity."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            # noinspection PyBroadException
            try:
                client = ACInfinityClient(
                    HOST, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                await client.login()
                _ = await client.get_devices_list_all()

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


class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        errors: dict[str, str] = {}
        if user_input is not None:
            polling_interval = user_input.get(
                CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
            )
            password = user_input.get(CONF_UPDATE_PASSWORD, None)

            if polling_interval < 5:
                errors[CONF_POLLING_INTERVAL] = "invalid_polling_interval"

            if password:
                email = self.config_entry.data[CONF_EMAIL]
                # noinspection PyBroadException
                try:
                    client = ACInfinityClient(
                        HOST,
                        email,
                        password,
                    )
                    await client.login()
                    _ = await client.get_devices_list_all()
                except ACInfinityClientCannotConnect:
                    errors[CONF_UPDATE_PASSWORD] = "cannot_connect"
                except ACInfinityClientInvalidAuth:
                    errors[CONF_UPDATE_PASSWORD] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors[CONF_UPDATE_PASSWORD] = "unknown"

            if not len(errors):
                new_data = self.config_entry.data.copy()
                new_data[CONF_POLLING_INTERVAL] = polling_interval
                new_data[CONF_PASSWORD] = password

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )

                coordinator: ACInfinityDataUpdateCoordinator = self.hass.data[DOMAIN][
                    self.config_entry.entry_id
                ]
                coordinator.update_interval = timedelta(seconds=polling_interval)

                _LOGGER.info("Polling Interval changed to %s seconds", polling_interval)
                if password:
                    return await self.async_step_notify_restart()
                return self.async_create_entry(title="", data={})

        cur_value = (
            int(self.config_entry.data[CONF_POLLING_INTERVAL])
            if CONF_POLLING_INTERVAL in self.config_entry.data
            and self.config_entry.data[CONF_POLLING_INTERVAL] is not None
            else DEFAULT_POLLING_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_POLLING_INTERVAL, default=cur_value): int,
                    vol.Optional(CONF_UPDATE_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_notify_restart(self):
        return self.async_show_menu(
            step_id="notify_restart", menu_options=["restart_yes", "restart_no"]
        )

    async def async_step_restart_yes(self, _):
        await self.hass.services.async_call("homeassistant", "restart")
        return self.async_create_entry(title="", data={})

    async def async_step_restart_no(self, _):
        return self.async_create_entry(title="", data={})
