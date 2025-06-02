"""Config flow for AC Infinity integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import section, SectionConfig
from homeassistant.helpers.selector import selector

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
    HOST, CONF_NUMBER_DISPLAY_TYPE, DEFAULT_NUMBER_DISPLAY_TYPE, ControllerPropertyKey, PortPropertyKey,
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
        return OptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            # noinspection PyBroadException
            client = ACInfinityClient(
                HOST, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            try:
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
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )


class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        return self.async_show_menu(
            step_id="init", menu_options=["integration_config", "entity_settings"]
        )

    async def async_step_integration_config(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            polling_interval = user_input.get(
                CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
            )
            password = user_input.get(CONF_UPDATE_PASSWORD, None)
            number_display_type = user_input.get(CONF_NUMBER_DISPLAY_TYPE, "auto")

            if polling_interval < 5:
                errors[CONF_POLLING_INTERVAL] = "invalid_polling_interval"

            if password:
                email = self.config_entry.data[CONF_EMAIL]
                # noinspection PyBroadException

                client = ACInfinityClient(
                    HOST,
                    email,
                    password,
                )

                try:
                    await client.login()
                    _ = await client.get_devices_list_all()
                except ACInfinityClientCannotConnect:
                    errors[CONF_UPDATE_PASSWORD] = "cannot_connect"
                except ACInfinityClientInvalidAuth:
                    errors[CONF_UPDATE_PASSWORD] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors[CONF_UPDATE_PASSWORD] = "unknown"
                finally:
                    await client.close()

            if not errors:
                prev_num_dis = self.__get_saved_conf_value(CONF_NUMBER_DISPLAY_TYPE, DEFAULT_NUMBER_DISPLAY_TYPE)

                new_data = self.config_entry.data.copy()
                new_data[CONF_POLLING_INTERVAL] = polling_interval
                new_data[CONF_NUMBER_DISPLAY_TYPE] = number_display_type
                if password:
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
                _LOGGER.info("Number display type changed to %s", number_display_type)

                if password or prev_num_dis != number_display_type:
                    return await self.async_step_notify_restart()
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="integration_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POLLING_INTERVAL, default=self.__get_saved_conf_value(CONF_POLLING_INTERVAL, CONF_POLLING_INTERVAL)): int,
                    vol.Required(CONF_NUMBER_DISPLAY_TYPE, default=self.__get_saved_conf_value(CONF_NUMBER_DISPLAY_TYPE, DEFAULT_NUMBER_DISPLAY_TYPE)): selector({
                        "select": {
                            "options": ["auto", "slider", "box"],
                            "mode": "dropdown"
                        }
                    }),
                    vol.Optional(CONF_UPDATE_PASSWORD): str
                }
            ),
            errors=errors
        )

    async def async_step_entity_settings(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            new_data = self.config_entry.data.copy()
            new_data["entity_settings"] = user_input

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )

            return await self.async_step_notify_restart()

        coordinator: ACInfinityDataUpdateCoordinator = self.hass.data[DOMAIN][
            self.config_entry.entry_id
        ]

        devices = {}
        device_keys = coordinator.ac_infinity.get_device_keys()
        for device_key in device_keys:
            port_count = coordinator.ac_infinity.get_controller_property(device_key, ControllerPropertyKey.PORT_COUNT)
            device_id = coordinator.ac_infinity.get_controller_property(device_key, ControllerPropertyKey.DEVICE_ID)
            device_name = coordinator.ac_infinity.get_controller_property(device_key, ControllerPropertyKey.DEVICE_NAME)

            ports = {}
            for i in range(1, port_count + 1):
                port_name = coordinator.ac_infinity.get_port_property(device_key, i, PortPropertyKey.NAME)
                ports[vol.Required(
                    f"port_{i}",
                    description=f"{device_name} {port_name} ({device_id}-{i})",
                    default=None)
                ] = selector({
                    "select": {
                        "options": [
                            { "value" : "all", "label": "All Entities" },
                            { "value": "sensors_and_controls", "label": "Sensors and Controls" },
                            { "value": "sensors_only", "label": "Sensors Only" },
                            { "value": "disable", "label": "Disable" }
                        ],
                        "mode": "dropdown",
                    }
                })

            devices[vol.Required(device_key, description=f"{device_name} ({device_id})")] = section(vol.Schema(ports))

        return self.async_show_form(
            step_id="entity_settings",
            data_schema=vol.Schema(devices),
            errors=errors
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

    def __get_saved_conf_value(self, conf_key:str, default):
        return (
            self.config_entry.data[conf_key]
            if conf_key in self.config_entry.data
               and self.config_entry.data[conf_key] is not None
            else default
        )

