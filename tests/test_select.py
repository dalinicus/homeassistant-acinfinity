import asyncio
from asyncio import Future

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_mock import MockFixture

from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_AT_TYPE,
)
from custom_components.ac_infinity.select import (
    ACInfinityPortSelectEntity,
    async_setup_entry,
)
from tests.data_models import DEVICE_ID, DEVICE_INFO_DATA, DEVICE_SETTINGS, MAC_ADDR

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities: list[ACInfinityPortSelectEntity] = []

    def add_entities_callback(
        self,
        new_entities: list[ACInfinityPortSelectEntity],
        update_before_add: bool = False,
    ):
        self._added_entities = new_entities


@pytest.fixture
def setup(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    ac_infinity = ACInfinity(EMAIL, PASSWORD)

    def set_data():
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._port_settings = DEVICE_SETTINGS

        return future

    mocker.patch.object(ACInfinity, "update", side_effect=set_data)
    mocker.patch.object(ACInfinity, "set_device_port_setting", return_value=future)
    mocker.patch.object(ConfigEntry, "__init__", return_value=None)
    mocker.patch.object(HomeAssistant, "__init__", return_value=None)

    hass = HomeAssistant("/path")
    hass.data = {DOMAIN: {ENTRY_ID: ac_infinity}}

    configEntry = ConfigEntry()
    configEntry.entry_id = ENTRY_ID

    entities = EntitiesTracker()

    return (hass, configEntry, entities, ac_infinity)


@pytest.mark.asyncio
class TestNumbers:
    set_data_mode_value = 0

    async def __execute_and_get_port_sensor(
        self, setup, property_key: str
    ) -> ACInfinityPortSelectEntity:
        entities: EntitiesTracker
        (hass, configEntry, entities, _) = setup

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
        (hass, configEntry, entities, _) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        assert len(entities._added_entities) == 4

    async def test_async_setup_mode_created_for_each_port(self, setup):
        """Sensor for device port mode created on setup"""

        sensor = await self.__execute_and_get_port_sensor(setup, SETTING_KEY_AT_TYPE)

        assert "Mode" in sensor._attr_name
        assert (
            sensor._attr_unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_1_{SETTING_KEY_AT_TYPE}"
        )
        assert len(sensor._attr_options) == 8

    @pytest.mark.parametrize(
        "atType,expected",
        [
            (1, "Off"),
            (2, "On"),
            (3, "Auto"),
            (4, "Timer to On"),
            (5, "Timer to Off"),
            (6, "Cycle"),
            (7, "Schedule"),
            (8, "VPD"),
        ],
    )
    async def test_async_update_mode_value_Correct(
        self, setup, mocker: MockFixture, atType, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        ac_infinity: ACInfinity

        (_, _, _, ac_infinity) = setup
        sensor: ACInfinityPortSelectEntity = await self.__execute_and_get_port_sensor(
            setup, SETTING_KEY_AT_TYPE
        )

        def set_data():
            future: Future = asyncio.Future()
            future.set_result(None)

            ac_infinity._devices = DEVICE_INFO_DATA
            ac_infinity._port_settings = DEVICE_SETTINGS
            ac_infinity._port_settings[str(DEVICE_ID)][1][SETTING_KEY_AT_TYPE] = atType
            return future

        mocker.patch.object(ACInfinity, "update", side_effect=set_data)
        await sensor.async_update()

        assert sensor._attr_current_option == expected

    @pytest.mark.parametrize(
        "expected,atTypeString",
        [
            (1, "Off"),
            (2, "On"),
            (3, "Auto"),
            (4, "Timer to On"),
            (5, "Timer to Off"),
            (6, "Cycle"),
            (7, "Schedule"),
            (8, "VPD"),
        ],
    )
    async def test_async_set_native_value(
        self, mocker: MockFixture, setup, atTypeString, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_set = mocker.patch.object(
            ACInfinity, "set_device_port_setting", return_value=future
        )
        sensor: ACInfinityPortSelectEntity = await self.__execute_and_get_port_sensor(
            setup, SETTING_KEY_AT_TYPE
        )
        await sensor.async_select_option(atTypeString)

        assert sensor._attr_current_option == atTypeString
        mock_set.assert_called_with(str(DEVICE_ID), 1, SETTING_KEY_AT_TYPE, expected)
