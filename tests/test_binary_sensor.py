import asyncio
from collections.abc import Iterable

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.const import (
    DEVICE_KEY_HUMIDITY,
    DEVICE_KEY_TEMPERATURE,
    DEVICE_KEY_VAPOR_PRESSURE_DEFICIT,
    DOMAIN,
    DEVICE_PORT_KEY_ONLINE
)
from custom_components.ac_infinity.binary_sensor import (
    ACInfinityPortBinarySensorEntity,
    async_setup_entry,
)
from tests.data_models import DEVICE_INFO_LIST_ALL, MAC_ADDR


EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"

class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities = []

    def add_entities_callback(
        self,
        new_entities: Iterable[ACInfinityPortBinarySensorEntity],
        update_before_add: bool = False,
    ):
        self._added_entities = new_entities


@pytest.fixture
def setup(mocker):
    future = asyncio.Future()
    future.set_result(None)

    ac_infinity = ACInfinity(EMAIL, PASSWORD)
    def set_data():
        ac_infinity._data = DEVICE_INFO_LIST_ALL
        return future
    
    mocker.patch.object(ACInfinity, "update", side_effect=set_data)
    mocker.patch.object(ConfigEntry, "__init__", return_value=None)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)

    hass = HomeAssistant()
    hass.data = {DOMAIN: {ENTRY_ID: ac_infinity}}

    configEntry = ConfigEntry()
    configEntry.entry_id = ENTRY_ID

    entities = EntitiesTracker()

    return (hass, configEntry, entities)


@pytest.mark.asyncio
class TestBinarySensors:
    async def __execute_and_get_port_sensor(
        self, setup, property_key: str
    ) -> ACInfinityPortBinarySensorEntity:
        entities: EntitiesTracker
        (hass, configEntry, entities) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        found = [
            sensor
            for sensor in entities._added_entities
            if property_key in sensor._attr_unique_id
            and "port_1" in sensor._attr_unique_id
        ]
        assert len(found) == 1

        return found[0]

    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        entities: EntitiesTracker
        (hass, configEntry, entities) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        assert len(entities._added_entities) == 4

    async def test_async_setup_entry_plug_created_for_each_port(self, setup):
        """Sensor for device port connected is created on setup"""

        sensor = await self.__execute_and_get_port_sensor(setup, DEVICE_PORT_KEY_ONLINE)

        assert "Online" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_port_1_{DEVICE_PORT_KEY_ONLINE}"
        assert sensor._attr_device_class == BinarySensorDeviceClass.PLUG

    async def test_async_update_plug_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinityPortBinarySensorEntity = await self.__execute_and_get_port_sensor(
            setup, DEVICE_PORT_KEY_ONLINE
        )
        await sensor.async_update()

        assert sensor.is_on