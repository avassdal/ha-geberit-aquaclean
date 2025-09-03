"""Config flow for Geberit AquaClean integration."""
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import DOMAIN
from .geberit_client import GeberitAquaCleanClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC_ADDRESS): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
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

    def __init__(self) -> None:
        """Initialize config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: bluetooth.BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name or discovery_info.address}
        
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm setup of a discovered bluetooth device."""
        if user_input is not None or not self._discovery_info:
            try:
                # Validate the discovered device
                mac_address = self._discovery_info.address
                data = {CONF_MAC_ADDRESS: mac_address}
                info = await validate_input(self.hass, data)
                
                return self.async_create_entry(title=info["title"], data=data)
                
            except CannotConnect:
                return self.async_abort(reason="cannot_connect")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during bluetooth setup")
                return self.async_abort(reason="unknown")

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or self._discovery_info.address
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        config_entry = self._get_reconfigure_entry()
        
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                
                await self.async_set_unique_id(user_input[CONF_MAC_ADDRESS])
                self._abort_if_unique_id_mismatch()
                
                return self.async_update_reload_and_abort(
                    config_entry,
                    data_updates=user_input,
                )
                
            except CannotConnect:
                return self.async_abort(reason="cannot_connect")
            except InvalidMac:
                return self.async_abort(reason="invalid_mac")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reconfigure")
                return self.async_abort(reason="unknown")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_MAC_ADDRESS, default=config_entry.data.get(CONF_MAC_ADDRESS)): str,
            }),
            description_placeholders={"name": config_entry.title},
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidMac(HomeAssistantError):
    """Error to indicate invalid MAC address."""
