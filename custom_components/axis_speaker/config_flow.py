"""Config flow for the Axis Speaker integration."""

from __future__ import annotations

from typing import Any

import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.httpx_client import get_async_client

from .api import AxisSpeakerAuthError, AxisSpeakerClient, AxisSpeakerError
from .const import CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default="root"): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class AxisSpeakerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a single Axis speaker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            client = AxisSpeakerClient(
                get_async_client(self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]),
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            try:
                device_info = await client.async_get_device_info()
            except AxisSpeakerAuthError:
                errors["base"] = "invalid_auth"
            except (AxisSpeakerError, httpx.HTTPError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=device_info.prod_full_name,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
