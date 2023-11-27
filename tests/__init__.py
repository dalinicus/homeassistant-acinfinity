"""File required by PyTest to discover tests"""

import asyncio
from asyncio import Future
from typing import Union
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from pytest_mock import MockFixture

from custom_components.ac_infinity import (
    ACInfinityControllerEntity,
    ACInfinityDataUpdateCoordinator,
    ACInfinityEntity,
    ACInfinityPortEntity,
)
from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.const import DOMAIN
from tests.data_models import (
    DEVICE_INFO_DATA,
    DEVICE_SETTINGS,
    EMAIL,
    ENTRY_ID,
    PASSWORD,
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


async def execute_and_get_controller_entity(
    setup_fixture, async_setup_entry, property_key: str
) -> ACInfinityControllerEntity:
    test_objects: ACTestObjects = setup_fixture

    await async_setup_entry(
        test_objects.hass,
        test_objects.configEntry,
        test_objects.entities.add_entities_callback,
    )

    found = [
        sensor
        for sensor in test_objects.entities._added_entities
        if property_key in sensor.unique_id
    ]
    assert len(found) == 1

    return found[0]


async def execute_and_get_port_entity(
    setup_fixture,
    async_setup_entry,
    port: int,
    data_key: str,
) -> ACInfinityPortEntity:
    test_objects: ACTestObjects = setup_fixture

    await async_setup_entry(
        test_objects.hass,
        test_objects.configEntry,
        test_objects.entities.add_entities_callback,
    )

    found = [
        sensor
        for sensor in test_objects.entities._added_entities
        if sensor.unique_id.endswith(data_key) and f"port_{port}" in sensor.unique_id
    ]
    assert len(found) == 1

    return found[0]


def setup_entity_mocks(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    mocker.patch.object(ConfigEntry, "__init__", return_value=None)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)
    write_ha_mock = mocker.patch.object(
        Entity, "async_write_ha_state", return_value=None
    )

    hass = HomeAssistant("/path")
    ac_infinity = ACInfinity(EMAIL, PASSWORD)
    ac_infinity._devices = DEVICE_INFO_DATA
    ac_infinity._port_settings = DEVICE_SETTINGS
    coordinator = ACInfinityDataUpdateCoordinator(hass, ac_infinity, 10)

    set_mock = mocker.patch.object(
        ac_infinity, "set_device_port_setting", return_value=future
    )
    sets_mock = mocker.patch.object(
        ac_infinity, "set_device_port_settings", return_value=future
    )
    refresh_mock = mocker.patch.object(
        coordinator, "async_request_refresh", return_value=future
    )

    hass.data = {DOMAIN: {ENTRY_ID: coordinator}}

    configEntry = ConfigEntry()
    configEntry.entry_id = ENTRY_ID

    entities = EntitiesTracker()

    return ACTestObjects(
        hass,
        configEntry,
        entities,
        ac_infinity,
        set_mock,
        sets_mock,
        write_ha_mock,
        coordinator,
        refresh_mock,
    )


class ACTestObjects:
    def __init__(
        self,
        hass,
        configEntry,
        entities,
        ac_infinity,
        set_mock,
        sets_mock,
        write_ha_mock,
        coordinator,
        refresh_mock,
    ) -> None:
        self.hass: HomeAssistant = hass
        self.configEntry: ConfigEntry = configEntry
        self.entities: EntitiesTracker = entities
        self.ac_infinity: ACInfinity = ac_infinity
        self.set_mock: MockType = set_mock
        self.sets_mock: MockType = sets_mock
        self.write_ha_mock: MockType = write_ha_mock
        self.coordinator: ACInfinityDataUpdateCoordinator = coordinator
        self.refresh_mock: MockType = refresh_mock
