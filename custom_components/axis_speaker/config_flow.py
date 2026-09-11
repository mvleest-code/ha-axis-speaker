"""Config flow for the Axis Speaker integration.

Three ways to add a device:
- Manual: type in a host.
- Manual + scan: the user step also runs a short active mDNS scan for Axis
  devices and offers them as a picklist (still lets you type a custom host).
- Zeroconf: Home Assistant's own passive mDNS discovery notices a new Axis
  device on the network and offers to set it up.
"""

from __future__ import annotations

from typing import Any

import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.httpx_client import get_async_client

from .api import AxisSpeakerAuthError, AxisSpeakerClient, AxisSpeakerDeviceInfo, AxisSpeakerError
from .const import CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, DOMAIN
from .discovery import async_discover_axis_hosts

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME, default="root"): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class AxisSpeakerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a single Axis speaker."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    async def _async_validate_and_create(
        self, host: str, username: str, password: str, verify_ssl: bool
    ) -> tuple[AxisSpeakerDeviceInfo | None, str | None]:
        """Return (device_info, error_code). Exactly one of them is set."""
        client = AxisSpeakerClient(
            get_async_client(self.hass, verify_ssl=verify_ssl), host, username, password
        )
        try:
            device_info = await client.async_get_device_info()
        except AxisSpeakerAuthError:
            return None, "invalid_auth"
        except (AxisSpeakerError, httpx.HTTPError):
            return None, "cannot_connect"
        return device_info, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            device_info, error = await self._async_validate_and_create(
                host,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_VERIFY_SSL],
            )
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(title=device_info.prod_full_name, data=user_input)

        discovered = await async_discover_axis_hosts(self.hass)
        if discovered:
            host_field = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=host, label=f"{name} ({host})")
                        for host, name in discovered.items()
                    ],
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        else:
            host_field = str

        schema = vol.Schema({vol.Required(CONF_HOST): host_field}).extend(CREDENTIALS_SCHEMA.schema)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle discovery via mDNS (`_axis-video`/`_axis-audiosite`)."""
        mac = discovery_info.properties.get("macaddress")
        host = discovery_info.host

        if mac:
            await self.async_set_unique_id(format_mac(mac))
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        else:
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

        self._discovered_host = host
        self._discovered_name = discovery_info.name.split(".")[0]
        self.context["title_placeholders"] = {"name": self._discovered_name}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._discovered_host is not None

        if user_input is not None:
            device_info, error = await self._async_validate_and_create(
                self._discovered_host,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_VERIFY_SSL],
            )
            if error:
                errors["base"] = error
            else:
                data = {CONF_HOST: self._discovered_host, **user_input}
                return self.async_create_entry(title=device_info.prod_full_name, data=data)

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=CREDENTIALS_SCHEMA,
            errors=errors,
            description_placeholders={
                "name": self._discovered_name or "",
                "host": self._discovered_host,
            },
        )
