import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity import (
    ACInfinityDataUpdateCoordinator,
    ACInfinityPortPropertyEntity,
)
from custom_components.ac_infinity.const import DOMAIN, SENSOR_PORT_KEY_ONLINE

from .ac_infinity import ACInfinityDevice, ACInfinityDevicePort

_LOGGER = logging.getLogger(__name__)


class ACInfinityPortBinarySensorEntity(
    ACInfinityPortPropertyEntity, BinarySensorEntity
):
    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        data_key: str,
        label: str,
        device_class: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device, port, data_key, label, icon)
        self._attr_device_class = device_class
        self._attr_is_on = self.get_property_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.get_property_value()
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s._attr_is_on updated to %s", self._attr_unique_id, self._attr_is_on
        )


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, add_entities_callback: AddEntitiesCallback
) -> None:
    """Setup the AC Infinity Platform."""

    coordinator: ACInfinityDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]

    device_sensors = {
        SENSOR_PORT_KEY_ONLINE: {
            "label": "Status",
            "deviceClass": BinarySensorDeviceClass.PLUG,
            "icon": "mdi:power",
        },
    }

    devices = coordinator.ac_infinity.get_all_device_meta_data()

    entities: list[ACInfinityPortBinarySensorEntity] = []
    for device in devices:
        for port in device.ports:
            for key, descr in device_sensors.items():
                entities.append(
                    ACInfinityPortBinarySensorEntity(
                        coordinator,
                        device,
                        port,
                        key,
                        descr["label"],
                        descr["deviceClass"],
                        descr["icon"],
                    )
                )

    add_entities_callback(entities)
