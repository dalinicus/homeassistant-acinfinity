import asyncio
from asyncio import Future

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from pytest_mock import MockFixture
from pytest_mock.plugin import MockType

from custom_components.ac_infinity.client import ACInfinityClient
from custom_components.ac_infinity.const import (
    DOMAIN,
    MANUFACTURER,
    AdvancedSettingsKey,
    ControllerPropertyKey,
    PortControlKey,
    PortPropertyKey,
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
    AI_DEVICE_ID,
    CONTROLLER_ACCESS_PORT,
    CONTROLLER_PROPERTIES,
    CONTROLLER_PROPERTIES_DATA,
    DEVICE_ID,
    DEVICE_INFO_LIST_ALL,
    DEVICE_NAME,
    DEVICE_SETTINGS_DATA,
    EMAIL,
    GET_DEV_MODE_SETTING_LIST_PAYLOAD,
    GET_DEV_SETTINGS_PAYLOAD,
    MAC_ADDR,
    PASSWORD,
    PORT_CONTROLS_DATA,
    PORT_PROPERTIES_DATA,
    SENSOR_PROPERTIES_DATA,
)


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.mark.asyncio
class TestACInfinity:
    async def test_update_logged_in_should_be_called_if_not_logged_in(
        self, mocker: MockFixture
    ):
        """if client is already logged in, then log in should not be called"""

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=False)
        mocker.patch.object(
            ACInfinityClient, "get_devices_list_all", return_value=DEVICE_INFO_LIST_ALL
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_mode_settings_list",
            return_value=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_settings",
            return_value=GET_DEV_SETTINGS_PAYLOAD,
        )
        mock_login: MockType = mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        await ac_infinity.refresh()

        assert mock_login.called

    async def test_update_logged_in_should_not_be_called_if_not_necessary(
        self, mocker: MockFixture
    ):
        """if client is not already logged in, then log in should be called"""

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocker.patch.object(
            ACInfinityClient, "get_devices_list_all", return_value=DEVICE_INFO_LIST_ALL
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_mode_settings_list",
            return_value=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_settings",
            return_value=GET_DEV_SETTINGS_PAYLOAD,
        )
        mock_login: MockType = mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        await ac_infinity.refresh()
        assert not mock_login.called

    async def test_update_data_set(self, mocker: MockFixture):
        """data should be set once update is called"""

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocker.patch.object(
            ACInfinityClient, "get_devices_list_all", return_value=DEVICE_INFO_LIST_ALL
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_mode_settings_list",
            return_value=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_settings",
            return_value=GET_DEV_SETTINGS_PAYLOAD,
        )
        mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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

    async def test_update_retried_on_failure(self, mocker: MockFixture):
        """update should be tried 3 times before raising an exception"""
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch("asyncio.sleep", return_value=future)
        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mock_get_all = mocker.patch.object(
            ACInfinityClient,
            "get_devices_list_all",
            return_value=DEVICE_INFO_LIST_ALL,
            side_effect=Exception("unit-test"),
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_mode_settings_list",
            return_value=GET_DEV_MODE_SETTING_LIST_PAYLOAD,
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_settings",
            return_value=GET_DEV_SETTINGS_PAYLOAD,
        )
        mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)

        with pytest.raises(Exception):
            await ac_infinity.refresh()

        assert mock_get_all.call_count == 3

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
        self, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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
        self, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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
        self, property_key, device_id
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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
        self, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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
        self, device_id, property_key: str, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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
        self, property_key, device_id, access_port, sensor_type: int
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_sensor_property(
            device_id, access_port, sensor_type, property_key
        )
        assert result is None

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (PortPropertyKey.SPEAK, True),
            (PortPropertyKey.NAME, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID), "12345"])
    async def test_get_port_property_exists_returns_correct_value(
        self, device_id, property_key: str, value
    ):
        """getting a port property gets the correct property from the correct port"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_properties = PORT_PROPERTIES_DATA

        result = ac_infinity.get_port_property_exists(device_id, 1, property_key)
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "property_key, port_num, value",
        [
            (PortPropertyKey.SPEAK, 1, 5),
            (PortPropertyKey.SPEAK, 2, 7),
            (PortPropertyKey.NAME, 3, "Circulating Fan"),
            (PortPropertyKey.NAME, 1, "Grow Lights"),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_port_property_gets_correct_property(
        self, device_id, port_num, property_key: str, value
    ):
        """getting a port property gets the correct property from the correct port"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_properties = PORT_PROPERTIES_DATA

        result = ac_infinity.get_port_property(device_id, port_num, property_key)
        assert result == value

    @pytest.mark.parametrize(
        "property_key, device_id, port_num",
        [
            (PortPropertyKey.SPEAK, "232161", 1),
            ("MyFakeField", DEVICE_ID, 1),
            (PortPropertyKey.SPEAK, DEVICE_ID, 9),
            ("MyFakeField", str(DEVICE_ID), 1),
            (PortPropertyKey.SPEAK, str(DEVICE_ID), 9),
        ],
    )
    async def test_get_port_property_returns_null_properly(
        self, property_key, device_id, port_num
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_properties = PORT_PROPERTIES_DATA

        result = ac_infinity.get_port_property(device_id, port_num, property_key)
        assert result is None

    async def test_get_device_all_device_meta_data_returns_meta_data(self):
        """getting port device ids should return ids"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        result = ac_infinity.get_all_controller_properties()
        assert len(result) > 0

        device = result[0]
        assert device.device_id == str(DEVICE_ID)
        assert device.device_name == DEVICE_NAME
        assert device.mac_addr == MAC_ADDR
        assert [port.port_index for port in device.ports] == [1, 2, 3, 4]

    @pytest.mark.parametrize("data", [{}, None])
    async def test_get_device_all_device_meta_data_returns_empty_list(self, data):
        """getting device metadata returns empty list if no device exists or data isn't initialized"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = data

        result = ac_infinity.get_all_controller_properties()
        assert result == []

    @pytest.mark.parametrize(
        "dev_type,expected_model",
        [
            (11, "UIS Controller 69 Pro (CTR69P)"),
            (18, "UIS Controller 69 Pro+ (CTR69Q)"),
            (20, "UIS Controller AI+ (CTR89Q)"),
            (3, "UIS Controller Type 3"),
        ],
    )
    async def test_ac_infinity_device_has_correct_device_info(
        self, dev_type: int, expected_model: str
    ):
        """getting device returns a model object that contains correct device info for the device registry"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
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
            (PortControlKey.ON_SPEED, True),
            (PortControlKey.AT_TYPE, True),
            (AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, True),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_VPD, True),
            ("keyNoExist", False),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID), "12345"])
    async def test_get_port_control_exists_returns_correct_value(
        self, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        result = ac_infinity.get_port_control_exists(device_id, 1, setting_key)
        assert result == (value if device_id != "12345" else False)

    @pytest.mark.parametrize(
        "setting_key, value",
        [
            (PortControlKey.ON_SPEED, 5),
            (
                PortControlKey.OFF_SPEED,
                0,
            ),  # make sure 0 still returns 0 and not None or default
            (PortControlKey.AT_TYPE, 2),
            (AdvancedSettingsKey.DYNAMIC_RESPONSE_TYPE, 1),
            (AdvancedSettingsKey.DYNAMIC_BUFFER_VPD, 6),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_port_control_gets_correct_setting(
        self, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        result = ac_infinity.get_port_control(device_id, 1, setting_key)
        assert result == value

    @pytest.mark.parametrize("default_value", [0, None, 5455])
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_port_control_gets_returns_default_if_value_is_null(
        self, device_id, default_value
    ):
        """getting a port setting returns 0 instead of null if the key exists but the value is null"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        ac_infinity._port_controls[(str(DEVICE_ID), 1)][PortControlKey.SURPLUS] = None

        result = ac_infinity.get_port_control(
            device_id, 1, PortControlKey.SURPLUS, default_value=default_value
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
        self, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

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
        self, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        result = ac_infinity.get_controller_setting(device_id, setting_key)
        assert result == value

    @pytest.mark.parametrize("default_value", [0, None, 5455])
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_controller_setting_gets_returns_default_if_value_is_null(
        self, device_id, default_value
    ):
        """getting a port setting returns 0 instead of null if the key exists but the value is null"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        ac_infinity._port_controls[(str(DEVICE_ID), 1)][
            AdvancedSettingsKey.CALIBRATE_HUMIDITY
        ] = None

        result = ac_infinity.get_controller_setting(
            device_id,
            AdvancedSettingsKey.CALIBRATE_HUMIDITY,
            default_value=default_value,
        )
        assert result == default_value

    @pytest.mark.parametrize(
        "setting_key, device_id",
        [
            (PortControlKey.ON_SPEED, "232161"),
            ("MyFakeField", DEVICE_ID),
            (PortPropertyKey.NAME, DEVICE_ID),
            ("MyFakeField", str(DEVICE_ID)),
            (PortPropertyKey.NAME, str(DEVICE_ID)),
        ],
    )
    async def test_get_port_control_returns_null_properly(
        self,
        setting_key,
        device_id,
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        result = ac_infinity.get_port_control(device_id, 1, setting_key)
        assert result is None

    async def test_update_port_control(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_set = mocker.patch.object(
            ACInfinityClient, "set_device_mode_settings", return_value=future
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        await ac_infinity.update_port_control(DEVICE_ID, 1, PortControlKey.AT_TYPE, 2)

        mocked_set.assert_called_with(DEVICE_ID, 1, [(PortControlKey.AT_TYPE, 2)])

    async def test_update_port_controls(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_sets = mocker.patch.object(
            ACInfinityClient, "set_device_mode_settings", return_value=future
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        await ac_infinity.update_port_controls(
            DEVICE_ID, 1, [(PortControlKey.AT_TYPE, 2)]
        )

        mocked_sets.assert_called_with(DEVICE_ID, 1, [(PortControlKey.AT_TYPE, 2)])

    async def test_update_port_controls_retried_on_failure(self, mocker: MockFixture):
        """updating settings should be tried 3 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_sets = mocker.patch.object(
            ACInfinityClient,
            "set_device_mode_settings",
            return_value=future,
            side_effect=Exception("unit-test"),
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        with pytest.raises(Exception):
            await ac_infinity.update_port_controls(
                DEVICE_ID, 1, [(PortControlKey.AT_TYPE, 2)]
            )

        assert mocked_sets.call_count == 3

    async def test_update_controller_setting(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_set = mocker.patch.object(
            ACInfinityClient, "update_advanced_settings", return_value=future
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA

        await ac_infinity.update_controller_setting(
            DEVICE_ID, AdvancedSettingsKey.CALIBRATE_HUMIDITY, 2
        )

        mocked_set.assert_called_with(
            DEVICE_ID, 0, DEVICE_NAME, [(AdvancedSettingsKey.CALIBRATE_HUMIDITY, 2)]
        )

    async def test_update_controller_settings(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_set = mocker.patch.object(
            ACInfinityClient, "update_advanced_settings", return_value=future
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._device_settings = DEVICE_SETTINGS_DATA

        await ac_infinity.update_controller_settings(
            DEVICE_ID, [(AdvancedSettingsKey.CALIBRATE_HUMIDITY, 2)]
        )

        mocked_set.assert_called_with(
            DEVICE_ID, 0, DEVICE_NAME, [(AdvancedSettingsKey.CALIBRATE_HUMIDITY, 2)]
        )

    async def test_update_controller_settings_retried_on_failure(
        self, mocker: MockFixture
    ):
        """updating settings should be tried 3 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_sets = mocker.patch.object(
            ACInfinityClient,
            "update_advanced_settings",
            return_value=future,
            side_effect=Exception("unit-test"),
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        with pytest.raises(Exception):
            await ac_infinity.update_controller_settings(
                DEVICE_ID, [(AdvancedSettingsKey.CALIBRATE_HUMIDITY, 2)]
            )

        assert mocked_sets.call_count == 3

    async def test_update_port_setting(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_set = mocker.patch.object(
            ACInfinityClient, "update_advanced_settings", return_value=future
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_properties = PORT_PROPERTIES_DATA
        ac_infinity._port_properties[(str(DEVICE_ID), 1)][
            PortPropertyKey.NAME
        ] = DEVICE_NAME

        await ac_infinity.update_port_setting(
            DEVICE_ID, 1, AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 2
        )

        mocked_set.assert_called_with(
            DEVICE_ID,
            1,
            DEVICE_NAME,
            [(AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 2)],
        )

    async def test_update_port_settings(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_set = mocker.patch.object(
            ACInfinityClient, "update_advanced_settings", return_value=future
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_properties = PORT_PROPERTIES_DATA
        ac_infinity._port_properties[(str(DEVICE_ID), 1)][
            PortPropertyKey.NAME
        ] = DEVICE_NAME

        await ac_infinity.update_port_settings(
            DEVICE_ID, 1, [(AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 2)]
        )

        mocked_set.assert_called_with(
            DEVICE_ID,
            1,
            DEVICE_NAME,
            [(AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 2)],
        )

    async def test_update_port_settings_retried_on_failure(self, mocker: MockFixture):
        """updating settings should be tried 3 times before failing"""
        future: Future = asyncio.Future()
        future.set_result(None)
        mocker.patch("asyncio.sleep", return_value=future)
        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_sets = mocker.patch.object(
            ACInfinityClient,
            "update_advanced_settings",
            return_value=future,
            side_effect=Exception("unit-test"),
        )

        ac_infinity = ACInfinityService(EMAIL, PASSWORD)
        ac_infinity._controller_properties = CONTROLLER_PROPERTIES_DATA
        ac_infinity._port_controls = PORT_CONTROLS_DATA

        with pytest.raises(Exception):
            await ac_infinity.update_port_settings(
                DEVICE_ID, 1, [(AdvancedSettingsKey.DYNAMIC_TRANSITION_HUMIDITY, 2)]
            )

        assert mocked_sets.call_count == 3

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
            suitable_fn=lambda e, c: is_suitable,
            get_value_fn=lambda e, c: None,
        )

        entity = ACInfinityControllerSensorEntity(
            test_objects.coordinator,
            description,
            ACInfinityController(CONTROLLER_PROPERTIES),
        )

        entities = ACInfinityEntities()
        entities.append_if_suitable(entity)

        assert len(entities) == (1 if is_suitable else 0)
