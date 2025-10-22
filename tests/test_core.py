import asyncio
from asyncio import Future

import aiohttp
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from pytest_mock import MockFixture

from custom_components.ac_infinity.client import (
    ACInfinityClient,
    ACInfinityClientCannotConnect,
    ACInfinityClientInvalidAuth,
    ACInfinityClientRequestFailed,
)
from custom_components.ac_infinity.const import (
    ControllerType,
    DOMAIN,
    MANUFACTURER,
    AdvancedSettingsKey,
    ControllerPropertyKey,
    DeviceControlKey,
    DevicePropertyKey,
    SensorPropertyKey,
    SensorType,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityEntities,
    ACInfinityService,
)
from custom_components.ac_infinity.sensor import (
    ACInfinityControllerSensorEntity,
    ACInfinityControllerSensorEntityDescription,
)

from . import ACTestObjects, setup_entity_mocks
from .data_models import (
    AI_CONTROLLER_PROPERTIES,
    AI_DEVICE_ID,
    CONTROLLER_ACCESS_PORT,
    CONTROLLER_PROPERTIES,
    CONTROLLER_PROPERTIES_DATA, DEVICE_CONTROLS,
    DEVICE_ID,
    DEVICE_INFO_LIST_ALL,
    DEVICE_NAME,
    DEVICE_SETTINGS_DATA,
    GET_DEV_MODE_SETTING_LIST_PAYLOAD,
    MAC_ADDR,
    DEVICE_CONTROLS_DATA,
    DEVICE_PROPERTIES_DATA,
    SENSOR_PROPERTIES_DATA,
)


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.fixture
def mock_client(mocker: MockFixture):
    """Create a mock ACInfinityClient for testing"""
    return mocker.create_autospec(ACInfinityClient, spec_set=True)

@pytest.mark.asyncio
class TestACInfinity:
    async def test_close_client_closed(self, mock_client):
        """when a client has not been logged in, is_logged_in should return false"""

        ac_infinity = ACInfinityService(mock_client)
        await ac_infinity.close()

        assert mock_client.close.called

    async def test_update_logged_in_should_be_called_if_not_logged_in(
        self, mock_client
    ):
        """if client is already logged in, then log in should not be called"""

        mock_client.is_logged_in.return_value = False
        mock_client.get_account_controllers.return_value = DEVICE_INFO_LIST_ALL
        mock_client.get_device_mode_settings.return_value = DEVICE_CONTROLS

        ac_infinity = ACInfinityService(mock_client)
        await ac_infinity.refresh()

        assert mock_client.login.called

    async def test_update_logged_in_should_not_be_called_if_not_necessary(
        self, mock_client
    ):
        """if client is not already logged in, then log in should be called"""

        mock_client.is_logged_in.return_value = True
        mock_client.get_account_controllers.return_value = DEVICE_INFO_LIST_ALL
        mock_client.get_device_mode_settings.return_value = DEVICE_CONTROLS

        ac_infinity = ACInfinityService(mock_client)
        await ac_infinity.refresh()
        assert not mock_client.login.called

    async def test_update_data_set(self, mock_client):
        """data should be set once update is called"""

        mock_client.is_logged_in.return_value = True
        mock_client.get_account_controllers.return_value = DEVICE_INFO_LIST_ALL
        mock_client.get_device_mode_settings.return_value = DEVICE_CONTROLS

        ac_infinity = ACInfinityService(mock_client)
        await ac_infinity.refresh()

        assert len(ac_infinity._controller_properties) == 2
        assert (
            ac_infinity._controller_properties[str(DEVICE_ID)][
                ControllerPropertyKey.DEVICE_NAME
            ]
            == "Grow Tent"
        )
        assert (
            ac_infinity._controller_properties[str(AI_DEVICE_ID)][
                ControllerPropertyKey.DEVICE_NAME
            ]
            == "Grow Tent AI"
        )

    async def test_update_retried_on_failure(self, mocker: MockFixture, mock_client):
        """update should be tried 5 times before raising an exception"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.get_account_controllers.side_effect = ACInfinityClientCannotConnect("unit-test")
        mock_client.get_device_mode_settings.return_value = DEVICE_CONTROLS


        ac_infinity = ACInfinityService(mock_client)

        with pytest.raises(ACInfinityClientCannotConnect):
            await ac_infinity.refresh()

        assert mock_client.get_account_controllers.call_count == 5

    @pytest.mark.parametrize(
        "exception_type",
        [
            ACInfinityClientCannotConnect("unit-test"),
            ACInfinityClientRequestFailed("unit-test"),
            aiohttp.ClientError("unit-test"),
            asyncio.TimeoutError(),
        ],
    )
    async def test_refresh_retries_on_retryable_exceptions(
        self, mocker: MockFixture, mock_client, exception_type
    ):
        """refresh should retry on retryable exceptions"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.get_account_controllers.side_effect = exception_type

        ac_infinity = ACInfinityService(mock_client)

        with pytest.raises(type(exception_type)):
            await ac_infinity.refresh()

        # Should retry 5 times total (initial + 4 retries)
        assert mock_client.get_account_controllers.call_count == 5

    async def test_refresh_raises_immediately_on_invalid_auth(
        self, mocker: MockFixture, mock_client
    ):
        """refresh should raise immediately on authentication failure without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.get_account_controllers.side_effect = ACInfinityClientInvalidAuth("unit-test")

        ac_infinity = ACInfinityService(mock_client)

        with pytest.raises(ACInfinityClientInvalidAuth):
            await ac_infinity.refresh()

        # Should NOT retry on auth failure
        assert mock_client.get_account_controllers.call_count == 1

    async def test_refresh_raises_immediately_on_unexpected_exception(
        self, mocker: MockFixture, mock_client
    ):
        """refresh should raise immediately on unexpected exceptions without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.get_account_controllers.side_effect = ValueError("unexpected error")

        ac_infinity = ACInfinityService(mock_client)

        with pytest.raises(ValueError):
            await ac_infinity.refresh()

        # Should NOT retry on unexpected exceptions
        assert mock_client.get_account_controllers.call_count == 1

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (ControllerPropertyKey.DEVICE_NAME, True),
            (ControllerPropertyKey.MAC_ADDR, True),
            (ControllerPropertyKey.TEMPERATURE, True),
            (ControllerPropertyKey.HUMIDITY, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID), "12345"])
    async def test_get_controller_property_exists_returns_correct_value(
        self, mock_client, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_controller_property_exists(device_id, property_key)
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (ControllerPropertyKey.DEVICE_NAME, "Grow Tent"),
            (ControllerPropertyKey.MAC_ADDR, MAC_ADDR),
            (ControllerPropertyKey.TEMPERATURE, 2417),
            (ControllerPropertyKey.HUMIDITY, 7200),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_controller_property_gets_correct_property(
        self, mock_client, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_controller_property(device_id, property_key)
        assert result == value

    @pytest.mark.parametrize(
        "property_key, device_id",
        [
            (ControllerPropertyKey.DEVICE_NAME, "232161"),
            ("MyFakeField", DEVICE_ID),
            ("MyFakeField", str(DEVICE_ID)),
        ],
    )
    async def test_get_controller_property_returns_null_properly(
        self, mock_client, property_key, device_id
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_controller_property(device_id, property_key)
        assert result is None

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (SensorPropertyKey.SENSOR_DATA, True),
            (SensorPropertyKey.SENSOR_PRECISION, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [AI_DEVICE_ID, str(AI_DEVICE_ID), "12345"])
    async def test_get_sensor_property_exists_returns_correct_value(
        self, mock_client, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._sensor_properties = SENSOR_PROPERTIES_DATA

        result = ac_infinity.get_sensor_property_exists(
            device_id,
            CONTROLLER_ACCESS_PORT,
            SensorType.CONTROLLER_HUMIDITY,
            property_key,
        )
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (SensorPropertyKey.SENSOR_DATA, 3080),
            (SensorPropertyKey.SENSOR_PRECISION, 3),
        ],
    )
    @pytest.mark.parametrize("device_id", [AI_DEVICE_ID, str(AI_DEVICE_ID)])
    async def test_get_sensor_property_gets_correct_property(
        self, mock_client, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._sensor_properties = SENSOR_PROPERTIES_DATA

        result = ac_infinity.get_sensor_property(
            device_id,
            CONTROLLER_ACCESS_PORT,
            SensorType.CONTROLLER_HUMIDITY,
            property_key,
        )
        assert result == value

    @pytest.mark.parametrize(
        "property_key, device_id, access_port, sensor_type",
        [
            (
                SensorPropertyKey.SENSOR_DATA,
                "232161",
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_HUMIDITY,
            ),
            (
                "MyFakeField",
                AI_DEVICE_ID,
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_HUMIDITY,
            ),
            (
                "MyFakeField",
                str(AI_DEVICE_ID),
                CONTROLLER_ACCESS_PORT,
                SensorType.CONTROLLER_HUMIDITY,
            ),
            (
                SensorPropertyKey.SENSOR_DATA,
                AI_DEVICE_ID,
                999,
                SensorType.CONTROLLER_HUMIDITY,
            ),
            (
                SensorPropertyKey.SENSOR_DATA,
                AI_DEVICE_ID,
                CONTROLLER_ACCESS_PORT,
                "fakeType",
            ),
        ],
    )
    async def test_get_sensor_property_returns_null_properly(
        self, mock_client, property_key, device_id, access_port, sensor_type: int
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_sensor_property(
            device_id, access_port, sensor_type, property_key
        )
        assert result is None

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (DevicePropertyKey.SPEAK, True),
            (DevicePropertyKey.NAME, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID), "12345"])
    async def test_get_port_property_exists_returns_correct_value(
        self, mock_client, device_id, property_key: str, value
    ):
        """getting a port property gets the correct property from the correct port"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_properties = DEVICE_PROPERTIES_DATA

        result = ac_infinity.get_device_property_exists(device_id, 1, property_key)
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "property_key, port_num, value",
        [
            (DevicePropertyKey.SPEAK, 1, 5),
            (DevicePropertyKey.SPEAK, 2, 7),
            (DevicePropertyKey.NAME, 3, "Circulating Fan"),
            (DevicePropertyKey.NAME, 1, "Grow Lights"),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_port_property_gets_correct_property(
        self, mock_client, device_id, port_num, property_key: str, value
    ):
        """getting a port property gets the correct property from the correct port"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_properties = DEVICE_PROPERTIES_DATA

        result = ac_infinity.get_device_property(device_id, port_num, property_key)
        assert result == value

    @pytest.mark.parametrize(
        "property_key, device_id, port_num",
        [
            (DevicePropertyKey.SPEAK, "232161", 1),
            ("MyFakeField", DEVICE_ID, 1),
            (DevicePropertyKey.SPEAK, DEVICE_ID, 9),
            ("MyFakeField", str(DEVICE_ID), 1),
            (DevicePropertyKey.SPEAK, str(DEVICE_ID), 9),
        ],
    )
    async def test_get_port_property_returns_null_properly(
        self, mock_client, property_key, device_id, port_num
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_properties = DEVICE_PROPERTIES_DATA

        result = ac_infinity.get_device_property(device_id, port_num, property_key)
        assert result is None

    async def test_get_device_all_device_meta_data_returns_meta_data(self, mock_client):
        """getting port device ids should return ids"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_all_controller_properties()
        assert len(result) > 0

        device = result[0]
        assert device.controller_id == str(DEVICE_ID)
        assert device.controller_name == DEVICE_NAME
        assert device.mac_addr == MAC_ADDR
        assert [port.device_port for port in device.devices] == [1, 2, 3, 4]

    async def test_controller_devices_property_returns_all_ports(self, mock_client):
        """controller.devices property should return all USB-C ports"""
        controller = ACInfinityController(CONTROLLER_PROPERTIES)

        assert len(controller.devices) == 4
        assert [device.device_port for device in controller.devices] == [1, 2, 3, 4]

        # Verify each device has the correct controller reference
        for device in controller.devices:
            assert device.controller == controller
            assert device.controller.controller_id == str(DEVICE_ID)

    async def test_controller_sensors_property_returns_empty_for_non_ai(self, mock_client):
        """controller.sensors property should return empty list for non-AI controllers"""
        controller = ACInfinityController(CONTROLLER_PROPERTIES)

        assert len(controller.sensors) == 0
        assert controller.sensors == []

    async def test_controller_sensors_property_returns_all_sensors_for_ai(self, mock_client):
        """controller.sensors property should return all sensors for AI controllers"""
        controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)

        # AI controller has 13 sensors in test data (including unknown sensor type)
        assert len(controller.sensors) == 13

        # Verify sensor types are correctly parsed
        sensor_types = [sensor.sensor_type for sensor in controller.sensors]
        assert SensorType.CONTROLLER_TEMPERATURE_F in sensor_types
        assert SensorType.CONTROLLER_TEMPERATURE_C in sensor_types
        assert SensorType.CONTROLLER_HUMIDITY in sensor_types
        assert SensorType.CONTROLLER_VPD in sensor_types
        assert SensorType.PROBE_TEMPERATURE_F in sensor_types
        assert SensorType.PROBE_TEMPERATURE_C in sensor_types
        assert SensorType.PROBE_HUMIDITY in sensor_types
        assert SensorType.PROBE_VPD in sensor_types
        assert SensorType.CO2 in sensor_types
        assert SensorType.LIGHT in sensor_types
        assert SensorType.SOIL in sensor_types
        assert SensorType.WATER in sensor_types
        assert 999 in sensor_types  # Unknown sensor type

        # Verify each sensor has the correct controller reference
        for sensor in controller.sensors:
            assert sensor.controller == controller
            assert sensor.controller.controller_id == str(AI_DEVICE_ID)

    @pytest.mark.parametrize("data", [{}, None])
    async def test_get_device_all_device_meta_data_returns_empty_list(self, mock_client, data):
        """getting device metadata returns empty list if no device exists or data isn't initialized"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = data

        result = ac_infinity.get_all_controller_properties()
        assert result == []

    @pytest.mark.parametrize(
        "dev_type,expected_model",
        [
            (11, "UIS Controller 69 Pro (CTR69P)"),
            (18, "UIS Controller 69 Pro+ (CTR69Q)"),
            (20, "UIS Controller AI+ (CTR89Q)"),
            (21, "UIS Controller Outlet AI (AC-ADA4)"),
            (22, "UIS Controller Outlet AI+ (AC-ADA8)"),
            (3, "UIS Controller Type 3"),
        ],
    )
    async def test_ac_infinity_device_has_correct_device_info(
        self, mock_client, dev_type: int, expected_model: str
    ):
        """getting device returns a model object that contains correct device info for the device registry"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._controller_properties[str(DEVICE_ID)]["devType"] = dev_type

        result = ac_infinity.get_all_controller_properties()
        assert len(result) > 0

        device = result[0]
        device_info = device._device_info
        assert (DOMAIN, str(DEVICE_ID)) in (device_info.get("identifiers") or {})
        assert device_info.get("hw_version") == "1.1"
        assert device_info.get("sw_version") == "3.2.25"
        assert device_info.get("name") == DEVICE_NAME
        assert device_info.get("manufacturer") == MANUFACTURER
        assert device_info.get("model") == expected_model

    @pytest.mark.parametrize(
        "setting_key, value",
        [
            (DeviceControlKey.ON_SPEED, True),
            (DeviceControlKey.AT_TYPE, True),
            (AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, True),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_VPD, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID), "12345"])
    async def test_get_port_control_exists_returns_correct_value(
        self, mock_client, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        result = ac_infinity.get_device_control_exists(device_id, 1, setting_key)
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "setting_key, value",
        [
            (DeviceControlKey.ON_SPEED, 5),
            (
                DeviceControlKey.OFF_SPEED,
                0,
            ),  # make sure 0 still returns 0 and not None or default
            (DeviceControlKey.AT_TYPE, 2),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_VPD, 6),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_port_control_gets_correct_setting(
        self, mock_client, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        result = ac_infinity.get_device_control(device_id, 1, setting_key)
        assert result == value

    @pytest.mark.parametrize("default_value", [0, None, 5455])
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_port_control_gets_returns_default_if_value_is_null(
        self, mock_client, device_id, default_value
    ):
        """getting a port setting returns 0 instead of null if the key exists but the value is null"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ac_infinity._device_controls[(str(DEVICE_ID), 1)][DeviceControlKey.SURPLUS] = None

        result = ac_infinity.get_device_control(
            device_id, 1, DeviceControlKey.SURPLUS, default_value=default_value
        )
        assert result == default_value

    @pytest.mark.parametrize(
        "setting_key, value",
        [
            (AdvancedSettingsKey.CALIBRATE_HUMIDITY, True),
            (AdvancedSettingsKey.TEMP_UNIT, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID), "12345"])
    async def test_get_controller_setting_exists_returns_correct_value(
        self, mock_client, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        result = ac_infinity.get_controller_setting_exists(device_id, setting_key)
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "setting_key, value",
        [
            (AdvancedSettingsKey.CALIBRATE_HUMIDITY, 5),
            (AdvancedSettingsKey.TEMP_UNIT, 1),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_controller_setting_gets_correct_property(
        self, mock_client, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        result = ac_infinity.get_controller_setting(device_id, setting_key)
        assert result == value

    @pytest.mark.parametrize("default_value", [0, None, 5455])
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_controller_setting_gets_returns_default_if_value_is_null(
        self, mock_client, device_id, default_value
    ):
        """getting a port setting returns 0 instead of null if the key exists but the value is null"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        ac_infinity._device_settings[(str(DEVICE_ID), 1)][
            AdvancedSettingsKey.CALIBRATE_HUMIDITY
        ] = None

        result = ac_infinity.get_controller_setting(
            device_id,
            AdvancedSettingsKey.CALIBRATE_HUMIDITY,
            default_value=default_value,
        )
        assert result == default_value

    @pytest.mark.parametrize(
        "setting_key, device_id, port_num",
        [
            (AdvancedSettingsKey.CALIBRATE_HUMIDITY, "232161", 1),
            ("MyFakeField", DEVICE_ID, 1),
            (AdvancedSettingsKey.CALIBRATE_HUMIDITY, DEVICE_ID, 9),
            ("MyFakeField", str(DEVICE_ID), 1),
            (AdvancedSettingsKey.CALIBRATE_HUMIDITY, str(DEVICE_ID), 9),
        ],
    )
    async def test_get_device_setting_returns_null_properly(
        self, mock_client, setting_key, device_id, port_num
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        result = ac_infinity.get_device_setting(device_id, port_num, setting_key)
        assert result is None

    @pytest.mark.parametrize(
        "setting_key, device_id",
        [
            (DeviceControlKey.ON_SPEED, "232161"),
            ("MyFakeField", DEVICE_ID),
            (DevicePropertyKey.NAME, DEVICE_ID),
            ("MyFakeField", str(DEVICE_ID)),
            (DevicePropertyKey.NAME, str(DEVICE_ID)),
        ],
    )
    async def test_get_port_control_returns_null_properly(
        self,
        mock_client,
        setting_key,
        device_id,
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        result = ac_infinity.get_device_control(device_id, 1, setting_key)
        assert result is None

    async def test_update_port_control(self, mock_client):
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_device_controls.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_control(controller.devices[0], DeviceControlKey.AT_TYPE, 2)

        mock_client.update_device_controls.assert_called_with(str(DEVICE_ID), 1, {DeviceControlKey.AT_TYPE: 2})

    async def test_update_port_controls(self, mock_client):
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_device_controls.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_controls(controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        mock_client.update_device_controls.assert_called_with(str(DEVICE_ID), 1, {DeviceControlKey.AT_TYPE: 2})

    async def test_update_port_controls_retried_on_failure(self, mocker: MockFixture, mock_client):
        """updating settings should be tried 5 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_controls.side_effect = ACInfinityClientCannotConnect("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientCannotConnect):
            await ac_infinity.update_device_controls(controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        assert mock_client.update_device_controls.call_count == 5

    @pytest.mark.parametrize(
        "exception_type",
        [
            ACInfinityClientCannotConnect("unit-test"),
            ACInfinityClientRequestFailed("unit-test"),
            aiohttp.ClientError("unit-test"),
            asyncio.TimeoutError(),
        ],
    )
    async def test_update_device_controls_retries_on_retryable_exceptions(
        self, mocker: MockFixture, mock_client, exception_type
    ):
        """update_device_controls should retry on retryable exceptions"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_controls.side_effect = exception_type

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(type(exception_type)):
            await ac_infinity.update_device_controls(controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        # Should retry 5 times total (initial + 4 retries)
        assert mock_client.update_device_controls.call_count == 5

    async def test_update_device_controls_raises_immediately_on_invalid_auth(
        self, mocker: MockFixture, mock_client
    ):
        """update_device_controls should raise immediately on authentication failure without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_controls.side_effect = ACInfinityClientInvalidAuth("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientInvalidAuth):
            await ac_infinity.update_device_controls(controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        # Should NOT retry on auth failure
        assert mock_client.update_device_controls.call_count == 1

    async def test_update_device_controls_raises_immediately_on_unexpected_exception(
        self, mocker: MockFixture, mock_client
    ):
        """update_device_controls should raise immediately on unexpected exceptions without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_controls.side_effect = ValueError("unexpected error")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ValueError):
            await ac_infinity.update_device_controls(controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        # Should NOT retry on unexpected exceptions
        assert mock_client.update_device_controls.call_count == 1

    async def test_update_controller_setting(self, mock_client):
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        await ac_infinity.update_controller_setting(
            controller, AdvancedSettingsKey.CALIBRATE_HUMIDITY, 2
        )

        mock_client.update_device_settings.assert_called_with(
            str(DEVICE_ID), 0, DEVICE_NAME, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
        )

    async def test_update_controller_settings(self, mock_client):
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        await ac_infinity.update_controller_settings(
            controller, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
        )

        mock_client.update_device_settings.assert_called_with(
            str(DEVICE_ID), 0, DEVICE_NAME, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
        )

    async def test_update_controller_settings_raises_for_ai_controller(self, mock_client):
        """updating controller settings should raise NotImplementedError for AI controllers"""
        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)

        with pytest.raises(NotImplementedError):
            await ac_infinity.update_controller_settings(
                ai_controller, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
            )

    async def test_update_controller_settings_retried_on_failure(
        self, mocker: MockFixture, mock_client,
    ):
        """updating settings should be tried 5 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = ACInfinityClientCannotConnect("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientCannotConnect):
            await ac_infinity.update_controller_settings(
                controller, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
            )

        assert mock_client.update_device_settings.call_count == 5

    @pytest.mark.parametrize(
        "exception_type",
        [
            ACInfinityClientCannotConnect("unit-test"),
            ACInfinityClientRequestFailed("unit-test"),
            aiohttp.ClientError("unit-test"),
            asyncio.TimeoutError(),
        ],
    )
    async def test_update_controller_settings_retries_on_retryable_exceptions(
        self, mocker: MockFixture, mock_client, exception_type
    ):
        """update_controller_settings should retry on retryable exceptions"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = exception_type

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(type(exception_type)):
            await ac_infinity.update_controller_settings(
                controller, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
            )

        # Should retry 5 times total (initial + 4 retries)
        assert mock_client.update_device_settings.call_count == 5

    async def test_update_controller_settings_raises_immediately_on_invalid_auth(
        self, mocker: MockFixture, mock_client
    ):
        """update_controller_settings should raise immediately on authentication failure without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = ACInfinityClientInvalidAuth("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientInvalidAuth):
            await ac_infinity.update_controller_settings(
                controller, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
            )

        # Should NOT retry on auth failure
        assert mock_client.update_device_settings.call_count == 1

    async def test_update_controller_settings_raises_immediately_on_unexpected_exception(
        self, mocker: MockFixture, mock_client
    ):
        """update_controller_settings should raise immediately on unexpected exceptions without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = ValueError("unexpected error")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ValueError):
            await ac_infinity.update_controller_settings(
                controller, {AdvancedSettingsKey.CALIBRATE_HUMIDITY: 2}
            )

        # Should NOT retry on unexpected exceptions
        assert mock_client.update_device_settings.call_count == 1

    async def test_update_port_setting(self, mock_client):
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_properties = DEVICE_PROPERTIES_DATA
        ac_infinity._device_properties[(str(DEVICE_ID), 1)][
            DevicePropertyKey.NAME
        ] = DEVICE_NAME

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_setting(
            controller.devices[0], AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 2
        )

        mock_client.update_device_settings.assert_called_with(
            str(DEVICE_ID),
            1,
            DEVICE_NAME,
            {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2},
        )

    async def test_update_port_settings(self, mock_client):
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_properties = DEVICE_PROPERTIES_DATA
        ac_infinity._device_properties[(str(DEVICE_ID), 1)][
            DevicePropertyKey.NAME
        ] = DEVICE_NAME

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_settings(
            controller.devices[0], {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
        )

        mock_client.update_device_settings.assert_called_with(
            str(DEVICE_ID),
            1,
            DEVICE_NAME,
            {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2},
        )

    async def test_update_port_settings_retried_on_failure(self, mocker: MockFixture, mock_client):
        """updating settings should be tried 5 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = ACInfinityClientCannotConnect("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientCannotConnect):
            await ac_infinity.update_device_settings(
                controller.devices[0], {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
            )

        assert mock_client.update_device_settings.call_count == 5

    @pytest.mark.parametrize(
        "exception_type",
        [
            ACInfinityClientCannotConnect("unit-test"),
            ACInfinityClientRequestFailed("unit-test"),
            aiohttp.ClientError("unit-test"),
            asyncio.TimeoutError(),
        ],
    )
    async def test_update_device_settings_retries_on_retryable_exceptions(
        self, mocker: MockFixture, mock_client, exception_type
    ):
        """update_device_settings should retry on retryable exceptions"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = exception_type

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(type(exception_type)):
            await ac_infinity.update_device_settings(
                controller.devices[0], {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
            )

        # Should retry 5 times total (initial + 4 retries)
        assert mock_client.update_device_settings.call_count == 5

    async def test_update_device_settings_raises_immediately_on_invalid_auth(
        self, mocker: MockFixture, mock_client
    ):
        """update_device_settings should raise immediately on authentication failure without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = ACInfinityClientInvalidAuth("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientInvalidAuth):
            await ac_infinity.update_device_settings(
                controller.devices[0], {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
            )

        # Should NOT retry on auth failure
        assert mock_client.update_device_settings.call_count == 1

    async def test_update_device_settings_raises_immediately_on_unexpected_exception(
        self, mocker: MockFixture, mock_client
    ):
        """update_device_settings should raise immediately on unexpected exceptions without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_device_settings.side_effect = ValueError("unexpected error")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        with pytest.raises(ValueError):
            await ac_infinity.update_device_settings(
                controller.devices[0], {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
            )

        # Should NOT retry on unexpected exceptions
        assert mock_client.update_device_settings.call_count == 1

    async def test_update_ai_device_control(self, mock_client):
        """Test updating a single AI device control calls the correct client method"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_control(ai_controller.devices[0], DeviceControlKey.AT_TYPE, 2)

        mock_client.update_ai_device_control_and_settings.assert_called_with(
            str(AI_DEVICE_ID), 1, {DeviceControlKey.AT_TYPE: 2}
        )

    async def test_update_ai_device_controls(self, mock_client):
        """Test updating multiple AI device controls calls the correct client method"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_controls(ai_controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        mock_client.update_ai_device_control_and_settings.assert_called_with(
            str(AI_DEVICE_ID), 1, {DeviceControlKey.AT_TYPE: 2}
        )

    async def test_update_ai_device_settings(self, mock_client):
        """Test updating AI device settings calls the correct client method"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.return_value = future

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        await ac_infinity.update_device_settings(
            ai_controller.devices[0], {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
        )

        mock_client.update_ai_device_control_and_settings.assert_called_with(
            str(AI_DEVICE_ID), 1, {AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY: 2}
        )

    async def test_update_ai_device_controls_retried_on_failure(self, mocker: MockFixture, mock_client):
        """AI device controls update should be tried 5 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.side_effect = ACInfinityClientCannotConnect("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientCannotConnect):
            await ac_infinity.update_device_controls(ai_controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        assert mock_client.update_ai_device_control_and_settings.call_count == 5

    @pytest.mark.parametrize(
        "exception_type",
        [
            ACInfinityClientCannotConnect("unit-test"),
            ACInfinityClientRequestFailed("unit-test"),
            aiohttp.ClientError("unit-test"),
            asyncio.TimeoutError(),
        ],
    )
    async def test_update_ai_device_controls_retries_on_retryable_exceptions(
        self, mocker: MockFixture, mock_client, exception_type
    ):
        """AI device controls update should retry on retryable exceptions"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.side_effect = exception_type

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        with pytest.raises(type(exception_type)):
            await ac_infinity.update_device_controls(ai_controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        # Should retry 5 times total (initial + 4 retries)
        assert mock_client.update_ai_device_control_and_settings.call_count == 5

    async def test_update_ai_device_controls_raises_immediately_on_invalid_auth(
        self, mocker: MockFixture, mock_client
    ):
        """AI device controls update should raise immediately on authentication failure without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.side_effect = ACInfinityClientInvalidAuth("unit-test")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        with pytest.raises(ACInfinityClientInvalidAuth):
            await ac_infinity.update_device_controls(ai_controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        # Should NOT retry on auth failure
        assert mock_client.update_ai_device_control_and_settings.call_count == 1

    async def test_update_ai_device_controls_raises_immediately_on_unexpected_exception(
        self, mocker: MockFixture, mock_client
    ):
        """AI device controls update should raise immediately on unexpected exceptions without retrying"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mock_client.is_logged_in.return_value = True
        mock_client.update_ai_device_control_and_settings.side_effect = ValueError("unexpected error")

        ac_infinity = ACInfinityService(mock_client)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_controls = DEVICE_CONTROLS_DATA

        ai_controller = ACInfinityController(AI_CONTROLLER_PROPERTIES)
        with pytest.raises(ValueError):
            await ac_infinity.update_device_controls(ai_controller.devices[0], {DeviceControlKey.AT_TYPE: 2})

        # Should NOT retry on unexpected exceptions
        assert mock_client.update_ai_device_control_and_settings.call_count == 1

    @pytest.mark.parametrize("is_suitable", [True, False])
    async def test_append_if_suitable_only_added_if_suitable(self, setup, is_suitable):
        test_objects: ACTestObjects = setup

        description = ACInfinityControllerSensorEntityDescription(
            key=ControllerPropertyKey.TEMPERATURE,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon=None,  # default
            translation_key="temperature",
            suggested_unit_of_measurement=None,
            enabled_fn=lambda entry, device_id, entity_config_key: True,
            suitable_fn=lambda e, c: is_suitable,
            get_value_fn=lambda e, c: None,
        )

        entity = ACInfinityControllerSensorEntity(
            test_objects.coordinator,
            description,
            ACInfinityController(CONTROLLER_PROPERTIES),
        )

        entities = ACInfinityEntities(test_objects.config_entry)
        entities.append_if_suitable(entity)

        assert len(entities) == (1 if is_suitable else 0)

    @pytest.mark.parametrize("is_enabled", [True, False])
    async def test_append_if_suitable_only_added_if_enabled(self, setup, is_enabled):
        test_objects: ACTestObjects = setup

        description = ACInfinityControllerSensorEntityDescription(
            key=ControllerPropertyKey.TEMPERATURE,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon=None,  # default
            translation_key="temperature",
            suggested_unit_of_measurement=None,
            enabled_fn=lambda entry, device_id, entity_config_key: is_enabled,
            suitable_fn=lambda e, c: True,
            get_value_fn=lambda e, c: None,
        )

        entity = ACInfinityControllerSensorEntity(
            test_objects.coordinator,
            description,
            ACInfinityController(CONTROLLER_PROPERTIES),
        )

        entities = ACInfinityEntities(test_objects.config_entry)
        entities.append_if_suitable(entity)

        assert len(entities) == (1 if is_enabled else 0)

    @pytest.mark.parametrize(
        "online_status, expected_available",
        [
            (1, True),  # Device online
            (0, False),  # Device offline
            (None, False),  # Device status unknown
        ],
    )
    @pytest.mark.parametrize("port", [1, 2, 3, 4])
    async def test_device_entity_available_based_on_online_status(
        self, setup, port, online_status, expected_available
    ):
        """Device entity availability should depend on device online status"""
        from custom_components.ac_infinity.const import DevicePropertyKey
        from custom_components.ac_infinity.sensor import ACInfinityDeviceSensorEntity, ACInfinityDeviceSensorEntityDescription

        test_objects: ACTestObjects = setup

        # Create a device entity
        description = ACInfinityDeviceSensorEntityDescription(
            key=DevicePropertyKey.SPEAK,
            device_class=SensorDeviceClass.POWER_FACTOR,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=None,
            icon=None,
            translation_key="current_power",
            suggested_unit_of_measurement=None,
            enabled_fn=lambda entry, device_id, entity_config_key: True,
            suitable_fn=lambda e, d: True,
            get_value_fn=lambda e, d: 0,
        )

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        device = controller.devices[port - 1]

        entity = ACInfinityDeviceSensorEntity(
            test_objects.coordinator,
            description,
            device,
        )

        # Set the online status
        test_objects.ac_infinity._device_properties[(str(DEVICE_ID), port)][
            DevicePropertyKey.ONLINE
        ] = online_status

        # Check availability
        assert entity.available == expected_available

    @pytest.mark.parametrize(
        "at_type_filter, current_at_type, online_status, expected_available",
        [
            # Device online scenarios
            (None, 7, 1, True),  # No filter, device online, any mode → available
            (None, 4, 1, True),  # No filter, device online, any mode → available
            (7, 7, 1, True),  # Filter matches (Schedule mode), device online → available
            (4, 4, 1, True),  # Filter matches (Timer to On mode), device online → available
            (5, 5, 1, True),  # Filter matches (Timer to Off mode), device online → available
            (7, 4, 1, False),  # Filter doesn't match (wants Schedule, has Timer to On), device online → unavailable
            (4, 7, 1, False),  # Filter doesn't match (wants Timer to On, has Schedule), device online → unavailable
            (5, 4, 1, False),  # Filter doesn't match (wants Timer to Off, has Timer to On), device online → unavailable

            # Device offline scenarios
            (None, 7, 0, False),  # No filter, device offline → unavailable
            (7, 7, 0, False),  # Filter matches, device offline → unavailable
            (4, 4, 0, False),  # Filter matches, device offline → unavailable
            (7, 4, 0, False),  # Filter doesn't match, device offline → unavailable

            # Device status unknown scenarios
            (None, 7, None, False),  # No filter, device status unknown → unavailable
            (7, 7, None, False),  # Filter matches, device status unknown → unavailable
        ],
    )
    @pytest.mark.parametrize("port", [1, 2])
    async def test_device_entity_available_based_on_at_type_and_online(
        self, setup, port, at_type_filter, current_at_type, online_status, expected_available
    ):
        """Device entity availability should depend on both online status and at_type filter

        Logic: available = super().available AND device_online AND (at_type is None OR at_type matches)
        """
        from custom_components.ac_infinity.const import DevicePropertyKey, DeviceControlKey
        from custom_components.ac_infinity.sensor import ACInfinityDeviceSensorEntity, ACInfinityDeviceSensorEntityDescription

        test_objects: ACTestObjects = setup

        # Create a device entity with at_type filter
        description = ACInfinityDeviceSensorEntityDescription(
            key=DevicePropertyKey.SPEAK,
            device_class=SensorDeviceClass.POWER_FACTOR,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=None,
            icon=None,
            translation_key="current_power",
            suggested_unit_of_measurement=None,
            enabled_fn=lambda entry, device_id, entity_config_key: True,
            suitable_fn=lambda e, d: True,
            get_value_fn=lambda e, d: 0,
        )

        controller = ACInfinityController(CONTROLLER_PROPERTIES)
        device = controller.devices[port - 1]

        # Create entity with at_type filter
        from custom_components.ac_infinity.core import ACInfinityDeviceEntity
        entity = ACInfinityDeviceEntity(
            test_objects.coordinator,
            device,
            lambda entry, device_id, entity_config_key: True,
            lambda e, d: True,
            at_type_filter,
            DevicePropertyKey.SPEAK,
            "sensor",
        )

        # Set the online status and current at_type
        test_objects.ac_infinity._device_properties[(str(DEVICE_ID), port)][
            DevicePropertyKey.ONLINE
        ] = online_status
        test_objects.ac_infinity._device_controls[(str(DEVICE_ID), port)][
            DeviceControlKey.AT_TYPE
        ] = current_at_type

        # Check availability
        assert entity.available == expected_available
