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
from typing import Any, Union

import xmltodict


class BaseHikvisionEntity(object):
    XML_ROOT_ELEMENT: str = None
    XML_ROOT_LIST_ELEMENT: str = None
    XML_PARSE_ATTRS = False
    TO_STRING_FIELDS = tuple()

    def __init__(self) -> None:
        self._xmldict = {}

    def _from_field(self, field: str, _default: Any = None) -> Any:
        return self._xmldict.get(field)

    def _to_field(self, field: str, value: Any):
        self._xmldict[field] = value

    @classmethod
    def from_xml_str(cls, xml_str: Union[str, bytes], resolve_root_array=True):
        parsed = xmltodict.parse(xml_str, xml_attribs=cls.XML_PARSE_ATTRS)
        if cls.XML_ROOT_LIST_ELEMENT and cls.XML_ROOT_LIST_ELEMENT in parsed:
            parsed = parsed.get(cls.XML_ROOT_LIST_ELEMENT)
        if cls.XML_ROOT_ELEMENT:
            parsed = parsed.get(cls.XML_ROOT_ELEMENT)
        if isinstance(parsed, list):
            return [cls.from_xml_dict(x) for x in parsed]
        else:
            return cls.from_xml_dict(parsed)

    @classmethod
    def from_xml_dict(cls, xml_dict: dict):
        result = cls()
        result._xmldict = xml_dict
        return result

    def __repr__(self):
        if len(self.TO_STRING_FIELDS) == 0:
            props = 'obj=' + hex(id(self))
        else:
            props = ', '.join(['{}={}'.format(f, self._from_field(f)) for f in self.TO_STRING_FIELDS])
        return '{}({})'.format(self.__class__.__name__, props)


class DeviceInfo(BaseHikvisionEntity):
    XML_ROOT_ELEMENT = 'DeviceInfo'

    DEVICE_TYPE_NVR = 'NVR'

    FIELD_DEVICE_NAME = 'deviceName'
    FIELD_DEVICE_ID = 'deviceID'
    FIELD_MODEL = 'model'
    FIELD_SERIAL_NUMBER = 'serialNumber'
    FIELD_FIRMWARE_VERSION = 'firmwareVersion'
    FIELD_FIRMWARE_RELEASE_DATE = 'firmwareReleaseDate'
    FIELD_DEVICE_TYPE = 'deviceType'

    @property
    def device_name(self) -> str:
        return self._from_field(self.FIELD_DEVICE_NAME)

    @device_name.setter
    def device_name(self, value: str):
        self._to_field(self.FIELD_DEVICE_NAME, value)

    @property
    def device_id(self) -> str:
        return self._from_field(self.FIELD_DEVICE_ID)

    @device_id.setter
    def device_id(self, value: str):
        self._to_field(self.FIELD_DEVICE_ID, value)

    @property
    def model(self) -> str:
        return self._from_field(self.FIELD_MODEL)

    @model.setter
    def model(self, value: str):
        self._to_field(self.FIELD_MODEL, value)

    @property
    def serial_number(self) -> str:
        return self._from_field(self.FIELD_SERIAL_NUMBER)

    @serial_number.setter
    def serial_number(self, value: str):
        self._to_field(self.FIELD_SERIAL_NUMBER, value)

    @property
    def device_type(self) -> str:
        return self._from_field(self.FIELD_DEVICE_TYPE)

    @device_type.setter
    def device_type(self, value: str):
        self._to_field(self.FIELD_DEVICE_TYPE, value)

    def is_nvr(self) -> bool:
        return self.device_type == self.DEVICE_TYPE_NVR


class InputChannel(BaseHikvisionEntity):
    XML_ROOT_LIST_ELEMENT = 'InputProxyChannelList'
    XML_ROOT_ELEMENT = 'InputProxyChannel'

    FIELD_ID = 'id'
    FIELD_NAME = 'name'

    TO_STRING_FIELDS = (FIELD_ID, FIELD_NAME)

    @property
    def input_id(self) -> str:
        return self._from_field(self.FIELD_ID)

    @input_id.setter
    def input_id(self, value: str):
        self._to_field(self.FIELD_ID, value)

    @property
    def input_name(self) -> str:
        return self._from_field(self.FIELD_NAME)

    @input_name.setter
    def input_name(self, value: str):
        self._to_field(self.FIELD_NAME, value)


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
