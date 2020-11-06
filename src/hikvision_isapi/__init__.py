#    hass-hikvision-connector
#    Copyright (C) 2020 Dmitry Berezovsky
#    The MIT License (MIT)
#
#    Permission is hereby granted, free of charge, to any person obtaining
#    a copy of this software and associated documentation files
#    (the "Software"), to deal in the Software without restriction,
#    including without limitation the rights to use, copy, modify, merge,
#    publish, distribute, sublicense, and/or sell copies of the Software,
#    and to permit persons to whom the Software is furnished to do so,
#    subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be
#    included in all copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#    SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""HomeAssistant-Hikvision Connector based on the native ISAPI client implementation"""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Config

from . import const
from .isapi.client import ISAPIClient
from .isapi.model import EventNotificationAlert

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured Hikvision integration."""
    # TODO: Handle yaml here
    hass.data.setdefault(const.DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up hikvision from a config entry."""
    _LOGGER.debug("Loading config entry {} (id: {})".format(config_entry.title, config_entry.entry_id))

    # Subscribe for changes to config entry
    undo_config_update_listener = config_entry.add_update_listener(update_config_listener)

    cfg = config_entry.data
    api_client = ISAPIClient(
        cfg.get(const.CONF_BASE_URL),
        cfg.get(const.CONF_USER),
        cfg.get(const.CONF_PASSWORD),
        ignore_ssl_errors=cfg.get(const.CONF_IGNORE_SSL_ERRORS),
    )

    # Bootstrap data structure for config entry
    hass.data[const.DOMAIN][config_entry.entry_id] = {
        const.DATA_API_CLIENT: api_client,
        const.UNDO_UPDATE_CONF_UPDATE_LISTENER: undo_config_update_listener,
        const.DATA_ALERTS_BG_TASKS: [],
        const.DATA_ALERTS_QUEUE: None,
        const.DATA_ENTITIES: [],
    }

    for component in const.PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(config_entry, component))

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Destroy resources related to config entry"""
    _LOGGER.debug("Unloading config entry {} (id: {})".format(config_entry.title, config_entry.entry_id))
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(config_entry, component) for component in const.PLATFORMS]
        )
    )

    # Shutting down background workers
    entry_data = hass.data[const.DOMAIN][config_entry.entry_id]
    for task in entry_data[const.DATA_ALERTS_BG_TASKS]:
        task.cancel()
    # Disposing client
    try:
        await entry_data[const.DATA_API_CLIENT].close()
    except Exception:
        _LOGGER.warning("Unable to close hikvision api client")
    finally:
        entry_data[const.DATA_API_CLIENT] = None

    # Remove entities from hass
    await asyncio.gather(*[entity.async_remove() for entity in entry_data[const.DATA_ENTITIES]])
    entry_data[const.DATA_ENTITIES] = []

    entry_data[const.UNDO_UPDATE_CONF_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[const.DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_config_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Will be invoked after once entry updated."""
    _LOGGER.debug(
        "Config entry {}(id: {}) updated. Platform reload will be triggered".format(
            config_entry.title, config_entry.entry_id
        )
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
