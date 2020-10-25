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
import datetime
import enum
import logging
from asyncio import Queue, CancelledError
from typing import NamedTuple, Dict, List, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import DOMAIN as COMP_BINARY_SENSOR
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.discovery import async_load_platform

from . import const
from .isapi.client import ISAPIClient
from .isapi.model import EventNotificationAlert

_LOGGER = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = (COMP_BINARY_SENSOR,)


class AlertType(enum.Enum):
    LineCrossing = 'linedetection'
    Intrusion = 'fielddetection'
    VideoLoss = 'videoloss'


CHANNEL_SCHEMA = vol.Schema({
    vol.Required(const.CONF_CHANNEL_ID): cv.string,
    vol.Optional(const.CONF_CHANNEL_ENTITY_ID): cv.string,
    vol.Optional(const.CONF_CHANNEL_NAME): cv.string,
})

ALERT_SCHEMA = vol.Schema({
    vol.Required(const.CONF_ALERT_TYPE): cv.enum(AlertType),
    vol.Optional(const.CONF_ALERT_CHANNEL): cv.positive_int,
    vol.Optional(const.CONF_ALERT_NAME): cv.string,
    vol.Optional(const.CONF_ALERT_RECOVERY_PERIOD): cv.time_period,
})

DEVICE_SCHEMA = vol.Schema({
    vol.Required(const.CONF_BASE_URL): cv.string,
    vol.Optional(const.CONF_USER): cv.string,
    vol.Optional(const.CONF_PASSWORD): cv.string,
    vol.Optional(const.CONF_DEFAULT_RECOVERY_PERIOD, default='00:01:00'): cv.time_period,
    vol.Optional(const.CONF_ALERTS): vol.All(
        cv.ensure_list, [ALERT_SCHEMA]
    ),
    vol.Optional(const.CONF_CHANNELS): vol.All(
        cv.ensure_list, [CHANNEL_SCHEMA]
    ),
})

CONFIG_SCHEMA = vol.Schema(
    {const.DOMAIN: cv.schema_with_slug_keys(DEVICE_SCHEMA)},
    extra=vol.ALLOW_EXTRA,
)


class AlertDef(NamedTuple):
    device_name: str
    type: AlertType
    name: str
    channel: str
    recovery_period: datetime.timedelta

    @classmethod
    def from_config(cls, device_name: str, config: Dict):
        return AlertDef(
            device_name=device_name,
            name=config.get(const.CONF_ALERT_NAME),
            type=config.get(const.CONF_ALERT_TYPE),
            channel=str(config.get(const.CONF_ALERT_CHANNEL)),
            recovery_period=config.get(const.CONF_ALERT_RECOVERY_PERIOD),
        )


class PlatformInitParams(NamedTuple):
    platform: str
    discovery_data: Dict


async def async_setup(hass: HomeAssistant, config):
    """Set up the Cast component."""
    conf = config.get(const.DOMAIN)

    hass.data[const.DOMAIN] = {}
    data = hass.data[const.DOMAIN]

    for device_name, cfg in conf.items():
        # Create API client for each device
        api_client = ISAPIClient(cfg.get(const.CONF_BASE_URL), cfg.get(const.CONF_USER),
                                 cfg.get(const.CONF_PASSWORD))
        event_stream = Queue()
        data[device_name] = {
            const.DATA_API_CLIENT: api_client,
            const.DATA_EVENT_STREAM: event_stream,
            const.DATA_HAS_SUBSCRIBERS: False,
            const.DATA_ALERT_CONFIGS: [],
            const.DATA_BG_TASKS: []
        }
        channels_map = build_channels_map(cfg.get(const.CONF_CHANNELS, []))
        alert_subscriber_detected = False
        # Create and initialize alert entities for each device
        for alert_def_dict in cfg.get(const.CONF_ALERTS, []):
            if alert_def_dict.get(const.CONF_ALERT_RECOVERY_PERIOD) is None:
                alert_def_dict[const.CONF_ALERT_RECOVERY_PERIOD] = cfg.get(const.CONF_DEFAULT_RECOVERY_PERIOD)
            alert_def = AlertDef.from_config(device_name, alert_def_dict)
            alert_init_params = build_platform_params_for_alert(alert_def, cfg, device_name,
                                                                channels_map,
                                                                len(data[device_name][const.DATA_ALERT_CONFIGS]))
            if alert_init_params is not None:
                _LOGGER.info('Discovered hikvision alert entity ' + alert_init_params.discovery_data.get(
                    const.DISCOVERY_SENSOR_ID))
                alert_subscriber_detected = True
                data[device_name][const.DATA_ALERT_CONFIGS].append(alert_def)

                await async_load_platform(hass, alert_init_params.platform, const.DOMAIN,
                                          alert_init_params.discovery_data, cfg)

        if alert_subscriber_detected:
            data[device_name][const.DATA_HAS_SUBSCRIBERS] = alert_subscriber_detected

    async def start_hikvision_isapi(event: Event):
        for device_name, device_data in data.items():
            if device_data.get(const.DATA_HAS_SUBSCRIBERS):
                _LOGGER.info("at least one alert subscriber detected. initializing ISAPI event stream")
                device_data[const.DATA_BG_TASKS].append(
                    hass.async_add_job(
                        api_client.listen_hikvision_event_stream, event_stream
                    )
                )
                device_data[const.DATA_BG_TASKS].append(
                    hass.async_add_job(
                        process_hikvision_alerts, hass, event_stream, device_name, device_data[const.DATA_ALERT_CONFIGS]
                    )
                )

    async def stop_hikvision_isapi(event: Event):
        for device_name, device_data in data.items():
            for task in device_data[const.DATA_BG_TASKS]:
                task.cancel()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_hikvision_isapi)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hikvision_isapi)
    return True


async def process_hikvision_alerts(hass: HomeAssistant, event_stream: Queue, device_name: str,
                                   alerts_cfg: List[AlertDef]):
    try:
        while True:
            event: EventNotificationAlert = await event_stream.get()

            # if event_type == 'videoloss' and event_state == 'inactive':
            #     continue
            # Finding suitable alert
            for alert in alerts_cfg:
                alert_channel = alert.channel
                if alert_channel is not None:
                    alert_channel = str(alert_channel)
                if alert.type.value == event.type and alert_channel == event.channel_id:
                    _LOGGER.debug(
                        'CLASSIFIED ALERT: {} \tState: {}, \tChannel: {}/{}, \t Time: {}'.format(event.type,
                                                                                                 event.state,
                                                                                                 event.channel_id,
                                                                                                 event.channel_name,
                                                                                                 str(event.timestamp)))
                    hass.bus.async_fire(const.EVENT_ALERT_NAME, {
                        const.EVENT_ALERT_DATA_CHANNEL: event.channel_id,
                        const.EVENT_ALERT_DATA_TYPE: event.type,
                        const.EVENT_ALERT_DATA_DEVICE: device_name,
                        const.EVENT_ALERT_DATA_TIMESTAMP: event.timestamp.isoformat(),
                    })

            _LOGGER.debug(
                'ALERT: {} \tState: {}, \tChannel: {}/{}, \t Time: {}'.format(event.type,
                                                                              event.state,
                                                                              event.channel_id,
                                                                              event.channel_name,
                                                                              str(event.timestamp)))
    except CancelledError:
        _LOGGER.info('Shutting down hikvision alerts processing for {}'.format(device_name))


def build_channels_map(channels_conf: List) -> Dict:
    result = {}
    for x in channels_conf:
        key = x.get(const.CONF_CHANNEL_ID)
        if key.lower().strip() == 'none':
            key = None
        result[key] = x
    return result


def build_platform_params_for_alert(alert_def: AlertDef, device_conf: Dict, device_name: str,
                                    channels_map: Dict, alert_cfg_id: int) -> Optional[PlatformInitParams]:
    channel_def: Dict = None
    if alert_def.channel is not None:
        channel_def = channels_map.get(alert_def.channel)
        if channel_def is None:
            alert_qualified_name = 'ch{} -> {}'.format(alert_def.channel, alert_def.type)
            _LOGGER.error('Unable to initialize alert [{}]. It refers to channel {} '
                          'which is not defined in channels section.'.format(alert_qualified_name, alert_def.channel))
            return None
    sensor_id = device_name + '_'
    sensor_name = alert_def.name
    if alert_def.name is None:
        sensor_name = device_name.capitalize() + ' '
    if channel_def is not None:
        sensor_id += channel_def.get(const.CONF_CHANNEL_ENTITY_ID,
                                     'ch' + channel_def.get(const.CONF_CHANNEL_ID)) + '_'
        if alert_def.name is None:
            sensor_name += channel_def.get(const.CONF_CHANNEL_NAME,
                                           'CH' + channel_def.get(const.CONF_CHANNEL_ID)) + ' '
    sensor_id += alert_def.type.name.lower()
    if alert_def.name is None:
        sensor_name += alert_def.type.name
    sensor_name = sensor_name.strip()
    discovery_data = {
        const.DISCOVERY_DEVICE_NAME: device_name,
        const.DISCOVERY_SENSOR_ID: sensor_id,
        const.DISCOVERY_SENSOR_NAME: sensor_name,
        const.DISCOVERY_ALERT_CFG_ID: alert_cfg_id,
        const.DISCOVERY_CHANNEL_CFG: channel_def,
    }
    return PlatformInitParams(COMP_BINARY_SENSOR, discovery_data)
