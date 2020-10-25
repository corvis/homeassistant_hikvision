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
from asyncio import CancelledError

import aiohttp

from .model import EventNotificationAlert

LOGGER = logging.getLogger('Hikvision_ISAPIClient')

ENDPOINT_EVENT_ALERTS_STREAM = '/ISAPI/Event/notification/alertStream'

__all__ = ['ISAPIClient']


class HikhisionStreamPartReader(aiohttp.BodyPartReader):
    async def read_chunk(self, size: int = aiohttp.BodyPartReader.chunk_size) -> bytes:
        """Reads body part content chunk of the specified size.

        size: chunk size
        """
        if self._at_eof:
            return b''
        if self._length:
            chunk = await self._read_chunk_from_length(size)
        else:
            chunk = await self._read_chunk_from_stream(size)

        self._read_bytes += len(chunk)
        if self._read_bytes == self._length:
            self._at_eof = True
        return chunk


class ISAPIClient(object):
    MAX_RETRY_INTERVAL = datetime.timedelta(minutes=5)
    INITIAL_RETRY_INTERVAL = datetime.timedelta(seconds=3)
    RETRY_INTERVAL_MULTIPLIER = 2

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.auth = None
        if username is not None or password is not None:
            self.auth = aiohttp.BasicAuth(username, password)
        self._infinite_session: aiohttp.ClientSession = None
        self._session: aiohttp.ClientSession = None
        self._retry_interval = self.INITIAL_RETRY_INTERVAL

    def __get_session(self, infinite=True) -> aiohttp.ClientSession:
        if infinite and self._infinite_session:
            return self._infinite_session
        elif not infinite and self._session:
            return self._session
        timeout = aiohttp.ClientTimeout(total=None) if infinite else None
        new_session = aiohttp.ClientSession(auth=self.auth, timeout=timeout)
        if infinite:
            self._infinite_session = new_session
        else:
            self._session = new_session
        return new_session

    def __build_url(self, path: str) -> str:
        return self.base_url + path

    async def listen_hikvision_event_stream(self, queue: asyncio.Queue):
        async with self.__get_session(infinite=True) as client:
            while True:
                try:
                    async with client.get(self.__build_url(ENDPOINT_EVENT_ALERTS_STREAM)) as response:
                        self._retry_interval = self.INITIAL_RETRY_INTERVAL
                        reader = aiohttp.MultipartReader.from_response(response)
                        reader.stream.part_reader_cls = HikhisionStreamPartReader
                        while True:
                            part = await reader.next()
                            if part is None:
                                break
                            filedata = await part.read(decode=False)
                            if filedata:
                                event = EventNotificationAlert.from_xml_str(filedata)
                                queue.put_nowait(event)
                except CancelledError:
                    LOGGER.info("Gracefully terminating alert stream listener")
                    break
                except (TimeoutError, Exception) as e:
                    retry_delay = self._retry_interval
                    self._retry_interval = self._retry_interval * self.RETRY_INTERVAL_MULTIPLIER
                    retry_notice = 'Reconnecting in {} seconds'.format(retry_delay.total_seconds())
                    if isinstance(e, TimeoutError):
                        LOGGER.warning("Timeout while reading data from hikvision alert stream. " + retry_notice)
                    else:
                        LOGGER.exception('Unknown error while reading event stream. ' + retry_notice)
                    await asyncio.sleep(retry_delay.total_seconds())
