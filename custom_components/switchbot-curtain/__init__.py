"""Support for Switchbot devices."""
from asyncio import Lock

import switchbot  # pylint: disable=import-error

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    BTLE_LOCK,
    CONF_RETRY_COUNT,
    CONF_RETRY_TIMEOUT,
    CONF_SCAN_TIMEOUT,
    CONF_TIME_BETWEEN_UPDATE_COMMAND,
    DATA_COORDINATOR,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_TIMEOUT,
    DEFAULT_SCAN_TIMEOUT,
    DEFAULT_TIME_BETWEEN_UPDATE_COMMAND,
    DOMAIN,
)
from .coordinator import SwitchbotDataUpdateCoordinator

PLATFORMS = ["binary_sensor", "cover", "sensor", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Switchbot from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if not entry.options:
        options = {
            CONF_TIME_BETWEEN_UPDATE_COMMAND: DEFAULT_TIME_BETWEEN_UPDATE_COMMAND,
            CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
            CONF_RETRY_TIMEOUT: DEFAULT_RETRY_TIMEOUT,
            CONF_SCAN_TIMEOUT: DEFAULT_SCAN_TIMEOUT,
        }

        hass.config_entries.async_update_entry(entry, options=options)

    # Use same coordinator instance for all entities.
    # Uses BTLE advertisement data, all Switchbot devices in range is stored here.
    if DATA_COORDINATOR not in hass.data[DOMAIN]:

        # Check if asyncio.lock is stored in hass data.
        # BTLE has issues with multiple connections,
        # so we use a lock to ensure that only one API request is reaching it at a time:
        if BTLE_LOCK not in hass.data[DOMAIN]:
            hass.data[DOMAIN][BTLE_LOCK] = Lock()

        if CONF_RETRY_TIMEOUT not in hass.data[DOMAIN]:
            hass.data[DOMAIN][CONF_RETRY_TIMEOUT] = entry.options[CONF_RETRY_TIMEOUT]

        if CONF_SCAN_TIMEOUT not in hass.data[DOMAIN]:
            hass.data[DOMAIN][CONF_SCAN_TIMEOUT] = entry.options[CONF_SCAN_TIMEOUT]

        switchbot.DEFAULT_RETRY_TIMEOUT = hass.data[DOMAIN][CONF_RETRY_TIMEOUT]

        # Store api in coordinator.
        coordinator = SwitchbotDataUpdateCoordinator(
            hass,
            update_interval=entry.options[CONF_TIME_BETWEEN_UPDATE_COMMAND],
            api=switchbot,
            retry_count=entry.options[CONF_RETRY_COUNT],
            scan_timeout=hass.data[DOMAIN][CONF_SCAN_TIMEOUT],
            api_lock=hass.data[DOMAIN][BTLE_LOCK],
        )

        hass.data[DOMAIN][DATA_COORDINATOR] = coordinator

    else:
        coordinator = hass.data[DOMAIN][DATA_COORDINATOR]

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    hass.data[DOMAIN][entry.entry_id] = {DATA_COORDINATOR: coordinator}

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # If CONF_RETRY_TIMEOUT or CONF_SCAN_TIMEOUT changed, update entry
        if (
            entry.options[CONF_RETRY_TIMEOUT] != hass.data[DOMAIN][CONF_RETRY_TIMEOUT]
            or entry.options[CONF_SCAN_TIMEOUT] != hass.data[DOMAIN][CONF_SCAN_TIMEOUT]
        ):
            options = {**entry.options}
            options[CONF_RETRY_TIMEOUT] = hass.data[DOMAIN][CONF_RETRY_TIMEOUT]
            options[CONF_SCAN_TIMEOUT] = hass.data[DOMAIN][CONF_SCAN_TIMEOUT]
            hass.config_entries.async_update_entry(entry, options=options)

        hass.data[DOMAIN].pop(entry.entry_id)

        if len(hass.config_entries.async_entries(DOMAIN)) == 0:
            hass.data.pop(DOMAIN)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""

    # If CONF_RETRY_TIMEOUT or CONF_SCAN_TIMEOUT changed,
    # Update hass data and reload all entries.
    if (
        entry.options[CONF_RETRY_TIMEOUT] != hass.data[DOMAIN][CONF_RETRY_TIMEOUT]
        or entry.options[CONF_SCAN_TIMEOUT] != hass.data[DOMAIN][CONF_SCAN_TIMEOUT]
    ):
        hass.data[DOMAIN][CONF_RETRY_TIMEOUT] = entry.options[CONF_RETRY_TIMEOUT]
        hass.data[DOMAIN][CONF_SCAN_TIMEOUT] = entry.options[CONF_SCAN_TIMEOUT]
        hass.data[DOMAIN].pop(DATA_COORDINATOR)

        for item in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_reload(item.entry_id)

    else:
        await hass.config_entries.async_reload(entry.entry_id)
