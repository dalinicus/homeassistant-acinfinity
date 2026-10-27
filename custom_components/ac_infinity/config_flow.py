"""Config flow for AC Infinity integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import probatio as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import selector
from probatio import Required

from custom_components.ac_infinity.client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
)
from . import ACInfinityService
from .core import ACInfinityData, ACInfinityEntryData
from .calibration import async_calibrate, read_reference
from .entity_filter import async_filter_schema
from .const import (
    ConfigurationKey,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    HOST, ControllerPropertyKey, DevicePropertyKey, EntityConfigValue,
)

_LOGGER = logging.getLogger(__name__)

# Individual entity configuration option constants
OPTION_ALL_ENTITIES = {"value": EntityConfigValue.ALL, "label": "Sensors, Controls, and Settings"}
OPTION_SENSORS_AND_SETTINGS = {"value": EntityConfigValue.SENSORS_AND_SETTINGS, "label": "Sensors and Settings"}
OPTION_SENSORS_AND_CONTROLS = {"value": EntityConfigValue.SENSORS_AND_CONTROLS, "label": "Sensors and Controls"}
OPTION_SENSORS_ONLY = {"value": EntityConfigValue.SENSORS_ONLY, "label": "Sensors Only"}
OPTION_DISABLE = {"value": EntityConfigValue.DISABLE, "label": "Disable"}

# Entity configuration option arrays
ENTITY_CONFIG_OPTIONS_CONTROLLER = [
    OPTION_SENSORS_AND_SETTINGS,
    OPTION_SENSORS_ONLY,
    OPTION_DISABLE
]

ENTITY_CONFIG_OPTIONS_SENSORS = [
    OPTION_SENSORS_ONLY,
    OPTION_DISABLE
]

ENTITY_CONFIG_OPTIONS_DEVICES = [
    OPTION_ALL_ENTITIES,
    OPTION_SENSORS_AND_CONTROLS,
    OPTION_SENSORS_ONLY,
    OPTION_DISABLE
]

CONFIG_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


NUMBER_DISPLAY_TYPE_SELECTOR = selector({
    "select": {
        "options": [
            {"value": "auto", "label": "Automatic (each entity's default)"},
            {"value": "box", "label": "Box (type a number)"},
            {"value": "slider", "label": "Slider"},
        ],
        "mode": "list",
    }
})


class ACInfinityFlowBase:
    """Base class for AC Infinity config and options flows."""

    @staticmethod
    def __get_saved_entity_conf_value(data: dict[str, Any] | None, device_id: str, entity_config_key: str):
        """Get saved entity configuration value from config entry data."""
        if data is None:
            # ConfigFlow - we are setting the integration up for the first time.  Don't add excessive entities.
            return EntityConfigValue.SENSORS_ONLY

        # devices / ports added to the account after setup have no saved value yet
        return (
            data.get(ConfigurationKey.ENTITIES, {})
            .get(device_id, {})
            .get(entity_config_key, EntityConfigValue.SENSORS_ONLY)
        )

    def _build_entity_config_schema(
        self,
        service: ACInfinityService,
        device_id: str | int,
        data: dict[str, Any] | None = None,
    ) -> tuple[dict[Required, Any], dict[str, str]]:
        """Build the entity configuration schema and description placeholders.

        Args:
            service: The AC Infinity service instance
            device_id: The device ID to build config for

        Returns:
            Tuple of (entities schema dict, description_placeholders dict)
        """
        device_name = service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME)
        device_code = service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_CODE)

        entities = {}
        description_placeholders = {
            "controller": device_name,
            "device_code": device_code
        }

        entities[
            vol.Required("controller",
                         default=self.__get_saved_entity_conf_value(data, str(device_id), "controller"))] = selector(
            {
                "select": {
                    "options": ENTITY_CONFIG_OPTIONS_CONTROLLER,
                    "mode": "dropdown"
                }
            })

        entities[
            vol.Required("sensors", default=self.__get_saved_entity_conf_value(data, str(device_id), "sensors"))] = selector({
            "select": {
                "options": ENTITY_CONFIG_OPTIONS_SENSORS,
                "mode": "dropdown"
            }
        })

        for i in service.get_device_ports(device_id):
            entity_config_key = f"port_{i}"
            description_placeholders[entity_config_key] = service.get_device_property(device_id, i, DevicePropertyKey.NAME)
            entities[vol.Required(entity_config_key, default=self.__get_saved_entity_conf_value(data, str(device_id), entity_config_key))] = selector(
                {
                    "select": {
                        "options": ENTITY_CONFIG_OPTIONS_DEVICES,
                        "mode": "dropdown"
                    }
                })

        return entities, description_placeholders


class ConfigFlow(ACInfinityFlowBase, config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for AC Infinity."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""
        # Public fields for temporary state during configuration
        self.username: str | None = None
        self.password: str | None = None
        self.service: ACInfinityService | None = None
        self.device_ids: list[str] | None = None
        self.device_index: int = 0
        self.entities: dict[str, Any] = {}
        self.filters: dict[str, Any] = {}

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

                self.username = user_input[CONF_EMAIL]
                self.password = user_input[CONF_PASSWORD]
                self.service = ACInfinityService(client, ACInfinityData())
                await self.service.refresh_controllers()

                self.device_ids = self.service.get_device_ids()
                self.device_index = 0

                if self.device_ids is None or len(self.device_ids) == 0:
                    return self.async_abort(reason="no_devices")

                return await self.async_step_enable_entities()

            except ACInfinityClientCannotConnect:
                await client.close()
                errors["base"] = "cannot_connect"
            except ACInfinityClientInvalidAuth:
                await client.close()
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                await client.close()
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    async def async_step_enable_entities(self, user_input: dict[str, Any] | None = None):
        if self.service is None or self.device_ids is None:
            _LOGGER.error("AC Infinity service is not initialized")
            return self.async_abort(reason="not_initialized")

        device_id: str = str(self.device_ids[self.device_index])
        errors: dict[str, str] = {}

        if user_input is not None:
            self.entities[str(device_id)] = user_input

            if self.device_index < len(self.device_ids) - 1:
                self.device_index += 1
                return await self.async_step_enable_entities()

            else:
                return await self.async_step_entity_filters()

        entities, description_placeholders = self._build_entity_config_schema(
            self.service,
            device_id
        )

        return self.async_show_form(
            step_id="enable_entities",
            data_schema=vol.Schema(entities),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_entity_filters(self, user_input: dict[str, Any] | None = None):
        """Integration wide filters to drop whole kinds of entities, across every device."""
        if user_input is not None:
            self.filters = user_input
            return await self.async_create_config_entry()

        return self.async_show_form(
            step_id="entity_filters", data_schema=await async_filter_schema(self.hass, None)
        )

    async def async_create_config_entry(self):
        if self.service:
            await self.service.close()

        await self.async_set_unique_id(f"{DOMAIN}-{self.username}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"AC Infinity ({self.username})", data={
                CONF_EMAIL: self.username,
                CONF_PASSWORD: self.password,
                ConfigurationKey.POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
                ConfigurationKey.ENTITIES: self.entities,
                ConfigurationKey.EXCLUDED_MODES: self.filters.get(ConfigurationKey.EXCLUDED_MODES, []),
                ConfigurationKey.EXCLUDED_ENTITY_TYPES: self.filters.get(ConfigurationKey.EXCLUDED_ENTITY_TYPES, []),
                ConfigurationKey.MODIFIED_AT: datetime.now().isoformat()
            }
        )


class OptionsFlow(ACInfinityFlowBase, config_entries.OptionsFlow):

    def __init__(self):
        """Initialize the options flow."""
        # Public field for temporary state during configuration
        self.current_device_id: str | int = 0

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        return self.async_show_menu(
            step_id="init", menu_options=["general_config", "controller_select", "entity_filters", "calibrate"]
        )

    async def async_step_general_config(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            polling_interval = user_input.get(
                ConfigurationKey.POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
            )
            password: str | None = user_input.get(ConfigurationKey.UPDATE_PASSWORD, None)
            number_display_type = user_input.get(ConfigurationKey.NUMBER_DISPLAY_TYPE, "auto")

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
                    _ = await client.get_account_controllers()
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
                display_type_changed = (
                    new_data.get(ConfigurationKey.NUMBER_DISPLAY_TYPE, "auto") != number_display_type
                )
                new_data[ConfigurationKey.NUMBER_DISPLAY_TYPE] = number_display_type
                if password:
                    new_data[CONF_PASSWORD] = password

                self.__update_config_entry_data(new_data)

                entry_data: ACInfinityEntryData = self.hass.data[DOMAIN][
                    self.config_entry.entry_id
                ]
                entry_data.list_coordinator.update_interval = timedelta(seconds=polling_interval)
                for device_coordinator in entry_data.device_coordinators.values():
                    device_coordinator.update_interval = timedelta(seconds=polling_interval)

                _LOGGER.info("Polling Interval changed to %s seconds", polling_interval)

                if password:
                    return await self.async_step_notify_restart()
                if display_type_changed:
                    # number entities report their display type when added; reload so they pick up the new one
                    self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="general_config",
            data_schema=vol.Schema(
                {
                    vol.Required(ConfigurationKey.POLLING_INTERVAL,
                                 default=self.__get_saved_conf_value(ConfigurationKey.POLLING_INTERVAL,
                                                                     DEFAULT_POLLING_INTERVAL)): int,
                    vol.Optional(ConfigurationKey.UPDATE_PASSWORD): str,
                    vol.Required(ConfigurationKey.NUMBER_DISPLAY_TYPE,
                                 default=self.__get_saved_conf_value(ConfigurationKey.NUMBER_DISPLAY_TYPE,
                                                                     "auto")): NUMBER_DISPLAY_TYPE_SELECTOR,
                }
            ),
            errors=errors
        )

    async def async_step_controller_select(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self.current_device_id = user_input["device_id"]
            return await self.async_step_enable_entities()

        entry_data: ACInfinityEntryData = self.hass.data[DOMAIN][
            self.config_entry.entry_id
        ]

        device_ids = entry_data.service.get_device_ids()
        if not device_ids:
            return self.async_abort(reason="no_devices")

        options = []
        for device_id in device_ids:
            device_code = entry_data.service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_CODE)
            device_name = entry_data.service.get_controller_property(device_id, ControllerPropertyKey.DEVICE_NAME)

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

    async def async_step_enable_entities(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        device_id: str | int = self.current_device_id

        if user_input is not None:
            new_data = self.config_entry.data.copy()
            if ConfigurationKey.ENTITIES not in new_data:
                new_data[ConfigurationKey.ENTITIES] = {}

            new_data[ConfigurationKey.ENTITIES][str(self.current_device_id)] = user_input
            self.__update_config_entry_data(new_data)

            return await self.async_step_notify_restart()

        service: ACInfinityService = self.hass.data[DOMAIN][
            self.config_entry.entry_id
        ].service

        entities, description_placeholders = self._build_entity_config_schema(
            service,
            device_id,
            dict(self.config_entry.data)
        )

        return self.async_show_form(
            step_id="enable_entities",
            data_schema=vol.Schema(entities),
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_entity_filters(self, user_input: dict[str, Any] | None = None):
        """Integration wide filters to drop whole kinds of entities, across every device.  Saving reloads the
        integration, which removes the excluded entities from Home Assistant."""
        if user_input is not None:
            new_data = self.config_entry.data.copy()
            new_data[ConfigurationKey.EXCLUDED_MODES] = user_input.get(ConfigurationKey.EXCLUDED_MODES, [])
            new_data[ConfigurationKey.EXCLUDED_ENTITY_TYPES] = user_input.get(ConfigurationKey.EXCLUDED_ENTITY_TYPES, [])
            self.__update_config_entry_data(new_data)
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="entity_filters",
            data_schema=await async_filter_schema(self.hass, dict(self.config_entry.data)),
        )

    async def async_step_calibrate(self, user_input: dict[str, Any] | None = None):
        """Calibrate a controller's built-in sensor against another sensor in Home Assistant."""
        entry_data: ACInfinityEntryData = self.hass.data[DOMAIN][self.config_entry.entry_id]
        controllers = {
            c.controller_id: c
            for c in entry_data.service.get_all_controller_properties()
            if not (c.is_ai_controller or c.is_airtap or c.is_room_to_room_fan)
        }
        if not controllers:
            return self.async_abort(reason="no_calibratable_controllers")

        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            temperature_entity = user_input.get("temperature_entity")
            humidity_entity = user_input.get("humidity_entity")
            if not temperature_entity and not humidity_entity:
                errors["base"] = "no_reference"
            else:
                try:
                    result = await async_calibrate(
                        entry_data.service,
                        controllers[user_input["device_id"]],
                        read_reference(self.hass, temperature_entity, temperature=True) if temperature_entity else None,
                        read_reference(self.hass, humidity_entity, temperature=False) if humidity_entity else None,
                    )
                except HomeAssistantError as ex:
                    errors["base"] = "calibration_failed"
                    placeholders["error"] = str(ex)
                else:
                    await entry_data.list_coordinator.async_request_refresh()
                    return self.async_abort(
                        reason="calibrated",
                        description_placeholders={
                            "temperature": "-" if result.temperature_offset is None
                            else f"{result.temperature_offset:+d} {result.temperature_unit}",
                            "humidity": "-" if result.humidity_offset is None else f"{result.humidity_offset:+d} %",
                            "clamped": " (limited to the controller's calibration range)" if result.clamped else "",
                        },
                    )

        return self.async_show_form(
            step_id="calibrate",
            data_schema=vol.Schema({
                vol.Required("device_id"): selector({
                    "select": {
                        "options": [{"value": i, "label": c.controller_name} for i, c in controllers.items()]
                    }
                }),
                vol.Optional("temperature_entity"): selector(
                    {"entity": {"domain": "sensor", "device_class": "temperature"}}
                ),
                vol.Optional("humidity_entity"): selector(
                    {"entity": {"domain": "sensor", "device_class": "humidity"}}
                ),
            }),
            errors=errors,
            description_placeholders=placeholders,
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
            data=new_data
        )

    def __get_saved_conf_value(self, conf_key: str, default):
        return (
            self.config_entry.data[conf_key]
            if conf_key in self.config_entry.data
            and self.config_entry.data[conf_key] is not None
            else default
        )
