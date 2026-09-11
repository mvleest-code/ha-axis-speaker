"""Thin async client for the AXIS VAPIX endpoints this integration uses.

Two VAPIX styles are mixed here on purpose, because that's how the device
itself is organised: the classic ``param.cgi`` key/value API (brand info,
firmware, configured media clips) and the newer JSON-RPC style CGIs
(``mqtt/client.cgi``). Both were verified by hand against a real
AXIS C1410 Network Mini Speaker (AXIS OS 11.11.192) before writing this.

VAPIX exposes a "Call service API" (SIP) capability flag on this device
(``Properties.API.SIP.SIP=yes``), but no working dial/answer/hangup endpoint
could be found under either the classic ``axis-cgi/`` tree or the newer
``config/rest/`` tree during testing. SIP call control is therefore not
implemented here - see the README.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

import httpx

PARAM_LINE_RE = re.compile(r"^root\.(?P<key>[^=]+)=(?P<value>.*)$")
MEDIA_CLIP_RE = re.compile(r"^MediaClip\.M(?P<id>\d+)\.(?P<field>Name|Location|Type)$")


class AxisSpeakerError(Exception):
    """Raised when the speaker returns an unexpected response."""


class AxisSpeakerAuthError(AxisSpeakerError):
    """Raised when authentication with the speaker fails."""


@dataclass
class AxisSpeakerDeviceInfo:
    """Static-ish info about the device, read from param.cgi."""

    prod_full_name: str
    prod_short_name: str
    prod_number: str
    firmware_version: str
    mac_address: str | None = None


@dataclass
class AxisMediaClip:
    """A single audio clip configured on the device."""

    clip_id: int
    name: str


@dataclass
class AxisSpeakerData:
    """Everything the coordinator polls in one go."""

    device_info: AxisSpeakerDeviceInfo
    clips: dict[int, AxisMediaClip] = field(default_factory=dict)
    mqtt_status: dict | None = None


def _parse_params(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for line in text.splitlines():
        match = PARAM_LINE_RE.match(line.strip())
        if match:
            params[match.group("key")] = match.group("value")
    return params


class AxisSpeakerClient:
    """Talks to a single AXIS speaker over VAPIX."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        host: str,
        username: str,
        password: str,
    ) -> None:
        self._client = client
        self._base_url = f"https://{host}"
        self._auth = httpx.DigestAuth(username, password)

    async def _get_params(self, group: str) -> dict[str, str]:
        response = await self._client.get(
            f"{self._base_url}/axis-cgi/param.cgi",
            params={"action": "list", "group": group},
            auth=self._auth,
        )
        self._raise_for_status(response)
        return _parse_params(response.text)

    async def _post_json(self, path: str, payload: dict) -> dict:
        response = await self._client.post(
            f"{self._base_url}/{path}",
            json=payload,
            auth=self._auth,
        )
        self._raise_for_status(response)
        return response.json()

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise AxisSpeakerAuthError(
                f"Authentication failed ({response.status_code})"
            )
        if response.status_code >= 400:
            raise AxisSpeakerError(
                f"Unexpected response {response.status_code}: {response.text[:200]}"
            )

    async def async_get_device_info(self) -> AxisSpeakerDeviceInfo:
        brand = await self._get_params("Brand")
        firmware = await self._get_params("Properties.Firmware")
        try:
            network = await self._get_params("Network.eth0")
        except AxisSpeakerError:
            network = {}
        try:
            return AxisSpeakerDeviceInfo(
                prod_full_name=brand["Brand.ProdFullName"],
                prod_short_name=brand["Brand.ProdShortName"],
                prod_number=brand["Brand.ProdNbr"],
                firmware_version=firmware["Properties.Firmware.Version"],
                mac_address=network.get("Network.eth0.MACAddress"),
            )
        except KeyError as err:
            raise AxisSpeakerError(f"Unexpected Brand/Firmware response: {err}") from err

    async def async_get_media_clips(self) -> dict[int, AxisMediaClip]:
        raw = await self._get_params("MediaClip")
        clips: dict[int, dict[str, str]] = {}
        for key, value in raw.items():
            match = MEDIA_CLIP_RE.match(key)
            if not match:
                continue
            clip_id = int(match.group("id"))
            clips.setdefault(clip_id, {})[match.group("field")] = value

        return {
            clip_id: AxisMediaClip(clip_id=clip_id, name=fields.get("Name", f"Clip {clip_id}"))
            for clip_id, fields in clips.items()
            if fields.get("Type") == "audio"
        }

    async def async_play_clip(self, clip_id: int, volume: int = 100, repeat: int = 0) -> None:
        response = await self._client.get(
            f"{self._base_url}/axis-cgi/playclip.cgi",
            params={"clip": clip_id, "volume": volume, "repeat": repeat},
            auth=self._auth,
        )
        self._raise_for_status(response)

    async def async_stop_clip(self) -> None:
        response = await self._client.get(
            f"{self._base_url}/axis-cgi/stopclip.cgi",
            auth=self._auth,
        )
        self._raise_for_status(response)

    async def async_get_mqtt_status(self) -> dict:
        return await self._post_json(
            "axis-cgi/mqtt/client.cgi",
            {"apiVersion": "1.6", "method": "getClientStatus"},
        )

    async def async_configure_mqtt(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
    ) -> None:
        """Point the speaker's own MQTT client at a broker and connect.

        Payload shape mirrors the ``config`` object the device itself
        returns from ``getClientStatus`` (confirmed live). The credential
        placement follows Axis's published MQTT Client API pattern but was
        not exercised against a real broker while building this - test it
        deliberately (e.g. with a throwaway broker) before relying on it.
        """
        config: dict = {
            "server": {
                "protocol": "ssl" if use_tls else "tcp",
                "host": host,
                "port": port,
            },
            "autoReconnect": True,
            "cleanSession": False,
        }
        if username:
            config["username"] = username
        if password:
            config["password"] = password

        await self._post_json(
            "axis-cgi/mqtt/client.cgi",
            {"apiVersion": "1.6", "method": "configureClient", "params": {"config": config}},
        )
        await self._post_json(
            "axis-cgi/mqtt/client.cgi",
            {"apiVersion": "1.6", "method": "activateClient"},
        )

    async def async_get_data(self) -> AxisSpeakerData:
        device_info = await self.async_get_device_info()
        clips = await self.async_get_media_clips()
        try:
            mqtt_status = await self.async_get_mqtt_status()
        except AxisSpeakerError:
            mqtt_status = None
        return AxisSpeakerData(device_info=device_info, clips=clips, mqtt_status=mqtt_status)
