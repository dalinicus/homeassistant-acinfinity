"""File required by PyTest to discover tests"""

import asyncio
from asyncio import Future
from typing import Union
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock

from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant, ServiceRegistry
from homeassistant.helpers.entity import Entity
from pytest_mock import MockFixture

from custom_components.ac_infinity.config_flow import OptionsFlow
from custom_components.ac_infinity.const import DOMAIN
from custom_components.ac_infinity.core import (
    ACInfinityControllerEntity,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntity,
    ACInfinityPortEntity,
    ACInfinityService,
)
from tests.data_models import (
    CONTROLLER_PROPERTIES_DATA,
    DEVICE_SETTINGS_DATA,
    EMAIL,
    ENTRY_ID,
    PASSWORD,
    PORT_PROPERTIES_DATA,
    PORT_CONTROLS_DATA,
)

MockType = Union[
    MagicMock,
    AsyncMock,
    NonCallableMagicMock,
]


class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities: list[ACInfinityEntity] = []

    def add_entities_callback(
        self,
        new_entities: list,
        update_before_add: bool = False,
    ):
        self._added_entities = new_entities

    @property
    def added_entities(self):
        return self._added_entities


async def execute_and_get_controller_entity(
    setup_fixture, async_setup_entry, property_key: str
) -> ACInfinityControllerEntity:
    test_objects: ACTestObjects = setup_fixture

    await async_setup_entry(
        test_objects.hass,
        test_objects.config_entry,
        test_objects.entities.add_entities_callback,
    )

    found = [
        sensor
        for sensor in test_objects.entities.added_entities
        if property_key in sensor.unique_id
    ]
    assert len(found) == 1
    entity = found[0]

    assert isinstance(entity, ACInfinityControllerEntity)
    return entity


async def execute_and_get_port_entity(
    setup_fixture,
    async_setup_entry,
    port: int,
    data_key: str,
) -> ACInfinityPortEntity:
    test_objects: ACTestObjects = setup_fixture

    await async_setup_entry(
        test_objects.hass,
        test_objects.config_entry,
        test_objects.entities.add_entities_callback,
    )

    found = [
        entity
        for entity in test_objects.entities.added_entities
        if entity.unique_id.endswith(data_key) and f"port_{port}" in entity.unique_id
    ]
    assert len(found) == 1
    entity = found[0]

    assert isinstance(entity, ACInfinityPortEntity)
    return entity


def setup_entity_mocks(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    mocker.patch.object(HomeAssistant, "__init__", return_value=None)
    write_ha_mock = mocker.patch.object(
        Entity, "async_write_ha_state", return_value=None
    )

    hass = HomeAssistant("/path")
    ac_infinity = ACInfinityService(EMAIL, PASSWORD)

    ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
    ac_infinity._device_settings = DEVICE_SETTINGS_DATA
    ac_infinity._port_properties = PORT_PROPERTIES_DATA
    ac_infinity._port_controls = PORT_CONTROLS_DATA

    coordinator = ACInfinityDataUpdateCoordinator(hass, ac_infinity, 10)


    port_control_set_mock = mocker.patch.object(
        ac_infinity, "update_port_control", return_value=future
    )
    port_control_sets_mock = mocker.patch.object(
        ac_infinity, "update_port_controls", return_value=future
    )
    controller_setting_set_mock = mocker.patch.object(
        ac_infinity, "update_controller_setting", return_value=future
    )
    controller_setting_sets_mock = mocker.patch.object(
        ac_infinity, "update_controller_settings", return_value=future
    )
    port_setting_set_mock = mocker.patch.object(
        ac_infinity, "update_port_setting", return_value=future
    )
    port_setting_sets_mock = mocker.patch.object(
        ac_infinity, "update_port_settings", return_value=future
    )
    refresh_mock = mocker.patch.object(
        coordinator, "async_request_refresh", return_value=future
    )

    hass.data = {DOMAIN: {ENTRY_ID: coordinator}}

    config_entry = ConfigEntry(
        entry_id=ENTRY_ID,
        data={CONF_EMAIL: ENTRY_ID},
        domain=DOMAIN,
        minor_version=0,
        source="",
        title="",
        version=0,
        unique_id=None,
        options=None,
    )

    entities = EntitiesTracker()

    update_entry = mocker.patch.object(ConfigEntries, "async_update_entry")

    async_call = mocker.patch.object(ServiceRegistry, "async_call")

    options_flow = OptionsFlow(config_entry)
    options_flow.config_entry = config_entry
    options_flow.hass = hass
    options_flow.hass.config_entries = MagicMock()
    options_flow.hass.config_entries.async_update_entry = update_entry
    options_flow.hass.services = MagicMock()
    options_flow.hass.services.async_call = async_call

    return ACTestObjects(
        hass,
        config_entry,
        entities,
        ac_infinity,
        controller_setting_set_mock,
        controller_setting_sets_mock,
        port_control_set_mock,
        port_control_sets_mock,
        port_setting_set_mock,
        port_setting_sets_mock,
        write_ha_mock,
        coordinator,
        refresh_mock,
        options_flow,
    )


class ACTestObjects:
    def __init__(
        self,
        hass,
        config_entry,
        entities,
        ac_infinity,
        controller_set_mock,
        controller_sets_mock,
        port_control_set_mock,
        port_control_sets_mock,
        port_setting_set_mock,
        port_setting_sets_mock,
        write_ha_mock,
        coordinator,
        refresh_mock,
        options_flow,
    ) -> None:
        self.hass: HomeAssistant = hass
        self.config_entry: ConfigEntry = config_entry
        self.entities: EntitiesTracker = entities
        self.ac_infinity: ACInfinityService = ac_infinity
        self.controller_set_mock: MockType = controller_set_mock
        self.controller_sets_mock: MockType = controller_sets_mock
        self.port_control_set_mock: MockType = port_control_set_mock
        self.port_control_sets_mock: MockType = port_control_sets_mock
        self.port_setting_set_mock: MockType = port_setting_set_mock
        self.port_setting_sets_mock: MockType = port_setting_sets_mock
        self.write_ha_mock: MockType = write_ha_mock
        self.coordinator: ACInfinityDataUpdateCoordinator = coordinator
        self.refresh_mock: MockType = refresh_mock
        self.options_flow: OptionsFlow = options_flow
