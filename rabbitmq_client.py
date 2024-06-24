import asyncio
import pandas as pd
import base64
import uuid
import aio_pika
import json
from settings import rabbit_password,rabbit_user, logging
from typing import MutableMapping
from aio_pika.abc import (
    AbstractChannel, AbstractConnection, AbstractIncomingMessage, AbstractQueue,
)
logger = logging.getLogger("bot")
class rabbitmq(object):
    connection: AbstractConnection
    channel: AbstractChannel
    callback_queue: AbstractQueue
    loop: asyncio.AbstractEventLoop

    def __init__(self):
        # Create a connection to RabbitMQ
        self.dictlist = None
        self.data = None
        self.futures: MutableMapping[str, asyncio.Future] = {}
        self.loop = asyncio.get_running_loop()
        self.rpc_queue = str(uuid.uuid4())
        logger.info(f"RPC que: {self.rpc_queue}")

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(f"amqp://{rabbit_user}:{rabbit_password}@rabbit-cluster.default/?heartbeat=900", loop=self.loop)
        except:
            self.connection = await aio_pika.connect_robust(f"amqp://{rabbit_user}:{rabbit_password}@192.168.10.80:30500/?heartbeat=900", loop=self.loop)
        self.channel = await self.connection.channel()
        self.callback_queue = await self.channel.declare_queue(name=self.rpc_queue,exclusive=True)
        await self.callback_queue.consume(self.on_response, no_ack=True)
        return self


    async def disconnect(self):
        await self.channel.close()
        await self.connection.close()
        self.futures.clear()
        try:
            # await self.callback_queue.delete()
            await asyncio.wait_for(self.callback_queue.delete(), timeout=3)
        except asyncio.TimeoutError as e:
            logger.warning("Timeout occurred while deleting the queue")
            logger.warning(e)
        except aio_pika.exceptions.ChannelNotFoundEntity:
            pass
        except Exception as e:
            logger.info(e)
        logger.info("done closing")
    async def on_response(self, message: AbstractIncomingMessage) -> None:
        if message.correlation_id is None:
            logger.info(f"Bad message {message!r}")
            return
        future: asyncio.Future = self.futures.pop(message.correlation_id)
        future.set_result(message.body)
    async def send_rpc_request(self,i: int) -> int:
        correlation_id = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futures[correlation_id] = future
        # Publish the RPC request with a reply_to field pointing to the callback queue
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=str(i).encode(),
                content_type="text/plain",
                correlation_id=correlation_id,
                reply_to=self.callback_queue.name
            ),
            routing_key="rpc_queue"
        )
        logger.info(f"Sent RPC request: {i}")
        logger.info(int(await future))


    async def send_json(self, i):
        try:
            correlation_id = str(uuid.uuid4())
            future = self.loop.create_future()
            self.futures[correlation_id] = future
            order = {'order': 'get logo', 'request': i}
            json_object = json.dumps(order, indent=4)
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json_object.encode(),
                    content_type="text/plain",
                    correlation_id=correlation_id,
                    reply_to=self.callback_queue.name,
                    expiration=300
                ),
                routing_key="rpc_queue"
            )
            json_return = json.loads(await future)
            logger.info(json_return)
            for d in self.data['stocks']:
                if d['ticker'] == json_return['ticker']:
                    if 'icon' in json_return:
                        d['icon'] = json_return['icon']
                    if 'nordnetID' in json_return:
                        d['nordnetID'] = json_return['nordnetID']
                    if 'nordnetName' in json_return:
                        d['nordnetName'] = json_return['nordnetName']
        except asyncio.CancelledError as e:
            logger.warning(f"task {i} was cancelled: {i['ticker']}")
            logger.warning(e)
            raise

    async def get_investtech(self, i):
        try:
            correlation_id = str(uuid.uuid4())
            future = self.loop.create_future()
            self.futures[correlation_id] = future
            order = {'order': 'investtech', 'request': i}
            json_object = json.dumps(order, indent=4)
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json_object.encode(),
                    content_type="text/plain",
                    correlation_id=correlation_id,
                    reply_to=self.callback_queue.name
                ),
                routing_key="rpc_queue"
            )
            json_return = json.loads(await future)
            image = json_return['image']
            decoded_image = base64.b64decode(image)
            header = json_return['header']
            body = json_return['body']
            filename = json_return['ticker'].lower().replace(".","_")
            with open(f"images/{filename}-investtech.png", "wb") as imagefile:
                imagefile.write(decoded_image)
            return header,body
        except asyncio.CancelledError as e:
            logger.warning(f"task {i} was cancelled: {i['ticker']}")
            logger.warning(e)
            raise
    
    async def build_report(self,request_dict, rsi = None):
        try:
            correlation_id = str(uuid.uuid4())
            future = self.loop.create_future()
            self.futures[correlation_id] = future
            order = {'order': 'build report', 'request': request_dict, 'rsi': rsi}
            json_object = json.dumps(order, indent=4)
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json_object.encode(),
                    content_type="text/plain",
                    correlation_id=correlation_id,
                    reply_to=self.callback_queue.name
                ),
                routing_key="rpc_queue"
            )
            json_return = json.loads(await future)
            if 'status' in json_return:
                logger.warning(json_return['ticker'], json_return['status'])
            else:
                logger.info(json_return['ticker'])
            return json_return 
        except asyncio.CancelledError as e:
            logger.warning(f"task was cancelled: {request_dict}")
            logger.warning(e)
            raise


    async def portfolio_report(self,request_dict, rsi = None):
        try:
            correlation_id = str(uuid.uuid4())
            future = self.loop.create_future()
            self.futures[correlation_id] = future
            order = {'order': 'portfolio report', 'request': request_dict, 'rsi': rsi}
            json_object = json.dumps(order, indent=4)
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json_object.encode(),
                    content_type="text/plain",
                    correlation_id=correlation_id,
                    reply_to=self.callback_queue.name
                ),
                routing_key="rpc_queue"
            )
            json_return = json.loads(await future)
            if 'status' in json_return:
                logger.warning(json_return['ticker'])
                logger.warning(json_return['status'])
            return json_return 
        except asyncio.CancelledError as e:
            logger.warning(f"task was cancelled: {request_dict}")
            logger.warning(e)
            raise

    async def get_yahoo(self, i, start=None):
        if type(i) == dict:
            ticker = i['ticker']
        elif type(i) == str:
            ticker = i
        try:
            correlation_id = str(uuid.uuid4())
            future = self.loop.create_future()
            self.futures[correlation_id] = future
            order = {'order': 'yahoo', 'request': ticker, 'start': str(start)}
            json_object = json.dumps(order, indent=4)
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json_object.encode(),
                    content_type="text/plain",
                    correlation_id=correlation_id,
                    reply_to=self.callback_queue.name
                ),
                routing_key="rpc_queue"
            )
            json_return = json.loads(await future)
            df = pd.DataFrame.from_dict(json_return)
            df.index = pd.to_datetime(df.index)
            return df
        except asyncio.CancelledError as e:
            logger.info(f"task was cancelled: {ticker}")
            logger.info(e)
            raise
# main is used for testing new features during development
async def main():
    logger.info("not in use at the moment")
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
