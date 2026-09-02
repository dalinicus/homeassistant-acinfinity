"""AIRTAP AI register fans: standalone Wi-Fi devices with no ports, controlled through port 0."""
import re
from types import SimpleNamespace
from typing import cast
from urllib.parse import parse_qsl

import pytest
from aioresponses import aioresponses
from homeassistant.config_entries import ConfigEntry
from pytest_mock import MockFixture

from custom_components.ac_infinity.client import (
    API_URL_GET_DEV_MODE_SETTING,
    API_URL_MODE_AND_SETTINGS,
    ACInfinityClient,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    AtType,
    ControllerPropertyKey,
    ControllerType,
    ConfigurationKey,
    DeviceControlKey,
    DevicePropertyKey,
    EntityConfigValue,
)
from custom_components.ac_infinity.core import (
    ACInfinityController,
    ACInfinityEntities,
    ACInfinityService,
)
from custom_components.ac_infinity.select import (
    DEVICE_DESCRIPTIONS as SELECT_DEVICE_DESCRIPTIONS,
    ACInfinityDeviceSelectEntity,
)
from custom_components.ac_infinity.number import (
    DEVICE_DESCRIPTIONS as NUMBER_DEVICE_DESCRIPTIONS,
    ACInfinityDeviceNumberEntity,
)
from tests import setup_entity_mocks
from tests.data_models import (
    DEVICE_CONTROLS,
    EMAIL,
    GET_DEV_MODE_SETTING_LIST_PAYLOAD,
    HOST,
    PASSWORD,
    UPDATE_SUCCESS_PAYLOAD,
    USER_ID,
)

AIRTAP_DEVICE_ID = 1424979258063655466
AIRTAP_MAC_ADDR = "E8F60AF1BBAC"
AIRTAP_NAME = "Master Bedroom Left"

# trimmed from a real /api/user/devInfoListAll response for an AIRTAP AI
AIRTAP_CONTROLLER_PROPERTIES = {
    "devId": str(AIRTAP_DEVICE_ID),
    "devCode": "WQA13",
    "devName": AIRTAP_NAME,
    "devType": ControllerType.AIRTAP_AI,
    "devPortCount": 0,
    "devMacAddr": AIRTAP_MAC_ADDR,
    "online": 1,
    "deviceInfo": {
        "devMacAddr": AIRTAP_MAC_ADDR,
        "devId": AIRTAP_DEVICE_ID,
        "temperature": 1730,
        "temperatureF": 6320,
        "humidity": None,
        "unit": 0,
        "speak": 10,
        "curMode": 0,
        "remainTime": 0,
        "online": 1,
        "ports": [],
        "sensors": None,
        "power": 790,
    },
    "firmwareVersion": "5.0.26",
    "hardwareVersion": "3.0",
    "airTap": True,
    "homeDev": True,
    "newFrameworkDevice": True,
}

AIRTAP_DEVICE_CONTROLS = {**DEVICE_CONTROLS, "devId": str(AIRTAP_DEVICE_ID), "externalPort": 0, "atType": AtType.AI, "onSpead": 10, "offSpead": 0}
AIRTAP_GET_DEV_MODE_SETTING_LIST_PAYLOAD = {"msg": "success.", "code": 200, "data": AIRTAP_DEVICE_CONTROLS}
NO_DATA_PAYLOAD = {"msg": "success.", "code": 200}


@pytest.fixture(autouse=True)
def isolate_service_caches():
    """ACInfinityService keeps its caches as class attributes; keep this module's refreshes from leaking into other tests."""
    names = ("_controller_properties", "_sensor_properties", "_device_properties", "_device_controls", "_device_settings")
    saved = {name: dict(getattr(ACInfinityService, name)) for name in names}
    yield
    for name in names:
        getattr(ACInfinityService, name).clear()
        getattr(ACInfinityService, name).update(saved[name])


@pytest.fixture
def setup(mocker: MockFixture):
    return setup_entity_mocks(mocker)


@pytest.fixture
def mock_client(mocker: MockFixture):
    return mocker.create_autospec(ACInfinityClient, spec_set=True)


async def refreshed_service(mock_client) -> ACInfinityService:
    mock_client.is_logged_in.return_value = True
    mock_client.get_account_controllers.return_value = [AIRTAP_CONTROLLER_PROPERTIES]
    mock_client.get_device_mode_settings.return_value = AIRTAP_DEVICE_CONTROLS
    ac_infinity = ACInfinityService(mock_client)
    await ac_infinity.refresh()
    return ac_infinity


class TestAirtapController:
    def test_detected_by_flag_or_device_type(self):
        assert ACInfinityController.is_airtap_json(AIRTAP_CONTROLLER_PROPERTIES)
        assert ACInfinityController.is_airtap_json({**AIRTAP_CONTROLLER_PROPERTIES, "airTap": False})
        assert ACInfinityController.is_airtap_json({**AIRTAP_CONTROLLER_PROPERTIES, "devType": 11, "airTap": True})
        assert not ACInfinityController.is_airtap_json({**AIRTAP_CONTROLLER_PROPERTIES, "devType": 11, "airTap": False})
        assert not ACInfinityController.is_airtap_json({"devType": 11, "deviceInfo": {"ports": []}})

    def test_fan_is_exposed_as_port_zero(self):
        controller = ACInfinityController(AIRTAP_CONTROLLER_PROPERTIES)

        assert controller.is_airtap
        assert not controller.is_ai_controller
        assert controller.device_info.get("model") == "AIRTAP AI Register Booster Fan"
        assert [device.device_port for device in controller.devices] == [0]
        assert controller.devices[0].device_name == AIRTAP_NAME

    def test_port_zero_entities_attach_to_the_fan_device(self):
        controller = ACInfinityController(AIRTAP_CONTROLLER_PROPERTIES)

        assert controller.devices[0].device_info is controller.device_info
        assert controller.device_info.get("identifiers") == {(DOMAIN, str(AIRTAP_DEVICE_ID))}

    def test_controllers_with_ports_are_unchanged(self):
        ports = [{"port": 1, "portName": "Fan"}, {"port": 2, "portName": "Light"}]
        controller_json = {**AIRTAP_CONTROLLER_PROPERTIES, "airTap": False, "devType": 11, "deviceInfo": {**AIRTAP_CONTROLLER_PROPERTIES["deviceInfo"], "ports": ports}}

        assert ACInfinityController.get_port_jsons(controller_json) == ports
        assert ACInfinityController.get_port_jsons({**controller_json, "deviceInfo": {"ports": None}}) == []


@pytest.mark.asyncio
class TestAirtapService:
    async def test_refresh_populates_port_zero(self, mock_client):
        ac_infinity = await refreshed_service(mock_client)

        assert ac_infinity.get_device_ports(AIRTAP_DEVICE_ID) == [0]
        assert ac_infinity.get_device_property(AIRTAP_DEVICE_ID, 0, DevicePropertyKey.SPEAK) == 10
        assert ac_infinity.get_device_property(AIRTAP_DEVICE_ID, 0, DevicePropertyKey.NAME) == AIRTAP_NAME
        assert ac_infinity.get_device_control(AIRTAP_DEVICE_ID, 0, DeviceControlKey.AT_TYPE) == AtType.AI
        assert ac_infinity.get_controller_property(AIRTAP_DEVICE_ID, ControllerPropertyKey.TEMPERATURE) == 1730

    async def test_controls_are_written_through_the_airtap_path(self, mock_client):
        ac_infinity = await refreshed_service(mock_client)
        device = ac_infinity.get_all_controller_properties()[0].devices[0]

        await ac_infinity.update_device_control(device, DeviceControlKey.AT_TYPE, AtType.ON)

        mock_client.update_airtap_controls.assert_called_once_with(str(AIRTAP_DEVICE_ID), {DeviceControlKey.AT_TYPE: AtType.ON})
        assert not mock_client.update_device_controls.called
        assert not mock_client.update_ai_device_control_and_settings.called

    async def test_settings_are_not_writable(self, mock_client):
        ac_infinity = await refreshed_service(mock_client)
        controller = ac_infinity.get_all_controller_properties()[0]

        with pytest.raises(NotImplementedError):
            await ac_infinity.update_controller_settings(controller, {"devCt": 1})
        with pytest.raises(NotImplementedError):
            await ac_infinity.update_device_settings(controller.devices[0], {"devCt": 1})


@pytest.mark.asyncio
class TestAirtapEntities:
    async def test_only_verified_entities_are_created(self, setup, mock_client):
        """Only the mode, speeds and current power are exposed; timers, triggers, VPD, ... are hidden."""
        ac_infinity = await refreshed_service(mock_client)
        setup.coordinator._ac_infinity = ac_infinity
        device = ac_infinity.get_all_controller_properties()[0].devices[0]
        config = cast(ConfigEntry, SimpleNamespace(data={ConfigurationKey.ENTITIES: {str(AIRTAP_DEVICE_ID): {"port_0": EntityConfigValue.ALL}}}))

        selects = ACInfinityEntities(config)
        for description in SELECT_DEVICE_DESCRIPTIONS:
            selects.append_if_suitable(ACInfinityDeviceSelectEntity(setup.coordinator, description, device))
        numbers = ACInfinityEntities(config)
        for description in NUMBER_DEVICE_DESCRIPTIONS:
            numbers.append_if_suitable(ACInfinityDeviceNumberEntity(setup.coordinator, description, device))

        assert [entity.data_key for entity in selects] == [DeviceControlKey.AT_TYPE]
        select = cast(ACInfinityDeviceSelectEntity, selects[0])
        assert select.options == ["AI", "Off", "On"]
        assert select.current_option == "AI"
        assert select.device_info.get("identifiers") == {(DOMAIN, str(AIRTAP_DEVICE_ID))}
        assert sorted(entity.data_key for entity in numbers) == sorted([DeviceControlKey.ON_SPEED, DeviceControlKey.OFF_SPEED])

    async def test_mode_select_writes_through_the_service(self, setup, mock_client):
        ac_infinity = await refreshed_service(mock_client)
        setup.coordinator._ac_infinity = ac_infinity
        device = ac_infinity.get_all_controller_properties()[0].devices[0]
        description = next(d for d in SELECT_DEVICE_DESCRIPTIONS if d.options and "AI" in d.options)
        entity = ACInfinityDeviceSelectEntity(setup.coordinator, description, device)

        await entity.async_select_option("On")

        mock_client.update_airtap_controls.assert_called_once_with(str(AIRTAP_DEVICE_ID), {DeviceControlKey.AT_TYPE: AtType.ON})
        with pytest.raises(ValueError):
            await entity.async_select_option("Auto")


@pytest.mark.asyncio
class TestAirtapClient:
    @staticmethod
    async def __send(key_values, existing=AIRTAP_DEVICE_CONTROLS):
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                mocked.post(re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*"), status=200, payload={"code": 200, "msg": "success.", "data": existing})
                mocked.put(re.compile(rf"{HOST}{API_URL_MODE_AND_SETTINGS}.*"), status=200, payload=UPDATE_SUCCESS_PAYLOAD)

                await client.update_airtap_controls(AIRTAP_DEVICE_ID, key_values)

                for (method, url), calls in mocked.requests.items():
                    if method == "PUT" and API_URL_MODE_AND_SETTINGS in str(url):
                        return dict(parse_qsl(url.raw_query_string, keep_blank_values=True)), calls[0].kwargs["headers"]
            raise AssertionError("no PUT sent")
        finally:
            await client.close()

    async def test_on_sends_mode_and_on_speed(self):
        params, headers = await self.__send({DeviceControlKey.AT_TYPE: AtType.ON, DeviceControlKey.ON_SPEED: 7})
        assert params == {"atType": "2", "devId": str(AIRTAP_DEVICE_ID), "port": "0", "onSpeed": "7", "modeAndSettingIdStr": "[16,18]"}
        assert headers["minversion"] == "3.5"

    async def test_on_without_speed_keeps_existing_on_speed(self):
        params, _ = await self.__send({DeviceControlKey.AT_TYPE: AtType.ON})
        assert params["onSpeed"] == "10" and params["modeAndSettingIdStr"] == "[16,18]"

    async def test_off_sends_off_speed(self):
        params, _ = await self.__send({DeviceControlKey.AT_TYPE: AtType.OFF})
        assert params == {"atType": "1", "devId": str(AIRTAP_DEVICE_ID), "port": "0", "offSpeed": "0", "modeAndSettingIdStr": "[16,17]"}

    async def test_ai_sends_only_mode(self):
        params, _ = await self.__send({DeviceControlKey.AT_TYPE: AtType.AI})
        assert params == {"atType": "0", "devId": str(AIRTAP_DEVICE_ID), "port": "0", "modeAndSettingIdStr": "[16]"}

    async def test_speed_change_keeps_current_mode(self):
        params, _ = await self.__send({DeviceControlKey.ON_SPEED: 4}, existing={**AIRTAP_DEVICE_CONTROLS, "atType": AtType.ON})
        assert params["atType"] == "2" and params["onSpeed"] == "4" and params["modeAndSettingIdStr"] == "[16,18]"

    async def test_unsupported_mode_rejected(self):
        with pytest.raises(ValueError):
            await self.__send({DeviceControlKey.AT_TYPE: AtType.AUTO})

    async def test_unsupported_key_rejected(self):
        with pytest.raises(ValueError):
            await self.__send({DeviceControlKey.TIMER_DURATION_TO_ON: 5})

    async def test_get_device_mode_settings_retries_with_min_version_when_data_missing(self):
        """Some devices only answer getdevModeSettingList when the minversion header is sent."""
        client = ACInfinityClient(HOST, EMAIL, PASSWORD)
        client._user_id = USER_ID
        try:
            with aioresponses() as mocked:
                url = re.compile(rf"{HOST}{API_URL_GET_DEV_MODE_SETTING}.*")
                mocked.post(url, status=200, payload=NO_DATA_PAYLOAD)
                mocked.post(url, status=200, payload=GET_DEV_MODE_SETTING_LIST_PAYLOAD)

                result = await client.get_device_mode_settings(AIRTAP_DEVICE_ID, 0)

                calls = next(calls for (method, u), calls in mocked.requests.items() if method == "POST" and API_URL_GET_DEV_MODE_SETTING in str(u))
                assert len(calls) == 2
                assert "minversion" not in calls[0].kwargs["headers"]
                assert calls[1].kwargs["headers"]["minversion"] == "3.5"
                assert result == DEVICE_CONTROLS
        finally:
            await client.close()


class TestNewDeviceDefaults:
    """Devices or ports added after setup have no saved entity configuration; they must default to sensors only
    instead of raising KeyError and taking the whole platform down."""

    def test_unknown_device_defaults_to_sensors_only(self):
        from custom_components.ac_infinity.core import enabled_fn_control, enabled_fn_sensor, enabled_fn_setting
        entry = cast(ConfigEntry, SimpleNamespace(data={ConfigurationKey.ENTITIES: {"known": {"port_1": EntityConfigValue.ALL}}}))
        assert enabled_fn_sensor(entry, "new-device", "port_0")
        assert not enabled_fn_control(entry, "new-device", "port_0")
        assert not enabled_fn_setting(entry, "new-device", "port_0")
        assert not enabled_fn_control(entry, "known", "port_2")
        assert enabled_fn_control(entry, "known", "port_1")

    def test_options_flow_schema_defaults_for_unknown_device(self, mock_client):
        """The options flow must build its form for a device that was added after setup."""
        import asyncio
        from custom_components.ac_infinity.config_flow import OptionsFlow
        ac_infinity = asyncio.get_event_loop().run_until_complete(refreshed_service(mock_client))
        flow = OptionsFlow()
        entities, placeholders = flow._build_entity_config_schema(ac_infinity, AIRTAP_DEVICE_ID, data={ConfigurationKey.ENTITIES: {}})
        assert placeholders["port_0"] == AIRTAP_NAME
        assert {str(k) for k in entities} == {"controller", "sensors", "port_0"}
        assert all(getattr(k, "default")() == EntityConfigValue.SENSORS_ONLY for k in entities)
