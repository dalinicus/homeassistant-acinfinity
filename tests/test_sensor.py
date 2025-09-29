from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from pytest_mock import MockFixture

from custom_components.ac_infinity.const import (
    DOMAIN,
    ControllerPropertyKey,
    CustomDevicePropertyKey,
    DevicePropertyKey,
    SensorPropertyKey,
    SensorReferenceKey,
    SensorType,
)
from custom_components.ac_infinity.sensor import (
    ACInfinityControllerSensorEntity,
    ACInfinityDeviceSensorEntity,
    ACInfinitySensorSensorEntity,
    async_setup_entry,
)
from tests import (
    ACTestObjects,
    execute_and_get_controller_entity,
    execute_and_get_device_entity,
    execute_and_get_sensor_entity,
    setup_entity_mocks,
)
from tests.data_models import (
    AI_DEVICE_ID,
    AI_MAC_ADDR,
    CO2_LIGHT_ACCESS_PORT,
    CONTROLLER_ACCESS_PORT,
    DEVICE_ID,
    MAC_ADDR,
    PROBE_ACCESS_PORT,
    SENSOR_PROPERTY_CONTROLLER_TEMP_C,
    SENSOR_PROPERTY_CONTROLLER_TEMP_F,
    SENSOR_PROPERTY_PROBE_TEMP_C,
    SENSOR_PROPERTY_PROBE_TEMP_F,
    SOIL_SENSOR_PORT,
)


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestSensors:
    async def test_async_setup_all_sensors_created(self, setup):
        """All sensors created"""

        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        assert len(test_objects.entities._added_entities) == 28

    async def test_async_setup_entry_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup for non-ai controllers"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.TEMPERATURE
        )

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3215, 32.15), (None, 0)])
    async def test_async_update_temperature_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.TEMPERATURE
        )

        test_objects.ac_infinity._controller_properties[str(DEVICE_ID)][
            ControllerPropertyKey.TEMPERATURE
        ] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.HUMIDITY
        )

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert (
            entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.HUMIDITY}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE

        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3215, 32.15), (None, 0)])
    async def test_async_update_humidity_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.HUMIDITY
        )

        test_objects.ac_infinity._controller_properties[str(DEVICE_ID)][
            ControllerPropertyKey.HUMIDITY
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.VPD
        )

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.unique_id == f"{DOMAIN}_{MAC_ADDR}_{ControllerPropertyKey.VPD}"
        assert entity.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert entity.entity_description.suggested_unit_of_measurement is None
        assert (
            entity.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (105, 1.05), (None, 0)])
    async def test_async_update_vpd_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_controller_entity(
            setup, async_setup_entry, ControllerPropertyKey.VPD
        )

        test_objects.ac_infinity._controller_properties[str(DEVICE_ID)][
            ControllerPropertyKey.VPD
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityControllerSensorEntity)
        assert entity.native_value == expected

    @pytest.mark.parametrize(
        "device_id, mac_addr, is_ai_controller, expected_count",
        [
            (DEVICE_ID, MAC_ADDR, False, 3),  # Non-AI controller should have 3 controller entities (temp, humidity, vpd)
            (AI_DEVICE_ID, AI_MAC_ADDR, True, 0),  # AI controller should have 0 controller entities due to is_ai_controller logic
        ],
    )
    async def test_async_setup_entry_controller_descriptions_created_based_on_controller_type(
        self, setup, device_id, mac_addr, is_ai_controller, expected_count
    ):
        """Controller sensor entities from CONTROLLER_DESCRIPTIONS should only be created for non-AI controllers"""

        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        # Look for controller entities (from CONTROLLER_DESCRIPTIONS) for the specified controller
        controller_entities = [
            entity
            for entity in test_objects.entities.added_entities
            if mac_addr in entity.unique_id
            and isinstance(entity, ACInfinityControllerSensorEntity)
            and (ControllerPropertyKey.TEMPERATURE in entity.unique_id
                 or ControllerPropertyKey.HUMIDITY in entity.unique_id
                 or ControllerPropertyKey.VPD in entity.unique_id)
        ]

        controller_type = "AI" if is_ai_controller else "non-AI"
        assert len(controller_entities) == expected_count, (
            f"Expected {expected_count} controller entities for {controller_type} controller "
            f"(device_id: {device_id}), but found {len(controller_entities)}: "
            f"{[e.unique_id for e in controller_entities]}"
        )

    async def test_async_setup_entry_ai_controller_f_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup for AI controllers"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties[
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_F,
            )
        ] = SENSOR_PROPERTY_CONTROLLER_TEMP_F
        test_objects.ac_infinity._sensor_properties.pop(
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_C,
            ),
            None,
        )

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_TEMPERATURE,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{CONTROLLER_ACCESS_PORT}_{SensorReferenceKey.CONTROLLER_TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "value,expected", [(0, -17.78), (6980, 21), (None, -17.78)]
    )
    async def test_async_update_ai_controller_temperature_f_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload.  Fahrenheit should be represented as Celsius"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties[
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_F,
            )
        ] = SENSOR_PROPERTY_CONTROLLER_TEMP_F
        test_objects.ac_infinity._sensor_properties.pop(
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_C,
            ),
            None,
        )

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_TEMPERATURE,
        )

        test_objects.ac_infinity._sensor_properties[
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_F,
            )
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_controller_c_temperature_created(self, setup):
        """Sensor for device reported temperature is created on setup for AI controllers"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties.pop(
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_F,
            ),
            None,
        )
        test_objects.ac_infinity._sensor_properties[
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_C,
            )
        ] = SENSOR_PROPERTY_CONTROLLER_TEMP_C

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_TEMPERATURE,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{CONTROLLER_ACCESS_PORT}_{SensorReferenceKey.CONTROLLER_TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (2155, 21.55), (None, 0)])
    async def test_async_update_ai_controller_temperature_c_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload.  Celsius should continue to be represented as Celsius"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties.pop(
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_F,
            ),
            None,
        )
        test_objects.ac_infinity._sensor_properties[
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_C,
            )
        ] = SENSOR_PROPERTY_CONTROLLER_TEMP_C

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_TEMPERATURE,
        )

        test_objects.ac_infinity._sensor_properties[
            (
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_TEMPERATURE_C,
            )
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_controller_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_HUMIDITY,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{CONTROLLER_ACCESS_PORT}_{SensorReferenceKey.CONTROLLER_HUMIDITY}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE

        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3215, 32.15), (None, 0)])
    async def test_async_update_ai_controller_humidity_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_HUMIDITY,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), CONTROLLER_ACCESS_PORT, SensorType.CONTROLLER_HUMIDITY)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_controller_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_VPD,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{CONTROLLER_ACCESS_PORT}_{SensorReferenceKey.CONTROLLER_VPD}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert entity.entity_description.suggested_unit_of_measurement is None
        assert (
            entity.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (170, 1.7), (None, 0)])
    async def test_async_update_ai_controller_vpd_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CONTROLLER_ACCESS_PORT,
            SensorReferenceKey.CONTROLLER_VPD,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), CONTROLLER_ACCESS_PORT, SensorType.CONTROLLER_VPD)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_probe_temperature_f_created(self, setup):
        """Sensor for device reported temperature is created on setup for AI controllers"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_F)
        ] = SENSOR_PROPERTY_PROBE_TEMP_F
        test_objects.ac_infinity._sensor_properties.pop(
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.CONTROLLER_TEMPERATURE_C),
            None,
        )

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            PROBE_ACCESS_PORT,
            SensorReferenceKey.PROBE_TEMPERATURE,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{PROBE_ACCESS_PORT}_{SensorReferenceKey.PROBE_TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize(
        "value,expected", [(0, -17.78), (6980, 21), (None, -17.78)]
    )
    async def test_async_update_ai_probe_temperature_f_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload.  Fahrenheit should be represented as Celsius"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_F)
        ] = SENSOR_PROPERTY_PROBE_TEMP_F
        test_objects.ac_infinity._sensor_properties.pop(
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.CONTROLLER_TEMPERATURE_C),
            None,
        )

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            PROBE_ACCESS_PORT,
            SensorReferenceKey.PROBE_TEMPERATURE,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_F)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_probe_temperature_c_created(self, setup):
        """Sensor for device reported temperature is created on setup for AI controllers"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties.pop(
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_F), None
        )
        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_C)
        ] = SENSOR_PROPERTY_PROBE_TEMP_C

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            PROBE_ACCESS_PORT,
            SensorReferenceKey.PROBE_TEMPERATURE,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{PROBE_ACCESS_PORT}_{SensorReferenceKey.PROBE_TEMPERATURE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TEMPERATURE
        assert (
            entity.entity_description.native_unit_of_measurement
            == UnitOfTemperature.CELSIUS
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (2155, 21.55), (None, 0)])
    async def test_async_update_ai_probe_temperature_c_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload.  Celsius should continue to be represented as Celsius"""

        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._sensor_properties.pop(
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.CONTROLLER_TEMPERATURE_F),
            None,
        )
        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_C)
        ] = SENSOR_PROPERTY_CONTROLLER_TEMP_C

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            PROBE_ACCESS_PORT,
            SensorReferenceKey.PROBE_TEMPERATURE,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_TEMPERATURE_C)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_probe_humidity_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            PROBE_ACCESS_PORT,
            SensorReferenceKey.PROBE_HUMIDITY,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{PROBE_ACCESS_PORT}_{SensorReferenceKey.PROBE_HUMIDITY}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.HUMIDITY
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE

        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3215, 32.15), (None, 0)])
    async def test_async_update_ai_probe_humidity_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            PROBE_ACCESS_PORT,
            SensorReferenceKey.PROBE_HUMIDITY,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_HUMIDITY)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_probe_vpd_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, PROBE_ACCESS_PORT, SensorReferenceKey.PROBE_VPD
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{PROBE_ACCESS_PORT}_{SensorReferenceKey.PROBE_VPD}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.PRESSURE
        assert entity.entity_description.suggested_unit_of_measurement is None
        assert (
            entity.entity_description.native_unit_of_measurement == UnitOfPressure.KPA
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (170, 1.7), (None, 0)])
    async def test_async_update_ai_probe_vpd_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup, async_setup_entry, PROBE_ACCESS_PORT, SensorReferenceKey.PROBE_VPD
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), PROBE_ACCESS_PORT, SensorType.PROBE_VPD)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_co2_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CO2_LIGHT_ACCESS_PORT,
            SensorReferenceKey.CO2_SENSOR,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{CO2_LIGHT_ACCESS_PORT}_{SensorReferenceKey.CO2_SENSOR}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.CO2
        assert entity.entity_description.suggested_unit_of_measurement is None
        assert (
            entity.entity_description.native_unit_of_measurement
            == CONCENTRATION_PARTS_PER_MILLION
        )
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (544, 544), (None, 0)])
    async def test_async_update_ai_co2_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CO2_LIGHT_ACCESS_PORT,
            SensorReferenceKey.CO2_SENSOR,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), CO2_LIGHT_ACCESS_PORT, SensorType.CO2)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_unknown_sensor_type_ignored(self, setup):
        """Sensor for device reported humidity is created on setup"""

        test_objects: ACTestObjects = setup
        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        found = [
            entity
            for entity in test_objects.entities.added_entities
            if "sensor_22" in entity.unique_id
        ]
        assert len(found) == 0

    async def test_async_setup_entry_ai_light_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CO2_LIGHT_ACCESS_PORT,
            SensorReferenceKey.LIGHT_SENSOR,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{CO2_LIGHT_ACCESS_PORT}_{SensorReferenceKey.LIGHT_SENSOR}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.POWER_FACTOR
        assert entity.entity_description.suggested_unit_of_measurement is None
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (560, 56), (None, 0)])
    async def test_async_update_ai_light_value_correct(self, setup, value, expected):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            CO2_LIGHT_ACCESS_PORT,
            SensorReferenceKey.LIGHT_SENSOR,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), CO2_LIGHT_ACCESS_PORT, SensorType.LIGHT)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    async def test_async_setup_entry_ai_soil_sensor_created(self, setup):
        """Sensor for device reported humidity is created on setup"""

        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            SOIL_SENSOR_PORT,
            SensorReferenceKey.SOIL,
        )

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert (
            entity.unique_id
            == f"{DOMAIN}_{AI_MAC_ADDR}_sensor_{SOIL_SENSOR_PORT}_{SensorReferenceKey.SOIL}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.MOISTURE
        assert entity.entity_description.suggested_unit_of_measurement is None
        assert entity.entity_description.native_unit_of_measurement == PERCENTAGE
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (560, 56), (None, 0)])
    async def test_async_update_ai_soil_sensor_value_correct(
        self, setup, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""

        test_objects: ACTestObjects = setup
        entity = await execute_and_get_sensor_entity(
            setup,
            async_setup_entry,
            SOIL_SENSOR_PORT,
            SensorReferenceKey.SOIL,
        )

        test_objects.ac_infinity._sensor_properties[
            (str(AI_DEVICE_ID), SOIL_SENSOR_PORT, SensorType.SOIL)
        ][SensorPropertyKey.SENSOR_DATA] = value

        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinitySensorSensorEntity)
        assert entity.native_value == expected

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_entry_current_power_created_for_each_port(
        self, setup, port
    ):
        """Sensor for device port speak created on setup"""

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, DevicePropertyKey.SPEAK
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{DevicePropertyKey.SPEAK}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.POWER_FACTOR

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_remaining_time_for_each_port(self, setup, port):
        """Sensor for device port surplus created on setup"""

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, DevicePropertyKey.REMAINING_TIME
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{DevicePropertyKey.REMAINING_TIME}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.DURATION
        assert entity.device_info is not None

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_setup_next_state_change_for_each_port(self, setup, port):
        """Sensor for device port surplus created on setup"""

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, CustomDevicePropertyKey.NEXT_STATE_CHANGE
        )

        assert (
            entity.unique_id
            == f"{DOMAIN}_{MAC_ADDR}_port_{port}_{CustomDevicePropertyKey.NEXT_STATE_CHANGE}"
        )
        assert entity.entity_description.device_class == SensorDeviceClass.TIMESTAMP
        assert entity.device_info is not None

    @pytest.mark.parametrize("value,expected", [(0, 0), (3, 3), (None, 0)])
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_async_update_current_power_value_correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup
        test_objects.ac_infinity._device_properties[(str(DEVICE_ID), port)][
            DevicePropertyKey.SPEAK
        ] = value

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, DevicePropertyKey.SPEAK
        )
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSensorEntity)
        assert entity.native_value == expected

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    @pytest.mark.parametrize("value,expected", [(0, 0), (12345, 12345), (None, 0)])
    async def test_async_update_duration_left_value_correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, DevicePropertyKey.REMAINING_TIME
        )

        test_objects.ac_infinity._device_properties[(str(DEVICE_ID), port)][
            DevicePropertyKey.REMAINING_TIME
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSensorEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    @pytest.mark.parametrize(
        "value,expected",
        [
            (500, datetime(2023, 1, 1, 0, 8, 20, tzinfo=ZoneInfo("America/Chicago"))),
            (
                12345,
                datetime(2023, 1, 1, 3, 25, 45, tzinfo=ZoneInfo("America/Chicago")),
            ),
            (None, None),
            (0, None),
        ],
    )
    @freeze_time(
        "2023-01-01 12:00:00", tz_offset=-6
    )  # Freezing time to a consistent value
    async def test_async_next_state_change_value_correct(
        self, setup, port, value, expected
    ):
        """Reported sensor value matches the value in the json payload"""
        test_objects: ACTestObjects = setup

        entity = await execute_and_get_device_entity(
            setup, async_setup_entry, port, CustomDevicePropertyKey.NEXT_STATE_CHANGE
        )

        test_objects.ac_infinity._controller_properties[(str(DEVICE_ID))][
            ControllerPropertyKey.TIME_ZONE
        ] = "America/Chicago"

        test_objects.ac_infinity._device_properties[(str(DEVICE_ID), port)][
            DevicePropertyKey.REMAINING_TIME
        ] = value
        entity._handle_coordinator_update()

        assert isinstance(entity, ACInfinityDeviceSensorEntity)
        assert entity.native_value == expected
        test_objects.write_ha_mock.assert_called()

    async def test_entity_ref_is_descriptive_for_debugging(self, setup):
        """entities should show unique id in the debug window"""
        test_objects: ACTestObjects = setup

        await async_setup_entry(
            test_objects.hass,
            test_objects.config_entry,
            test_objects.entities.add_entities_callback,
        )

        for entity in test_objects.entities.added_entities:
            assert "unique_id" in entity.__repr__()
