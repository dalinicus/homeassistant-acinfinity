from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)

from .ac_infinity import ACInfinity, ACInfinityDevice, ACInfinityDevicePort


class ACInfinityBinarySensor(BinarySensorEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        property_key: str,
        sensor_label: str,
        device_class: str,
    ) -> None:
        self._acis = acis
        self._device = device

        self._property_key = property_key
        self._attr_device_class = device_class

        self._attr_unique_id = f"aci_{device.mac_addr}_{property_key}"
        self._attr_name = f"{device.device_name} {sensor_label}"

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_is_on = self._acis.get_device_property(
            self._device.device_id, self._property_key
        )

class ACInfinityPortBinarySensor(BinarySensorEntity):
    def __init__(
        self,
        acis: ACInfinity,
        device: ACInfinityDevice,
        port: ACInfinityDevicePort,
        uuid: str,
        property_key: str,
        sensor_label: str,
        device_class: str,
        unit: str,
    ) -> None:
        self._acis = acis
        self._device = device
        self._port = port

        self._property_key = property_key
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

        self._attr_unique_id = f"aci_{uuid}_{device.mac_addr}_port_{port.port_id}_{property_key}"
        self._attr_name = f"{device.device_name} {port.port_name} {sensor_label}"

    async def async_update(self) -> None:
        await self._acis.update()
        self._attr_is_on = self._acis.get_device_port_property(
            self._device.device_id, self._port.port_id, self._property_key
        )
