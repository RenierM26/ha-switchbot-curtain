"""Support for SwitchBot curtains."""
from __future__ import annotations

import logging
from typing import Any

# pylint: disable=import-error
import switchbot

from homeassistant.components.cover import (
    ATTR_POSITION,
    DEVICE_CLASS_CURTAIN,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)
from homeassistant.const import CONF_MAC, CONF_NAME, CONF_PASSWORD, CONF_SENSOR_TYPE
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CURTAIN,
    CONF_RETRY_COUNT,
    CONF_RETRY_TIMEOUT,
    DATA_COORDINATOR,
    DOMAIN,
    MANUFACTURER,
)

# Initialize the logger
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Switchbot curtain based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    curtain_device = []

    switchbot.DEFAULT_RETRY_COUNT = entry.options[CONF_RETRY_COUNT]
    switchbot.DEFAULT_RETRY_TIMEOUT = entry.options[CONF_RETRY_TIMEOUT]

    if entry.data[CONF_SENSOR_TYPE] == ATTR_CURTAIN:
        for idx in coordinator.data:
            if idx == entry.unique_id.lower():

                curtain_device.append(
                    SwitchBotCurtain(
                        coordinator,
                        idx,
                        entry.data[CONF_MAC],
                        entry.data[CONF_NAME],
                        entry.data.get(CONF_PASSWORD, None),
                    )
                )

    async_add_entities(curtain_device)


class SwitchBotCurtain(CoordinatorEntity, CoverEntity, RestoreEntity):
    """Representation of a Switchbot."""

    def __init__(self, coordinator, idx, mac, name, password=None) -> None:
        """Initialize the Switchbot."""
        super().__init__(coordinator)
        self._last_run_success = None
        self._idx = idx
        self.switchbot_name = name
        self._mac = mac
        self._model = self.coordinator.data[self._idx]["modelName"]
        self._device = switchbot.SwitchbotCurtain(mac=mac, password=password)

    @property
    def assumed_state(self) -> bool:
        """Return true if unable to access real state of entity."""
        return True

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self._mac.replace(":", "")

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self.switchbot_name

    @property
    def device_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "last_run_success": self._last_run_success,
        }

    @property
    def device_class(self) -> str:
        """Return the class of this device."""
        return DEVICE_CLASS_CURTAIN

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.coordinator.data[self._idx]["data"]["position"] <= 10

    async def async_open_cover(self, **kwargs) -> None:
        """Open the curtain with using this device."""

        _LOGGER.info("Switchbot to open curtain %s", self._mac)

        update_ok = await self.hass.async_add_executor_job(self._device.open)

        if update_ok:
            self._last_run_success = True
        else:
            self._last_run_success = False

    async def async_close_cover(self, **kwargs) -> None:
        """Close the curtain with using this device."""

        _LOGGER.info("Switchbot to close the curtain %s", self._mac)

        update_ok = await self.hass.async_add_executor_job(self._device.close)

        if update_ok:
            self._last_run_success = True
        else:
            self._last_run_success = False

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the moving of this device."""

        _LOGGER.info("Switchbot to stop %s", self._mac)

        update_ok = await self.hass.async_add_executor_job(self._device.stop)

        if update_ok:
            self._last_run_success = True
        else:
            self._last_run_success = False

    async def async_set_cover_position(self, **kwargs):
        """Move the cover shutter to a specific position."""
        position = kwargs.get(ATTR_POSITION)

        _LOGGER.info("Switchbot to move at %d %s", position, self._mac)

        update_ok = await self.hass.async_add_executor_job(
            self._device.set_position, position
        )

        if update_ok:
            self._last_run_success = True
        else:
            self._last_run_success = False

    @property
    def current_cover_position(self):
        """Return the current position of cover shutter."""
        return self.coordinator.data[self._idx]["data"]["position"]

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self._mac.replace(":", ""))},
            "name": self.switchbot_name,
            "model": self._model,
            "manufacturer": MANUFACTURER,
        }
