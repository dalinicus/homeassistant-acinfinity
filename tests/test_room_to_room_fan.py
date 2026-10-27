"""
Regression tests for standalone room-to-room/through-wall fans (e.g. AC-TWT6,
devType 33). These devices have no ports and report insideTemp/outsideTemp
instead of a meaningful top-level "temperature" field.

This uses a sanitized capture of a real AC-TWT6's /api/user/devInfoListAll
entry (identifiers replaced) rather than the shared global fixtures in
data_models.py, since mutating those shared dicts would leak state into
unrelated test files.
"""
from types import SimpleNamespace

import pytest

from custom_components.ac_infinity.client import ACInfinityClient
from custom_components.ac_infinity.const import ControllerPropertyKey, ControllerType
from custom_components.ac_infinity.core import ACInfinityController, ACInfinityService
from custom_components.ac_infinity.sensor import CONTROLLER_DESCRIPTIONS

DEVICE_ID = "1111111111111111111"
MAC_ADDR = "AABBCCDDEEFF"

# Sanitized real-world capture of a devInfoListAll entry for an AC-TWT6.
ROOM_TO_ROOM_FAN_PROPERTIES = {
    "devId": DEVICE_ID,
    "devCode": "WA028",
    "devName": "Test Fan",
    "devType": ControllerType.UIS_ROOM_TO_ROOM_FAN,
    "devPortCount": 0,
    "devMacAddr": MAC_ADDR,
    "devVersion": 9,
    "online": 1,
    "isShare": 0,
    "devExternalList": None,
    "deviceInfo": {
        "devMacAddr": MAC_ADDR,
        "devId": DEVICE_ID,
        "temperature": 1860,  # stale/unused on this device type -- should be hidden
        "temperatureF": None,
        "humidity": 0,
        "unit": 0,
        "ports": [],
        "insideTemp": 2346,
        "insideTempF": 7423,
        "outsideTemp": 2260,
        "outsideTempF": 7268,
        "insideRoomName": "Utility Room",
        "outsideRoomName": "Living Room",
        "roomToRoomFan": True,
    },
    "appEmail": "test@example.com",
    "firmwareVersion": "3.0.31",
    "hardwareVersion": "3.0",
    "zoneId": "America/New_York",
}


def _get_description(key: str):
    matches = [d for d in CONTROLLER_DESCRIPTIONS if d.key == key]
    assert len(matches) == 1, f"expected exactly one description for {key}"
    return matches[0]


@pytest.fixture
def controller_and_service():
    client = ACInfinityClient("http://unittest.abcxyz", "test@example.com", "hunter2")
    service = ACInfinityService(client)
    service._controller_properties = {DEVICE_ID: ROOM_TO_ROOM_FAN_PROPERTIES}
    controller = ACInfinityController(ROOM_TO_ROOM_FAN_PROPERTIES)
    return controller, service


class TestRoomToRoomFan:
    def test_is_room_to_room_fan_true_for_devtype_33(self, controller_and_service):
        controller, _ = controller_and_service
        assert controller.is_room_to_room_fan is True
        assert controller.is_ai_controller is False

    def test_generic_temperature_sensor_not_suitable(self, controller_and_service):
        """The stale top-level 'temperature' field must not be surfaced for this device type."""
        controller, service = controller_and_service
        description = _get_description(ControllerPropertyKey.TEMPERATURE)
        entity = SimpleNamespace(data_key=description.key, ac_infinity=service)

        assert description.suitable_fn(entity, controller) is False

    def test_inside_temperature_sensor_suitable_and_correct(self, controller_and_service):
        controller, service = controller_and_service
        description = _get_description(ControllerPropertyKey.INSIDE_TEMP)
        entity = SimpleNamespace(data_key=description.key, ac_infinity=service)

        assert description.suitable_fn(entity, controller) is True
        assert description.get_value_fn(entity, controller) == 23.46

    def test_outside_temperature_sensor_suitable_and_correct(self, controller_and_service):
        controller, service = controller_and_service
        description = _get_description(ControllerPropertyKey.OUTSIDE_TEMP)
        entity = SimpleNamespace(data_key=description.key, ac_infinity=service)

        assert description.suitable_fn(entity, controller) is True
        assert description.get_value_fn(entity, controller) == 22.60

    def test_inside_outside_not_suitable_for_non_room_to_room_controllers(self):
        """A regular 69 Pro controller (no insideTemp/outsideTemp) shouldn't get these sensors."""
        client = ACInfinityClient("http://unittest.abcxyz", "test@example.com", "hunter2")
        service = ACInfinityService(client)

        regular_properties = {
            **ROOM_TO_ROOM_FAN_PROPERTIES,
            "devType": ControllerType.UIS_69_PRO,
        }
        service._controller_properties = {DEVICE_ID: regular_properties}
        controller = ACInfinityController(regular_properties)

        inside_description = _get_description(ControllerPropertyKey.INSIDE_TEMP)
        outside_description = _get_description(ControllerPropertyKey.OUTSIDE_TEMP)
        temperature_description = _get_description(ControllerPropertyKey.TEMPERATURE)

        entity = SimpleNamespace(data_key=inside_description.key, ac_infinity=service)
        assert inside_description.suitable_fn(entity, controller) is False

        entity = SimpleNamespace(data_key=outside_description.key, ac_infinity=service)
        assert outside_description.suitable_fn(entity, controller) is False

        entity = SimpleNamespace(data_key=temperature_description.key, ac_infinity=service)
        assert temperature_description.suitable_fn(entity, controller) is True
