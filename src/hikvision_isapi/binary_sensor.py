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

import asyncio
import datetime
import logging
from asyncio import Queue
from typing import Dict, List, NamedTuple, Optional, Callable

from homeassistant.components.binary_sensor import BinarySensorEntity, DEVICE_CLASS_MOTION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval

from . import const, utils
from .isapi.client import ISAPIClient
from .isapi.model import EventNotificationAlert

_LOGGER = logging.getLogger(__name__)


class AlertDef(NamedTuple):
    related_device_id: str
    type: const.AlertType
    channel: Optional[str]
    recovery_period: datetime.timedelta


def name_to_id(name: str) -> str:
    return name.strip().replace(" ", "_").replace("-", "_").lower()


def should_listen_for_alerts(options: Dict) -> bool:
    for chanel_name, config in options.items():
        if chanel_name.startswith(const.OPT_ROOT_ALERTS) and config.get(const.OPT_ALERTS_ENABLE_TRACKING):
            return True
    return False


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the platform from config_entry."""
    # We should scan options for alert configs and then if at least 1 listener is enabled subscribe for the stream
    hik_client = hass.data[const.DOMAIN][config_entry.entry_id][const.DATA_API_CLIENT]
    entities = []
    if should_listen_for_alerts(config_entry.options):
        alerts_cfg = await start_isapi_alert_listeners(
            hass, hass.data[const.DOMAIN][config_entry.entry_id], config_entry
        )

        inputs_map = {}
        if config_entry.data.get(const.CONF_DEVICE_TYPE) == const.DEVICE_TYPE_NVR:
            inputs = await hik_client.get_available_inputs()
            for input in inputs:
                inputs_map[input.input_id] = (
                    name_to_id(const.SENSOR_ID_PREFIX + str(input.input_id).rjust(2, "0")),
                    input.input_name,
                )
        else:
            inputs_map[const.NON_NVR_CHANNEL_NUMBER] = (None, None)

        for alert in alerts_cfg:
            if alert.channel not in inputs_map:
                _LOGGER.warning("Ignoring sensors for channel {} (device {})".format(alert.channel, config_entry.title))
            input_prefix_id, input_prefix_name = inputs_map.get(alert.channel, (None, None))
            sensor_id = "_".join(filter(None, (name_to_id(config_entry.title), input_prefix_id, alert.type.value)))
            sensor_name = " ".join(
                filter(
                    None,
                    (
                        config_entry.title,
                        input_prefix_name,
                        const.ALERT_TYPES_MAP.get(alert.type.value, alert.type.value),
                    ),
                )
            )
            entities.append(HikvisionAlertBinarySensor(hass, sensor_id, sensor_name, alert))
    if len(entities) > 0:
        async_add_entities(entities)
    return True


async def start_isapi_alert_listeners(hass, data: Dict, config_entry: ConfigEntry) -> List[AlertDef]:
    _LOGGER.info("Initializing Hikvision ISAPI alert stream listener")
    api_client: ISAPIClient = data[const.DATA_API_CLIENT]
    event_stream = data[const.DATA_ALERTS_QUEUE] = Queue()
    options: Dict = config_entry.options

    # Build a list of AlertDefs
    alerts_cfg = []
    common_options = config_entry.options.get(const.OPT_ROOT_COMMON)
    if config_entry.data.get(const.CONF_DEVICE_TYPE) == const.DEVICE_TYPE_NVR:
        for chanel_name, channel_config in options.items():
            if chanel_name.startswith(const.OPT_ROOT_ALERTS) and len(chanel_name) > len(const.OPT_ROOT_ALERTS):
                channel_num = chanel_name.replace(const.OPT_ROOT_ALERTS, "", 1)
                if channel_config.get(const.OPT_ALERTS_ENABLE_TRACKING):
                    alerts_cfg += alertdef_from_channel_options(
                        config_entry.entry_id, channel_config, channel_num, common_options
                    )

    else:
        if options.get(const.OPT_ROOT_ALERTS).get(const.OPT_ALERTS_ENABLE_TRACKING):
            alerts_cfg += alertdef_from_channel_options(
                config_entry.entry_id, options.get(const.OPT_ROOT_ALERTS), const.NON_NVR_CHANNEL_NUMBER, common_options
            )

    data[const.DATA_ALERTS_BG_TASKS].append(
        hass.loop.create_task(api_client.listen_hikvision_event_stream(event_stream))
    )
    data[const.DATA_ALERTS_BG_TASKS].append(
        hass.loop.create_task(process_hikvision_alerts(hass, event_stream, config_entry.entry_id, alerts_cfg))
    )
    return alerts_cfg


def alertdef_from_channel_options(
    deivce_id: str, config: Dict, channel_num: Optional[str], common_options: Dict
) -> List[AlertDef]:
    res = []
    default_recovery_interval = utils.parse_timedelta_or_default(
        common_options.get(const.OPT_COMMON_DEFAULT_RECOVERY_PERIOD, ""), datetime.timedelta(minutes=1)
    )
    for alert_type in config.get(const.OPT_ALERTS_ALERT_TYPES):
        res.append(
            AlertDef(
                related_device_id=deivce_id,
                type=const.AlertType(alert_type),
                recovery_period=default_recovery_interval,
                channel=channel_num,
            )
        )
    return res


async def process_hikvision_alerts(
    hass: HomeAssistant, event_stream: Queue, config_entry_id: str, alerts_cfg: List[AlertDef]
):
    try:
        while True:
            event: EventNotificationAlert = await event_stream.get()

            if event.type == const.AlertType.VideoLoss.value and event.state == const.ALERT_STATE_INACTIVE:
                continue

            # Finding suitable alert
            for alert in alerts_cfg:
                alert_channel = alert.channel
                if alert_channel is not None:
                    alert_channel = str(alert_channel)
                if alert.type.value == event.type and alert_channel == event.channel_id:
                    _LOGGER.debug(
                        "CLASSIFIED ALERT: {} \tState: {}, \tChannel: {}/{}, \t Time: {}".format(
                            event.type, event.state, event.channel_id, event.channel_name, str(event.timestamp)
                        )
                    )
                    async_dispatcher_send(
                        hass,
                        const.SIGNAL_ALERT_NAME,
                        {
                            const.EVENT_ALERT_DATA_CHANNEL: event.channel_id,
                            const.EVENT_ALERT_DATA_TYPE: event.type,
                            const.EVENT_ALERT_DATA_DEVICE: config_entry_id,
                            const.EVENT_ALERT_DATA_TIMESTAMP: event.timestamp.isoformat(),
                        },
                    )
                    # hass.bus.async_fire(const.EVENT_ALERT_NAME, {
                    #     const.EVENT_ALERT_DATA_CHANNEL: event.channel_id,
                    #     const.EVENT_ALERT_DATA_TYPE: event.type,
                    #     const.EVENT_ALERT_DATA_DEVICE: config_entry_id,
                    #     const.EVENT_ALERT_DATA_TIMESTAMP: event.timestamp.isoformat(),
                    # })

            _LOGGER.debug(
                "ALERT: {} \tState: {}, \tChannel: {}/{}, \t Time: {}".format(
                    event.type, event.state, event.channel_id, event.channel_name, str(event.timestamp)
                )
            )
    except asyncio.CancelledError:
        _LOGGER.info("Shutting down hikvision alerts processing for config {}".format(config_entry_id))


class HikvisionAlertBinarySensor(BinarySensorEntity):
    def __init__(self, hass: HomeAssistant, sensor_id, sensor_name, alert_def: AlertDef):
        self._hass = hass
        self._unique_id = sensor_id
        self._name = sensor_name
        self._alert_def = alert_def
        self._triggered: Optional[bool] = None
        self._last_triggered: Optional[datetime.datetime] = None
        self._recovery_period = alert_def.recovery_period
        # hass.bus.async_listen(const.EVENT_ALERT_NAME, self._on_event_received)
        self._dispose_signal_dispatchers: List[Callable] = []
        self._dispose_signal_dispatchers.append(
            async_track_time_interval(hass, self._check_if_state_outdated, datetime.timedelta(seconds=20))
        )
        _LOGGER.debug("Configured Hikvision Alert sensor {}".format(self.name))

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        return DEVICE_CLASS_MOTION

    async def _handle_alert_signal(self, data: Dict):
        if not self._match_event(data):
            return
        self._triggered = True
        self._last_triggered = datetime.datetime.fromisoformat(data.get(const.EVENT_ALERT_DATA_TIMESTAMP))
        _LOGGER.debug("Signal received")
        self.async_schedule_update_ha_state(True)

    async def _on_event_received(self, event: Event):
        await self._handle_alert_signal(event.data)

    @property
    def is_on(self):
        return self._triggered

    @property
    def device_state_attributes(self):
        if self._triggered is None:
            return None
        attrs = {const.ATTR_LAST_TRIGGERED_TIME: self._last_triggered}
        return attrs

    @property
    def should_poll(self) -> bool:
        """Disable polling."""
        return False

    def _match_event(self, data: Dict) -> bool:
        return (
            data.get(const.EVENT_ALERT_DATA_DEVICE) == self._alert_def.related_device_id
            and data.get(const.EVENT_ALERT_DATA_TYPE) == self._alert_def.type.value
            and data.get(const.EVENT_ALERT_DATA_CHANNEL) == str(self._alert_def.channel)
        )

    async def _check_if_state_outdated(self, arg):
        if (
            self._last_triggered is not None
            and datetime.datetime.now(self._last_triggered.tzinfo) - self._last_triggered < self._recovery_period
        ):
            self._triggered = False
            self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self) -> None:
        # Added to hass so need to register to dispatch signals coming from alerts queue.
        self._dispose_signal_dispatchers.append(
            async_dispatcher_connect(self.hass, const.SIGNAL_ALERT_NAME, self._handle_alert_signal)
        )

    async def async_will_remove_from_hass(self):
        _LOGGER.debug("Unloading Hikvision Alert sensor {}".format(self.name))
        # Unregister signal dispatch listeners when being removed."""
        for disposer in self._dispose_signal_dispatchers:
            disposer()
        self._dispose_signal_dispatchers = []
