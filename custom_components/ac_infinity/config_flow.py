"""Config flow for AC Infinity integration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import section, SectionConfig
from homeassistant.helpers.selector import selector, Selector

from custom_components.ac_infinity import ACInfinityDataUpdateCoordinator
from custom_components.ac_infinity.client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
)
from . import ACInfinityService

from .const import (
    ConfigurationKey,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    HOST, ControllerPropertyKey, PortPropertyKey, EntityConfigValue,
)

_LOGGER = logging.getLogger(__name__)

# Individual entity configuration option constants
OPTION_ALL_ENTITIES = {"value": EntityConfigValue.All, "label": "All Entities"}
OPTION_SENSORS_AND_CONTROLS = {"value": EntityConfigValue.SensorsAndControls, "label": "Sensors and Controls"}
OPTION_SENSORS_ONLY = {"value": EntityConfigValue.SensorsOnly, "label": "Sensors Only"}
OPTION_DISABLE = {"value": EntityConfigValue.Disable, "label": "Disable"}

# Entity configuration option arrays
ENTITY_CONFIG_OPTIONS_CONTROLLER = [
    OPTION_ALL_ENTITIES,
    OPTION_SENSORS_ONLY,
    OPTION_DISABLE
]

ENTITY_CONFIG_OPTIONS_SENSORS = [
    OPTION_ALL_ENTITIES,
    OPTION_DISABLE
]

ENTITY_CONFIG_OPTIONS_PORTS = [
    OPTION_ALL_ENTITIES,
    OPTION_SENSORS_AND_CONTROLS,
    OPTION_SENSORS_ONLY,
    OPTION_DISABLE
]

CONFIG_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for AC Infinity."""

    VERSION = 1

    def __init__(self):
        self.__ac_infinity: ACInfinityService | None = None

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
                self.__ac_infinity = ACInfinityService(client)

            except ACInfinityClientCannotConnect:
                errors["base"] = "cannot_connect"
            except ACInfinityClientInvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # await self.async_set_unique_id(f"ac_infinity-{user_input[CONF_EMAIL]}")
                # self._abort_if_unique_id_configured()

                # return self.async_create_entry(
                #    title=f"AC Infinity ({user_input[CONF_EMAIL]})", data=user_input
                #)
                return await self.async_step_entities()

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    async def async_step_entities(self, user_input: dict[str, Any] | None = None):

        errors: dict[str, str] = {}
        if user_input is not None:
            raise NotImplementedError()


class OptionsFlow(config_entries.OptionsFlow):

    def __init__(self):
        self.__current_device_id: str | int = 0

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        return self.async_show_menu(
            step_id="init", menu_options=["general_config", "controller_select"]
        )

    async def async_step_general_config(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            polling_interval = user_input.get(
                ConfigurationKey.POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
            )
            password: str | None = user_input.get(ConfigurationKey.UPDATE_PASSWORD, None)

            if polling_interval < 5:
                errors[ConfigurationKey.POLLING_INTERVAL] = "invalid_polling_interval"

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
                    errors[ConfigurationKey.UPDATE_PASSWORD] = "cannot_connect"
                except ACInfinityClientInvalidAuth:
                    errors[ConfigurationKey.UPDATE_PASSWORD] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors[ConfigurationKey.UPDATE_PASSWORD] = "unknown"
                finally:
                    await client.close()

            if not errors:

                new_data = self.config_entry.data.copy()
                new_data[ConfigurationKey.POLLING_INTERVAL] = polling_interval
                if password:
                    new_data[CONF_PASSWORD] = password

                self.__update_config_entry_data(new_data)

                coordinator: ACInfinityDataUpdateCoordinator = self.hass.data[DOMAIN][
                    self.config_entry.entry_id
                ]
                coordinator.update_interval = timedelta(seconds=polling_interval)

                _LOGGER.info("Polling Interval changed to %s seconds", polling_interval)

                if password:
                    return await self.async_step_notify_restart()
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="general_config",
            data_schema=vol.Schema(
                {
                    vol.Required(ConfigurationKey.POLLING_INTERVAL,
                                 default=self.__get_saved_conf_value(ConfigurationKey.POLLING_INTERVAL,
                                                                     DEFAULT_POLLING_INTERVAL)): int,
                    vol.Optional(ConfigurationKey.UPDATE_PASSWORD): str
                }
            ),
            errors=errors
        )

    async def async_step_controller_select(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self.__current_device_id = user_input["device_id"]
            return await self.async_step_entity_settings()

        coordinator: ACInfinityDataUpdateCoordinator = self.hass.data[DOMAIN][
            self.config_entry.entry_id
        ]

        device_ids = coordinator.ac_infinity.get_device_ids()
        if not device_ids:
            return self.async_abort(reason="no_devices")

        options = []
        for device_id in device_ids:
            device_code = coordinator.ac_infinity.get_controller_property(device_id, ControllerPropertyKey.DEVICE_CODE)
            device_name = coordinator.ac_infinity.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME)

            options.append({"value": device_id, "label": f"{device_name} ({device_code})"})

        return self.async_show_form(
            step_id="controller_select",
            data_schema=vol.Schema({
                vol.Required("device_id"): selector({
                    "select": {
                        "options": options
                    }
                })
            }),
        )

    async def async_step_entity_settings(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        device_id: str | int = self.__current_device_id

        if user_input is not None:
            new_data = self.config_entry.data.copy()
            if ConfigurationKey.ENTITIES not in new_data:
                new_data[ConfigurationKey.ENTITIES] = {}

            new_data[ConfigurationKey.ENTITIES][str(self.__current_device_id)] = user_input
            self.__update_config_entry_data(new_data)

            return await self.async_step_notify_restart()

        ac_infinity: ACInfinityService = self.hass.data[DOMAIN][
            self.config_entry.entry_id
        ].ac_infinity

        device_name = ac_infinity.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME)
        port_count = ac_infinity.get_controller_property(device_id, ControllerPropertyKey.PORT_COUNT)

        entities = {}
        description_placeholders = {
            "controller": device_name
        }

        entities[
            vol.Required("controller",
                         default=self.__get_saved_entity_conf_value(str(device_id), "controller"))] = selector(
            {
                "select": {
                    "options": ENTITY_CONFIG_OPTIONS_CONTROLLER,
                    "mode": "dropdown"
                }
            })

        entities[
            vol.Required("sensors", default=self.__get_saved_entity_conf_value(str(device_id), "sensors"))] = selector({
            "select": {
                "options": ENTITY_CONFIG_OPTIONS_SENSORS,
                "mode": "dropdown"
            }
        })

        for i in range(1, port_count + 1):
            entity_config_key = f"port_{i}"
            description_placeholders[entity_config_key] = ac_infinity.get_port_property(device_id, i,
                                                                                                    PortPropertyKey.NAME)
            entities[vol.Required(entity_config_key,
                                  default=self.__get_saved_entity_conf_value(str(device_id),
                                                                             entity_config_key))] = selector(
                {
                    "select": {
                        "options": ENTITY_CONFIG_OPTIONS_PORTS,
                        "mode": "dropdown"
                    }
                })

        return self.async_show_form(
            step_id="entity_settings",
            data_schema=vol.Schema(entities),
            errors=errors,
            description_placeholders=description_placeholders
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

    def __update_config_entry_data(self, new_data: dict[str, Any]) -> None:
        """Update config entry data with modified timestamp."""
        new_data[ConfigurationKey.MODIFIED_AT] = datetime.now().isoformat()
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=new_data,
        )

    def __get_saved_conf_value(self, conf_key: str, default):
        return (
            self.config_entry.data[conf_key]
            if conf_key in self.config_entry.data
               and self.config_entry.data[conf_key] is not None
            else default
        )

    def __get_saved_entity_conf_value(self, device_id: str, entity_config_key: str):
        return (
            self.config_entry.data[ConfigurationKey.ENTITIES][device_id][entity_config_key]
            if ConfigurationKey.ENTITIES in self.config_entry.data
               and self.config_entry.data[ConfigurationKey.ENTITIES] is not None
               and device_id in self.config_entry.data[ConfigurationKey.ENTITIES]
               and self.config_entry.data[ConfigurationKey.ENTITIES][device_id] is not None
               and entity_config_key in self.config_entry.data[ConfigurationKey.ENTITIES][device_id]
               and self.config_entry.data[ConfigurationKey.ENTITIES][device_id][entity_config_key] is not None
            else EntityConfigValue.All
        )
