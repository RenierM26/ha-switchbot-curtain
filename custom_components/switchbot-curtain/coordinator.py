"""Provides the switchbot DataUpdateCoordinator."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

# pylint: disable=import-error
import switchbot

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

CONNECT_LOCK = asyncio.Lock()
_LOGGER = logging.getLogger(__name__)


class SwitchbotDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching switchbot data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        update_interval: int,
        api: switchbot,
        retry_count: int,
        scan_timeout: int,
    ) -> None:
        """Initialize global switchbot data updater."""
        self.switchbot_api = api
        self.switchbot_devices = None
        self.retry_count = retry_count
        self.scan_timeout = scan_timeout
        self.update_interval = timedelta(seconds=update_interval)

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=self.update_interval
        )

    def _update_data(self) -> dict | None:
        """Fetch data from Switchbot via Switchbots Class."""
        _devices_data = None

        _devices_data = self.switchbot_api.GetSwitchbotDevices().discover(
            retry=self.retry_count, scan_timeout=self.scan_timeout
        )

        if _devices_data:
            self.switchbot_devices = _devices_data

        return self.switchbot_devices

    async def _async_update_data(self):
        """Fetch data from switchbot."""

        async with CONNECT_LOCK:
            _get_switchbot_api = await self.hass.async_add_executor_job(
                self._update_data
            )

        if not _get_switchbot_api:
            raise UpdateFailed("Unable to fetch switchbot services data")

        return _get_switchbot_api
