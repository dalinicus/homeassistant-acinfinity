import asyncio
from asyncio import Future

import pytest
from homeassistant.components.number import NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_mock import MockFixture

from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.const import (
    DOMAIN,
    SENSOR_PORT_KEY_SPEAK,
)
from custom_components.ac_infinity.number import (
    ACInfinityPortNumberEntity,
    async_setup_entry,
)
from tests.data_models import DEVICE_INFO_LIST_ALL, MAC_ADDR

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities: list[ACInfinityPortNumberEntity] = []

    def add_entities_callback(
        self,
        new_entities: list[ACInfinityPortNumberEntity],
        update_before_add: bool = False,
    ):
        self._added_entities = new_entities


@pytest.fixture
def setup(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    ac_infinity = ACInfinity(EMAIL, PASSWORD)

    def set_data():
        ac_infinity._devices = DEVICE_INFO_LIST_ALL
        return future

    mocker.patch.object(ACInfinity, "update", side_effect=set_data)
    mocker.patch.object(ConfigEntry, "__init__", return_value=None)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)

    hass = HomeAssistant("/path")
    hass.data = {DOMAIN: {ENTRY_ID: ac_infinity}}

    configEntry = ConfigEntry()
    configEntry.entry_id = ENTRY_ID

    entities = EntitiesTracker()

    return (hass, configEntry, entities)


@pytest.mark.asyncio
class TestNumbers:
    async def __execute_and_get_port_sensor(
        self, setup, property_key: str
    ) -> ACInfinityPortNumberEntity:
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

    async def test_async_setup_entry_intensity_created_for_each_port(self, setup):
        """Sensor for device port intensity created on setup"""

        sensor = await self.__execute_and_get_port_sensor(setup, SENSOR_PORT_KEY_SPEAK)

        assert "Intensity" in sensor._attr_name
        assert (
            sensor._attr_unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_1_{SENSOR_PORT_KEY_SPEAK}"
        )
        assert sensor._attr_device_class == NumberDeviceClass.POWER_FACTOR
        assert sensor._attr_native_min_value == 0
        assert sensor._attr_native_max_value == 10

    async def test_async_update_intensity_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinityPortNumberEntity = await self.__execute_and_get_port_sensor(
            setup, SENSOR_PORT_KEY_SPEAK
        )
        await sensor.async_update()

        assert sensor._attr_native_value == 5
