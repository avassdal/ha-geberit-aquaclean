"""Config flow for Geberit AquaClean integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components import bluetooth

from .const import DOMAIN
from .geberit_client import GeberitAquaCleanClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC_ADDRESS): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, any]) -> dict[str, any]:
    """Validate the user input allows us to connect."""
    mac_address = data[CONF_MAC_ADDRESS]

    # Validate MAC address format
    if not _is_valid_mac(mac_address):
        raise InvalidMac

    # Try to find the device using HA Bluetooth
    ble_device = bluetooth.async_ble_device_from_address(
        hass, mac_address.upper(), connectable=True
    )
    if not ble_device:
        raise CannotConnect

    # Try to connect to validate the device
    scanner = bluetooth.async_get_scanner(hass)
    client = GeberitAquaCleanClient(mac_address, hass, scanner)
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

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_MAC_ADDRESS])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidMac:
                errors[CONF_MAC_ADDRESS] = "invalid_mac"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidMac(HomeAssistantError):
    """Error to indicate invalid MAC address."""
