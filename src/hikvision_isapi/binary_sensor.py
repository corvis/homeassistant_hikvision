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

import datetime
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity, DEVICE_CLASS_MOTION
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.event import async_track_time_interval

from . import const, AlertDef

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    if discovery_info is None or const.DISCOVERY_DEVICE_NAME not in discovery_info:
        _LOGGER.warning("Skipped initialization of the binary sensor as manual initialization is not supported "
                        "(discovery context is required)")
        return

    alert_def = hass.data[const.DOMAIN][discovery_info[const.DISCOVERY_DEVICE_NAME]][const.DATA_ALERT_CONFIGS][
        discovery_info.get(const.DISCOVERY_ALERT_CFG_ID)]

    async_add_entities([HikvisionAlertBinarySensor(hass,
                                                   discovery_info.get(const.DISCOVERY_SENSOR_ID),
                                                   discovery_info.get(const.DISCOVERY_SENSOR_NAME),
                                                   alert_def
                                                   )
                        ])
    return True


class HikvisionAlertBinarySensor(BinarySensorEntity):

    def __init__(self, hass: HomeAssistant, sensor_id, sensor_name, alert_def: AlertDef):
        self._hass = hass
        self._unique_id = sensor_id
        self._name = sensor_name
        self._alert_def = alert_def
        self._triggered: bool = None
        self._last_triggered: datetime.datetime = None
        self._recovery_period = alert_def.recovery_period
        hass.bus.async_listen(const.EVENT_ALERT_NAME, self._on_event_received)
        async_track_time_interval(hass, self._check_if_state_outdated, datetime.timedelta(seconds=20))

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        return DEVICE_CLASS_MOTION

    async def _on_event_received(self, event: Event):
        if not self._match_event(event):
            return
        self._triggered = True
        self._last_triggered = event.time_fired
        _LOGGER.debug('ON EVENT ')
        self.async_schedule_update_ha_state(True)

    @property
    def is_on(self):
        return self._triggered

    @property
    def device_state_attributes(self):
        if self._triggered is None:
            return None
        attrs = {
            const.ATTR_LAST_TRIGGERED_TIME: self._last_triggered
        }
        return attrs

    @property
    def should_poll(self) -> bool:
        """Disable polling."""
        return False

    def _match_event(self, event: Event) -> bool:
        return event.data.get(const.EVENT_ALERT_DATA_DEVICE) == self._alert_def.device_name \
            and event.data.get(const.EVENT_ALERT_DATA_TYPE) == self._alert_def.type.value \
            and event.data.get(const.EVENT_ALERT_DATA_CHANNEL) == str(self._alert_def.channel)

    async def _check_if_state_outdated(self, arg):
        if self._last_triggered is not None \
                and datetime.datetime.now(self._last_triggered.tzinfo) - self._last_triggered < self._recovery_period:
            self._triggered = False
            self.async_schedule_update_ha_state(True)
