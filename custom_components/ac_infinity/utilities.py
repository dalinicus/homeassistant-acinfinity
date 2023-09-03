from .ac_infinity import ACInfinityDevice, ACInfinityDevicePort
from .const import DOMAIN


def get_device_property_unique_id(device: ACInfinityDevice, property_key: str):
    return f"{DOMAIN}_{device.mac_addr}_{property_key}"


def get_device_port_property_unique_id(
    device: ACInfinityDevice, port: ACInfinityDevicePort, property_key: str
):
    return f"{DOMAIN}_{device.mac_addr}_port_{port.port_id}_{property_key}"