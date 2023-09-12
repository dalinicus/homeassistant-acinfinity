import datetime
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity.ac_infinity import (
    ACInfinity,
    ACInfinityDevice,
    ACInfinityDevicePort,
)
from custom_components.ac_infinity.const import (
    DOMAIN,
    SETTING_KEY_SCHEDULED_END_TIME,
    SETTING_KEY_SCHEDULED_START_TIME,
)

from .utilities import get_device_port_property_name, get_device_port_property_unique_id

DEFAULT_TIME = datetime.time(0, 0)


class ACInfinityPortTimeEntity(TimeEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        setting_key: str,
        label: str,
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
        self._attr_native_value: time | None = None

    async def async_update(self) -> None:
        await self._acis.update()
        total_minutes = self._acis.get_device_port_setting(
            self._device.device_id, self._port.port_id, self._setting_key
        )

        # UIS stores a schedule value as minutes from midnight. A value of 0 is midnight.
        # Both 65535 and None could represent a value of "disabled"
        if total_minutes is not None and total_minutes // 60 <= 23:
            self._attr_native_value = datetime.time(
                hour=total_minutes // 60, minute=total_minutes % 60
            )
        else:
            self._attr_native_value = None

    async def async_set_value(self, value: time) -> None:
        total_minutes = None if value is None else (value.hour * 60) + value.minute
        await self._acis.set_device_port_setting(
            self._device.device_id, self._port.port_id, self._setting_key, total_minutes
        )
        self._attr_native_value = value


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    acis: ACInfinity = hass.data[DOMAIN][config.entry_id]

    select_entities = {
        SETTING_KEY_SCHEDULED_START_TIME: {"label": "Scheduled Start Time"},
        SETTING_KEY_SCHEDULED_END_TIME: {"label": "Scheduled End Time"},
    }

    await acis.update()
    devices = acis.get_all_device_meta_data()

    sensor_objects = []
    for device in devices:
        for port in device.ports:
            for key, descr in select_entities.items():
                sensor_objects.append(
                    ACInfinityPortTimeEntity(
                        acis,
                        device,
                        port,
                        key,
                        str(descr["label"]),
                    )
                )

    add_entities_callback(sensor_objects)
