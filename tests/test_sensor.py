import asyncio
from asyncio import Future

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from pytest_mock import MockFixture

from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.const import (
    DEVICE_KEY_HUMIDITY,
    DEVICE_KEY_TEMPERATURE,
    DEVICE_KEY_VAPOR_PRESSURE_DEFICIT,
    DEVICE_PORT_KEY_SPEAK,
    DOMAIN,
)
from custom_components.ac_infinity.sensor import (
    ACInfinityPortSensorEntity,
    ACInfinitySensorEntity,
    async_setup_entry,
)
from tests.data_models import DEVICE_INFO_LIST_ALL, MAC_ADDR

EMAIL = "myemail@unittest.com"
PASSWORD = "hunter2"
ENTRY_ID = f"ac_infinity-{EMAIL}"


class EntitiesTracker:
    def __init__(self) -> None:
        self._added_entities: list[ACInfinitySensorEntity] = []

    def add_entities_callback(
        self,
        new_entities: list[ACInfinitySensorEntity],
        update_before_add: bool = False,
    ):
        self._added_entities = new_entities


@pytest.fixture
def setup(mocker: MockFixture):
    future: Future = asyncio.Future()
    future.set_result(None)

    ac_infinity = ACInfinity(EMAIL, PASSWORD)

    def set_data():
        ac_infinity._data = DEVICE_INFO_LIST_ALL
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
class TestSensors:
    async def __execute_and_get_sensor(
        self, setup, property_key: str
    ) -> ACInfinitySensorEntity:
        entities: EntitiesTracker
        (hass, configEntry, entities) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        found = [
            sensor
            for sensor in entities._added_entities
            if property_key in sensor._attr_unique_id
        ]
        assert len(found) == 1

        return found[0]

    async def __execute_and_get_port_sensor(
        self, setup, port: int, property_key: str
    ) -> ACInfinityPortSensorEntity:
        entities: EntitiesTracker
        (hass, configEntry, entities) = setup

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
        (hass, configEntry, entities) = setup

        await async_setup_entry(hass, configEntry, entities.add_entities_callback)

        assert len(entities._added_entities) == 7

    async def test_async_setup_entry_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup"""

        sensor = await self.__execute_and_get_sensor(setup, DEVICE_KEY_TEMPERATURE)

        assert "Temperature" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_{DEVICE_KEY_TEMPERATURE}"
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    async def test_async_update_temperature_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinitySensorEntity = await self.__execute_and_get_sensor(
            setup, DEVICE_KEY_TEMPERATURE
        )
        await sensor.async_update()

        assert sensor._attr_native_value == 24.17

    async def test_async_setup_entry_humidity_created(self, mocker, setup):
        """Sensor for device reported humidity is created on setup"""

        sensor = await self.__execute_and_get_sensor(setup, DEVICE_KEY_HUMIDITY)

        assert "Humidity" in sensor._attr_name
        assert sensor._attr_unique_id == f"{DOMAIN}_{MAC_ADDR}_{DEVICE_KEY_HUMIDITY}"
        assert sensor._attr_device_class == SensorDeviceClass.HUMIDITY
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE

    async def test_async_update_humidity_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinitySensorEntity = await self.__execute_and_get_sensor(
            setup, DEVICE_KEY_HUMIDITY
        )
        await sensor.async_update()

        assert sensor._attr_native_value == 72

    async def test_async_setup_entry_vpd_created(self, mocker, setup):
        """Sensor for device reported humidity is created on setup"""

        sensor = await self.__execute_and_get_sensor(
            setup, DEVICE_KEY_VAPOR_PRESSURE_DEFICIT
        )

        assert "VPD" in sensor._attr_name
        assert (
            sensor._attr_unique_id
            == f"{DOMAIN}_{MAC_ADDR}_{DEVICE_KEY_VAPOR_PRESSURE_DEFICIT}"
        )
        assert sensor._attr_device_class == SensorDeviceClass.PRESSURE
        assert sensor._attr_native_unit_of_measurement == UnitOfPressure.KPA

    async def test_async_update_vpd_value_Correct(self, setup):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinitySensorEntity = await self.__execute_and_get_sensor(
            setup, DEVICE_KEY_VAPOR_PRESSURE_DEFICIT
        )
        await sensor.async_update()

        assert sensor._attr_native_value == 0.83

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_power_created_for_each_port(
        self, setup, port
    ):
        """Sensor for device port speak created on setup"""

        sensor = await self.__execute_and_get_port_sensor(
            setup, port, DEVICE_PORT_KEY_SPEAK
        )

        assert "Power" in sensor._attr_name
        assert (
            sensor._attr_unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{DEVICE_PORT_KEY_SPEAK}"
        )
        assert sensor._attr_device_class == SensorDeviceClass.POWER_FACTOR

    @pytest.mark.parametrize(
        "port,expected",
        [
            (1, 5),
            (2, 7),
            (3, 5),
            (4, 0),
        ],
    )
    async def test_async_update_current_power_value_Correct(
        self, setup, port, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        sensor: ACInfinityPortSensorEntity = await self.__execute_and_get_port_sensor(
            setup, port, DEVICE_PORT_KEY_SPEAK
        )
        await sensor.async_update()

        assert sensor._attr_native_value == expected
