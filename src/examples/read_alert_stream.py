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
import os

from hikvision_isapi.isapi.client import ISAPIClient
from hikvision_isapi.isapi.model import EventNotificationAlert

eventbus = asyncio.Queue()


async def main(hik_client: ISAPIClient):
    while True:
        event: EventNotificationAlert = await eventbus.get()

        # if event_type == 'videoloss' and event_state == 'inactive':
        #     continue
        print('Event: {} \tState: {}, \tChannel: {}/{}, \t Time: {}'.format(event.type, event.state, event.channel_id,
                                                                            event.channel_name,
                                                                            str(event.timestamp)))


if __name__ == '__main__':
    hik_client = ISAPIClient(os.environ.get('BASE_URL'),
                             os.environ.get('USERNAME'),
                             os.environ.get('PASSWORD')
                             )
    loop = asyncio.get_event_loop()

    loop.run_until_complete(asyncio.gather(main(hik_client), hik_client.listen_hikvision_event_stream(eventbus)))
