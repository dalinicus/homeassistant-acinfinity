from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity.ac_infinity import (
    ACInfinity,
    ACInfinityDevice,
    ACInfinityDevicePort,
)
from custom_components.ac_infinity.const import DOMAIN, SETTING_KEY_AT_TYPE

from .utilities import get_device_port_property_name, get_device_port_property_unique_id


class ACInfinityPortSelectEntity(SelectEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        setting_key: str,
        label: str,
        options: list[str],
    ) -> None:
        self._acis = acis
        self._device = device
        self._port = port
        self._setting_key = setting_key

        self._attr_device_info = port.device_info
        self._attr_unique_id = get_device_port_property_unique_id(
            device, port, setting_key
        )
        self._attr_name = get_device_port_property_name(device, port, label)
        self._attr_options = options
        self._attr_current_option = options[0]

    async def async_update(self) -> None:
        await self._acis.update()
        option = self._acis.get_device_port_setting(
            self._device.device_id, self._port.port_id, self._setting_key
        )
        self._attr_current_option = self._attr_options[option - 1]  # 1 to 0 based array

    async def async_select_option(self, option: str) -> None:
        index = self._attr_options.index(option)

        await self._acis.set_device_port_setting(
            self._device.device_id, self._port.port_id, self._setting_key, index + 1
        )  # 0 to 1 based array
        self._attr_current_option = option


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    select_entities = {
        SETTING_KEY_AT_TYPE: {
            "label": "Mode",
            "options": [
                "Off",
                "On",
                "Auto",
                "Timer to On",
                "Timer to Off",
                "Cycle",
                "Schedule",
                "VPD",
            ],
        }
    }

    await acis.update()
    devices = acis.get_all_device_meta_data()

    sensor_objects = []
    for device in devices:
        for port in device.ports:
            for key, descr in select_entities.items():
                sensor_objects.append(
                    ACInfinityPortSelectEntity(
                        acis,
                        device,
                        port,
                        key,
                        str(descr["label"]),
                        list[str](descr["options"]),
                    )
                )

    add_entities_callback(sensor_objects)
