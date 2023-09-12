import asyncio
import datetime
from asyncio import Future

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_mock import MockFixture

from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_SCHEDULED_END_TIME,
    SETTING_KEY_SCHEDULED_START_TIME,
)
from custom_components.ac_infinity.time import (
    ACInfinityPortTimeEntity,
    async_setup_entry,
)
from tests.data_models import DEVICE_ID, DEVICE_INFO_DATA, DEVICE_SETTINGS, MAC_ADDR

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities: list[ACInfinityPortTimeEntity] = []

    def add_entities_callback(
        self,
        new_entities: list[ACInfinityPortTimeEntity],
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
        self, setup, property_key: str, port: int
    ) -> ACInfinityPortTimeEntity:
        entities: EntitiesTracker
        (hass, configEntry, entities, _) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        found = [
            sensor
            for sensor in entities._added_entities
            if property_key in sensor._attr_unique_id
            and f"port_{port}" in sensor._attr_unique_id
        ]
        assert len(found) == 1

        return found[0]

    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""
        entities: EntitiesTracker
        (hass, configEntry, entities, _) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        assert len(entities._added_entities) == 8

    @pytest.mark.parametrize(
        "key", [SETTING_KEY_SCHEDULED_START_TIME, SETTING_KEY_SCHEDULED_END_TIME]
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_schedule_end_time_created_for_each_port(
        self, setup, key, port
    ):
        """Setting for scheduled end time created on setup"""

        sensor: ACInfinityPortTimeEntity = await self.__execute_and_get_port_sensor(
            setup, key, port
        )

        assert "Scheduled" in sensor._attr_name
        assert "Time" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{key}"

    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_SCHEDULED_START_TIME, SETTING_KEY_SCHEDULED_END_TIME]
    )
    @pytest.mark.parametrize(
        "value,expected_hour,expected_minute",
        [(750, 12, 30), (0, 0, 0)],  # make sure midnight is not represented as None
    )
    async def test_async_update_value_Correct(
        self, setup, mocker: MockFixture, setting, value, expected_hour, expected_minute
    ):
        """Reported sensor value matches the value in the json payload"""
        ac_infinity: ACInfinity

        (_, _, _, ac_infinity) = setup
        sensor: ACInfinityPortTimeEntity = await self.__execute_and_get_port_sensor(
            setup, setting, 1
        )

        def set_data():
            future: Future = asyncio.Future()
            future.set_result(None)

            ac_infinity._devices = DEVICE_INFO_DATA
            ac_infinity._port_settings = DEVICE_SETTINGS
            ac_infinity._port_settings[str(DEVICE_ID)][1][setting] = value
            return future

        mocker.patch.object(ACInfinity, "update", side_effect=set_data)
        await sensor.async_update()

        assert sensor._attr_native_value
        assert sensor._attr_native_value.hour == expected_hour
        assert sensor._attr_native_value.minute == expected_minute

    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_SCHEDULED_START_TIME, SETTING_KEY_SCHEDULED_END_TIME]
    )
    @pytest.mark.parametrize("value", [None, 1441, 65535])
    async def test_async_update_value_represents_disabled_Correct(
        self, setup, mocker: MockFixture, setting, value
    ):
        """Reported sensor value is None (disabled) if the number of minutes is None or greater than 24 hours"""
        ac_infinity: ACInfinity

        (_, _, _, ac_infinity) = setup
        sensor: ACInfinityPortTimeEntity = await self.__execute_and_get_port_sensor(
            setup, setting, 1
        )

        def set_data():
            future: Future = asyncio.Future()
            future.set_result(None)

            ac_infinity._devices = DEVICE_INFO_DATA
            ac_infinity._port_settings = DEVICE_SETTINGS
            ac_infinity._port_settings[str(DEVICE_ID)][1][setting] = value
            return future

        mocker.patch.object(ACInfinity, "update", side_effect=set_data)
        await sensor.async_update()

        assert sensor._attr_native_value is None

    @pytest.mark.parametrize(
        "value, expected", [(None, None), (datetime.time(12, 30), 750)]
    )
    @pytest.mark.parametrize(
        "setting", [SETTING_KEY_SCHEDULED_START_TIME, SETTING_KEY_SCHEDULED_END_TIME]
    )
    async def test_async_set_native_value(
        self, mocker: MockFixture, setup, setting, value: datetime.time, expected: int
    ):
        """Reported sensor value matches the value in the json payload"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_set = mocker.patch.object(
            ACInfinity, "set_device_port_setting", return_value=future
        )
        sensor: ACInfinityPortTimeEntity = await self.__execute_and_get_port_sensor(
            setup, setting, 1
        )
        await sensor.async_set_value(value)
        assert sensor._attr_native_value == value

        mock_set.assert_called_with(str(DEVICE_ID), 1, setting, expected)
