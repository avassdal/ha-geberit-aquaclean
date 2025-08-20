"""Config flow for Geberit AquaClean integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from bleak import BleakScanner

from .const import DOMAIN
from .geberit_client import GeberitAquaCleanClient
from .scanner import get_scanner, DiscoveredDevice

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): str,
    }
)

STEP_DEVICE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("device"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, any]) -> dict[str, any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    mac_address = data[CONF_MAC]

    # Validate MAC address format
    if not _is_valid_mac(mac_address):
        raise InvalidMac

    # Try to find the device
    device = await BleakScanner.find_device_by_address(mac_address, timeout=10.0)
    if not device:
        raise CannotConnect

    # Try to connect to validate the device
    client = GeberitAquaCleanClient(mac_address)
    if not await client.connect():
        await client.disconnect()
        raise CannotConnect

    await client.disconnect()

    # Return info that you want to store in the config entry.
    return {"title": f"Geberit AquaClean ({mac_address})"}


def _is_valid_mac(mac: str) -> bool:
    """Check if MAC address is valid."""
    try:
        # Check format XX:XX:XX:XX:XX:XX
        parts = mac.split(":")
        if len(parts) != 6:
            return False
        for part in parts:
            if len(part) != 2:
                return False
            int(part, 16)
        return True
    except ValueError:
        return False


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Geberit AquaClean."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        super().__init__()
        self._discovered_devices: list[DiscoveredDevice] = []

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step - start device discovery."""
        return await self.async_step_bluetooth()

    async def async_step_bluetooth(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle Bluetooth device discovery step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            if "device" in user_input:
                # User selected a device from the discovered list
                selected_mac = user_input["device"]
                device_info = next(
                    (d for d in self._discovered_devices if d.address == selected_mac),
                    None
                )
                
                if device_info:
                    try:
                        # Validate the selected device
                        validation_data = {CONF_MAC: selected_mac}
                        info = await validate_input(self.hass, validation_data)
                        
                        # Check if already configured
                        await self.async_set_unique_id(selected_mac)
                        self._abort_if_unique_id_configured()
                        
                        return self.async_create_entry(
                            title=device_info.display_name,
                            data=validation_data
                        )
                    except CannotConnect:
                        errors["base"] = "cannot_connect"
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.exception("Unexpected exception")
                        errors["base"] = "unknown"
                else:
                    errors["device"] = "device_not_found"
            else:
                # Manual MAC entry fallback
                return await self.async_step_manual()
        
        # Perform device discovery
        if not errors:
            scanner = get_scanner()
            try:
                self._discovered_devices = await scanner.scan_for_devices(timeout=10.0)
            except Exception as e:
                _LOGGER.error("Error during device discovery: %s", e)
                errors["base"] = "discovery_failed"
        
        # Create device selection options
        device_options = {}
        for device in self._discovered_devices:
            device_options[device.address] = device.display_name
        
        if not device_options and not errors:
            # No devices found, offer manual entry option
            return await self.async_step_no_devices()
        
        # Add manual entry option
        device_options["manual"] = "Enter MAC address manually"
        
        data_schema = vol.Schema({
            vol.Required("device"): vol.In(device_options)
        })
        
        return self.async_show_form(
            step_id="bluetooth",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._discovered_devices))
            }
        )

    async def async_step_no_devices(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle case when no devices are discovered."""
        if user_input is not None:
            if user_input.get("action") == "manual":
                return await self.async_step_manual()
            elif user_input.get("action") == "rescan":
                return await self.async_step_bluetooth()
        
        return self.async_show_form(
            step_id="no_devices",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "manual": "Enter MAC address manually",
                    "rescan": "Scan again"
                })
            })
        )

    async def async_step_manual(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle manual MAC address entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_MAC])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidMac:
                errors[CONF_MAC] = "invalid_mac"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="manual", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidMac(HomeAssistantError):
    """Error to indicate invalid MAC address."""
