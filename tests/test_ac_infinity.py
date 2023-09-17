import asyncio
from asyncio import Future

import pytest
from pytest_mock import MockFixture
from pytest_mock.plugin import MockType

from custom_components.ac_infinity.ac_infinity import ACInfinity
from custom_components.ac_infinity.client import ACInfinityClient
from custom_components.ac_infinity.const import (
    DOMAIN,
    MANUFACTURER,
    PROPERTY_KEY_DEVICE_NAME,
    PROPERTY_KEY_MAC_ADDR,
    PROPERTY_PORT_KEY_NAME,
    SENSOR_KEY_HUMIDITY,
    SENSOR_KEY_TEMPERATURE,
    SENSOR_PORT_KEY_SPEAK,
    SENSOR_SETTING_KEY_SURPLUS,
    SETTING_KEY_AT_TYPE,
    SETTING_KEY_OFF_SPEED,
    SETTING_KEY_ON_SPEED,
)

from .data_models import (
    DEVICE_ID,
    DEVICE_INFO_DATA,
    DEVICE_INFO_LIST_ALL,
    DEVICE_NAME,
    DEVICE_SETTINGS,
    DEVICE_SETTINGS_PAYLOAD,
    EMAIL,
    MAC_ADDR,
    PASSWORD,
)


@pytest.mark.asyncio
class TestACInfinity:
    async def test_update_logged_in_should_be_called_if_not_logged_in(
        self, mocker: MockFixture
    ):
        """if client is already logged in, than log in should not be called"""

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=False)
        mocker.patch.object(
            ACInfinityClient, "get_all_device_info", return_value=DEVICE_INFO_LIST_ALL
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_port_settings",
            return_value=DEVICE_SETTINGS_PAYLOAD,
        )
        mockLogin: MockType = mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        await ac_infinity.update()

        assert mockLogin.called

    async def test_update_logged_in_should_not_be_called_if_not_necessary(
        self, mocker: MockFixture
    ):
        """if client is not already logged in, than log in should be called"""

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocker.patch.object(
            ACInfinityClient, "get_all_device_info", return_value=DEVICE_INFO_LIST_ALL
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_port_settings",
            return_value=DEVICE_SETTINGS_PAYLOAD,
        )
        mockLogin: MockType = mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        await ac_infinity.update()
        assert not mockLogin.called

    async def test_update_data_set(self, mocker: MockFixture):
        """data should be set once update is called"""

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocker.patch.object(
            ACInfinityClient, "get_all_device_info", return_value=DEVICE_INFO_LIST_ALL
        )
        mocker.patch.object(
            ACInfinityClient,
            "get_device_port_settings",
            return_value=DEVICE_SETTINGS_PAYLOAD,
        )
        mocker.patch.object(ACInfinityClient, "login")

        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        await ac_infinity.update()

        assert len(ac_infinity._devices) == 1
        assert (
            ac_infinity._devices[str(DEVICE_ID)][PROPERTY_KEY_DEVICE_NAME]
            == "Grow Tent"
        )

    @pytest.mark.parametrize(
        "property_key, value",
        [
            (PROPERTY_KEY_DEVICE_NAME, "Grow Tent"),
            (PROPERTY_KEY_MAC_ADDR, MAC_ADDR),
            (SENSOR_KEY_TEMPERATURE, 2417),
            (SENSOR_KEY_HUMIDITY, 7200),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_device_property_gets_correct_property(
        self, device_id, property_key, value
    ):
        """getting a device property returns the correct value"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA

        result = ac_infinity.get_device_property(device_id, property_key)
        assert result == value

    @pytest.mark.parametrize(
        "property_key, device_id",
        [
            (PROPERTY_KEY_DEVICE_NAME, "232161"),
            ("MyFakeField", DEVICE_ID),
            ("MyFakeField", str(DEVICE_ID)),
        ],
    )
    async def test_get_device_property_returns_null_properly(
        self, property_key, device_id
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA

        result = ac_infinity.get_device_property(device_id, property_key)
        assert result is None

    @pytest.mark.parametrize(
        "property_key, port_num, value",
        [
            (SENSOR_PORT_KEY_SPEAK, 1, 5),
            (SENSOR_PORT_KEY_SPEAK, 2, 7),
            (PROPERTY_PORT_KEY_NAME, 3, "Circulating Fan"),
            (PROPERTY_PORT_KEY_NAME, 1, "Grow Lights"),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_device_port_property_gets_correct_property(
        self, device_id, port_num, property_key, value
    ):
        """getting a porp property gets the correct property from the correct port"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA

        result = ac_infinity.get_device_port_property(device_id, port_num, property_key)
        assert result == value

    @pytest.mark.parametrize(
        "property_key, device_id, port_num",
        [
            (SENSOR_PORT_KEY_SPEAK, "232161", 1),
            ("MyFakeField", DEVICE_ID, 1),
            (SENSOR_PORT_KEY_SPEAK, DEVICE_ID, 9),
            ("MyFakeField", str(DEVICE_ID), 1),
            (SENSOR_PORT_KEY_SPEAK, str(DEVICE_ID), 9),
        ],
    )
    async def test_get_device_port_property_returns_null_properly(
        self, property_key, device_id, port_num
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA

        result = ac_infinity.get_device_port_property(device_id, port_num, property_key)
        assert result is None

    async def test_get_device_all_device_meta_data_returns_meta_data(self):
        """getting port device ids should return ids"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA

        result = ac_infinity.get_all_device_meta_data()
        assert len(result) > 0

        device = result[0]
        assert device.device_id == str(DEVICE_ID)
        assert device.device_name == DEVICE_NAME
        assert device.mac_addr == MAC_ADDR
        assert [port.port_id for port in device.ports] == [1, 2, 3, 4]

    @pytest.mark.parametrize("data", [{}, None])
    async def test_get_device_all_device_meta_data_returns_empty_list(self, data):
        """getting device metadata returns empty list if no device exists or data isn't initialized"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = data

        result = ac_infinity.get_all_device_meta_data()
        assert result == []

    @pytest.mark.parametrize(
        "devType,expected_model",
        [(11, "UIS Controller 69 Pro (CTR69P)"), (3, "UIS Controller Type 3")],
    )
    async def test_ac_infinity_device_has_correct_device_info(
        self, devType: int, expected_model: str
    ):
        """getting device returns an model object that contains correct device info for the device registry"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._devices[str(DEVICE_ID)]["devType"] = devType

        result = ac_infinity.get_all_device_meta_data()
        assert len(result) > 0

        device = result[0]
        device_info = device._device_info
        assert (DOMAIN, str(DEVICE_ID)) in device_info.get("identifiers")
        assert device_info.get("hw_version") == "1.1"
        assert device_info.get("sw_version") == "3.2.25"
        assert device_info.get("name") == DEVICE_NAME
        assert device_info.get("manufacturer") == MANUFACTURER
        assert device_info.get("model") == expected_model

    @pytest.mark.parametrize(
        "setting_key, value",
        [
            (SETTING_KEY_ON_SPEED, 5),
            (
                SETTING_KEY_OFF_SPEED,
                0,
            ),  # make sure 0 still returns 0 and not None or default
            (SETTING_KEY_AT_TYPE, 2),
        ],
    )
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_device_port_setting_gets_correct_property(
        self, device_id, setting_key, value
    ):
        """getting a port setting gets the correct setting from the correct port"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._port_settings = DEVICE_SETTINGS

        result = ac_infinity.get_device_port_setting(device_id, 1, setting_key)
        assert result == value

    @pytest.mark.parametrize("default_value", [0, None, 5455])
    @pytest.mark.parametrize("device_id", [DEVICE_ID, str(DEVICE_ID)])
    async def test_get_device_port_setting_gets_returns_default_if_value_is_null(
        self, device_id, default_value
    ):
        """getting a port setting returns 0 instead of null if the key exists but the value is null"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._port_settings = DEVICE_SETTINGS

        ac_infinity._port_settings[str(DEVICE_ID)][1][SENSOR_SETTING_KEY_SURPLUS] = None

        result = ac_infinity.get_device_port_setting(
            device_id, 1, SENSOR_SETTING_KEY_SURPLUS, default_value=default_value
        )
        assert result == default_value

    @pytest.mark.parametrize(
        "setting_key, device_id",
        [
            (SETTING_KEY_ON_SPEED, "232161"),
            ("MyFakeField", DEVICE_ID),
            (PROPERTY_PORT_KEY_NAME, DEVICE_ID),
            ("MyFakeField", str(DEVICE_ID)),
            (PROPERTY_PORT_KEY_NAME, str(DEVICE_ID)),
        ],
    )
    async def test_get_device_port_setting_returns_null_properly(
        self,
        setting_key,
        device_id,
    ):
        """the absence of a value should return None instead of keyerror"""
        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._port_settings = DEVICE_SETTINGS

        result = ac_infinity.get_device_port_setting(device_id, 1, setting_key)
        assert result is None

    async def test_set_device_port_setting(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_set = mocker.patch.object(
            ACInfinityClient, "set_device_port_setting", return_value=future
        )

        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._port_settings = DEVICE_SETTINGS

        await ac_infinity.set_device_port_setting(DEVICE_ID, 1, SETTING_KEY_AT_TYPE, 2)

        mocked_set.assert_called_with(DEVICE_ID, 1, SETTING_KEY_AT_TYPE, 2)

    async def test_set_device_port_settings(self, mocker: MockFixture):
        future: Future = asyncio.Future()
        future.set_result(None)

        mocker.patch.object(ACInfinityClient, "is_logged_in", return_value=True)
        mocked_sets = mocker.patch.object(
            ACInfinityClient, "set_device_port_settings", return_value=future
        )

        ac_infinity = ACInfinity(EMAIL, PASSWORD)
        ac_infinity._devices = DEVICE_INFO_DATA
        ac_infinity._port_settings = DEVICE_SETTINGS

        await ac_infinity.set_device_port_settings(
            DEVICE_ID, 1, [(SETTING_KEY_AT_TYPE, 2)]
        )

        mocked_sets.assert_called_with(DEVICE_ID, 1, [(SETTING_KEY_AT_TYPE, 2)])
