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

from datetime import datetime
from typing import Any

import xmltodict


class BaseHikvisionEntity(object):
    XML_ROOT_ELEMENT: str = None
    XML_PARSE_ATTRS = False

    def __init__(self) -> None:
        self._xmldict = {}

    def _from_field(self, field: str, _default: Any = None) -> Any:
        return self._xmldict.get(field)

    def _to_field(self, field: str, value: Any):
        self._xmldict[field] = value

    @classmethod
    def from_xml_str(cls, xml_str: str):
        parsed = xmltodict.parse(xml_str, xml_attribs=cls.XML_PARSE_ATTRS)
        if cls.XML_ROOT_ELEMENT:
            parsed = parsed.get(cls.XML_ROOT_ELEMENT)
        return cls.from_xml_dict(parsed)

    @classmethod
    def from_xml_dict(cls, xml_dict: dict):
        result = cls()
        result._xmldict = xml_dict
        return result


class EventNotificationAlert(BaseHikvisionEntity):
    XML_ROOT_ELEMENT = 'EventNotificationAlert'

    FIELD_EVENT_TYPE = 'eventType'
    FIELD_EVENT_DESCRIPTION = 'eventDescription'
    FIELD_CHANNEL_NAME = 'channelName'
    FIELD_CHANNEL_ID = 'channelID'
    FIELD_EVENT_STATE = 'eventState'
    FIELD_EVENT_TIME = 'dateTime'

    @property
    def type(self) -> str:
        return self._from_field(self.FIELD_EVENT_TYPE)

    @type.setter
    def type(self, value: str):
        self._to_field(self.FIELD_EVENT_TYPE, value)

    @property
    def description(self) -> str:
        return self._from_field(self.FIELD_EVENT_DESCRIPTION)

    @description.setter
    def description(self, value: str):
        self._to_field(self.FIELD_EVENT_DESCRIPTION, value)

    @property
    def channel_name(self) -> str:
        return self._from_field(self.FIELD_CHANNEL_NAME)

    @channel_name.setter
    def channel_name(self, value: str):
        self._to_field(self.FIELD_CHANNEL_NAME, value)

    @property
    def channel_id(self) -> str:
        return self._from_field(self.FIELD_CHANNEL_ID)

    @channel_id.setter
    def channel_id(self, value: str):
        self._to_field(self.FIELD_CHANNEL_ID, value)

    @property
    def state(self) -> str:
        return self._from_field(self.FIELD_EVENT_STATE)

    @state.setter
    def state(self, value: str):
        self._to_field(self.FIELD_EVENT_STATE, value)

    @property
    def timestamp(self) -> datetime:
        str_val = self._from_field(self.FIELD_EVENT_TIME)
        if str_val is None:
            return None
        return datetime.fromisoformat(self._from_field(self.FIELD_EVENT_TIME))

    @timestamp.setter
    def timestamp(self, value: datetime):
        self._to_field(self.FIELD_EVENT_TIME, datetime.isoformat(value))
