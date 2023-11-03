# imports neded for async connection
import io
import yfinance as yf
import pandas
from datetime import datetime,timedelta,date
import base64
from bs4 import BeautifulSoup
import re
import asyncio
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from aio_pika import Message, connect
from aio_pika.abc import AbstractIncomingMessage
import time
import os
import localdb, screen, settings
logger = settings.logging.getLogger("bot")

try:
    hostname = os.environ['HOSTNAME']
except KeyError:
    hostname = "No hostname found"

#simple class object to fetch information from nordnet, with cookie and headers.
class webscrape_nordnet(object):

    def __init__(self):
        self.session = requests.Session()
        self.retry = Retry(connect=3, backoff_factor=0.5)
        self.adapter = HTTPAdapter(max_retries=self.retry)
        self.session.mount('http://', self.adapter)
        self.session.mount('https://', self.adapter)
        self.cookie = ""
        self.cookie_time = datetime.now()

    def get_cookie(self, url):
        self.session.get(url)
        self.cookie = self.session.cookies.get_dict()
        cookie_csrf = self.cookie['_csrf']
        cookie_next = self.cookie['NEXT']
        headers = {
            'cookie': f"lang=no; _csrf={cookie_csrf}",
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
            'Accept': "application/json",
            'Referer': "https://www.nordnet.no/",
            'client-id': "NEXT",
            'Connection': "keep-alive",
            'Cookie': f"NEXT={cookie_next}; lang=no; _csrf={cookie_csrf}; cookie_consent=analytics%2Cfunctional%2Cmarketing%2Cnecessary; _ga=GA1.2.403542613.1696779243; _gid=GA1.2.780383003.1696779243; _gat_UA-58430789-10=1", 
            'Sec-Fetch-Dest': "empty",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Site': "same-origin"
            }
        self.session.headers.update(headers)

#the "main" part of the class object for now. Fetches the icon URL from Nordnet at stores it.
    async def get_logo(self, ticker):
        await asyncio.sleep(0.5)
        if self.cookie == "" or self.cookie_time + timedelta(hours=12) > datetime.now():
            self.get_cookie("https://www.nordnet.no")
        symbol = ticker['ticker'].replace(".ol", "")
        url=f"https://www.nordnet.no/api/2/main_search?query={symbol}&search_space=ALL&limit=6"
        response = self.session.get(url)
        json_response = json.loads(response.text)
        try:
            response_filtered = next(item for item in json_response[0]['results'] if item['display_symbol'].lower() == symbol.lower() )
            if "instrument_icon" in response_filtered:
                ticker['icon'] = response_filtered['instrument_icon']
            ticker['nordnetID'] = str(response_filtered['instrument_id'])
            ticker['nordnetName'] = response_filtered['display_name']
        except Exception as e:
            await rabbit_logger(f"{ticker['ticker']} failed")
            print(e)
            print(ticker)
        json_ticker = json.dumps(ticker)
        return json_ticker


class webscrape_investtech(object):

    def __init__(self):
        self.session = requests.Session()
        self.retry = Retry(connect=3, backoff_factor=0.5)
        self.adapter = HTTPAdapter(max_retries=self.retry)
        self.session.mount('http://', self.adapter)
        self.session.mount('https://', self.adapter)
        self.cookie = ""
        self.cookie_time = datetime.now()


    def get_cookie(self, url):
        self.session.get(url)
        self.cookie = self.session.cookies.get_dict()
        cookie_sid = self.cookie['sid']
        headers = {
                "cookie": f"sid={cookie_sid}",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0",
                "Connection": "keep-alive",
                "Cookie": f"sid={cookie_sid}; consent=all"
            }
        self.session.headers.update(headers)


    async def get_text(self, ticker):
        await asyncio.sleep(0.5)
        if self.cookie == "" or self.cookie_time + timedelta(hours=12) > datetime.now():
            self.get_cookie("https://www.investtech.com")
        url = "https://www.investtech.com/no/market.php"

        querystring = {"CompanyID":ticker['investechID']}

        payload = ""

        try:
            response = self.session.get(url, data=payload, headers=self.session.headers, params=querystring)
            soup = BeautifulSoup(response.text, 'html.parser')
            header = soup.find(string=re.compile('teknisk analyse'))
            body = soup.find('div', class_="ca2017_twoColCollapse")
            body = body.text.split(" ",9)[9]
            body = body.split("Anbefaling")[0]
        except Exception as e:
            await rabbit_logger(f"{ticker['ticker']} failed to get header and body")
            header=None
            body=None
        return header,body

    async def get_image(self, ticker, b64=True):
        await asyncio.sleep(0.5)
        if self.cookie == "" or self.cookie_time + timedelta(hours=12) > datetime.now():
            self.get_cookie("https://www.investtech.com")
        payload = ""
        url = "https://www.investtech.com/no/img.php"
        querystring = {"CompanyID":ticker['investechID'],"chartId":"2","indicators":"80,81,82,83,84,85,87,88","w":"1174","h":"515"}
        try:
            response = self.session.get(url, data=payload, headers=self.session.headers, params=querystring)
            imageb64 = base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            await rabbit_logger(f"{ticker['ticker']} failed to get image")
            imageb64=None
        if b64:
            return imageb64
        else:
            return response.content

async def get_yahoo_data(ticker, start):
    if start == None:
        start = datetime.now() - timedelta(days=365*2.5)
    else:
        start = datetime.fromisoformat(start)
    await asyncio.sleep(0.3)
    try:
        if type(ticker) == dict:
            df = yf.download(ticker['ticker'], start=start, progress=False)
        elif type(ticker) == str:
            df = yf.download(ticker, start=start, progress=False)
        json_df = df.to_json(date_format='iso')
        return json_df
    except Exception as e:
        if type(ticker) == dict:
            rabbit_logger(f"failed to get data for {ticker['ticker']}")
        elif type(ticker) == str:
            rabbit_logger(f"Failed to get data for {ticker}")


class rabbitcon(object):
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.que = None
        self.exchange_log = None

    async def connect(self):
        try:
            self.connection = await connect("amqp://pod:pod@rabbit-cluster.default/")
        except:
            self.connection = await connect("amqp://pod:pod@192.168.1.204:31394/?heartbeat=900")

        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.exchange = self.channel.default_exchange
        self.exchange_log = await self.channel.declare_exchange("log")
        self.queue = await self.channel.declare_queue("rpc_queue")

async def rabbit_logger(log):
    log = f"{hostname} - {log}"
    message_body = log.encode()
    await conn.exchange_log.publish(Message(body=message_body), routing_key="log")

async def main(conn) -> None:
# 
# In the main loop i look for a Json string which contains two main keys: orget_yahoo_datader and request
# example:  {'order': 'get logo', 'request': 'the json to work on'}
# I could have multiple queues running. But for now i just want to do one task and move on to the next.
#

# connect to the server and declare a que. Setting prefetch to 1 so other workers can grab from que as well.
    # connection = await connect("amqp://pod:pod@rabbit-cluster.default/")
    # channel = await connection.channel()
    # await channel.set_qos(prefetch_count=1)
    # exchange = channel.default_exchange
    # queue = await channel.declare_queue("rpc_queue")
    await conn.connect()
    print(" [x] Awaiting RPC requests")
    scrape_nordnet = webscrape_nordnet()
    scrape_investtech = webscrape_investtech()
    update_report = localdb.scanReport()
    portfolio_report = localdb.portfolioReport()
    map_db = localdb.tickermap()
    async with conn.queue.iterator() as qiterator:
        message: AbstractIncomingMessage
        async for message in qiterator:
            print("test")
            try:
                async with message.process(requeue=False):
                    assert message.reply_to is not None
                    n = json.loads(message.body.decode())
                    print(n)
                    if n['order'] == "get logo":
                        response = await asyncio.wait_for(scrape_nordnet.get_logo(n['request']), timeout=10)
                    elif n['order'] == "investtech":
                        image = await asyncio.wait_for(scrape_investtech.get_image(n['request']), timeout=10)
                        header,body = await asyncio.wait_for(scrape_investtech.get_text(n['request']), timeout=10)
                        response_dict = {'ticker': n['request']['ticker'], 'image': image, 'header': header, 'body': body}
                        response = json.dumps(response_dict)
                    elif n['order'] == "yahoo":
                        response = await asyncio.wait_for(get_yahoo_data(n['request'], n['start']),timeout=10)
                    elif n['order'] == "build report":
                        try:
                            try:
                                mapped_ticker = n['request']
                                ticker = n['request']['ticker']
                            except:
                                ticker=n['request']['Symbol']
                                mapped_ticker = map_db.get_map_data(ticker)
                            if mapped_ticker == None:
                                raise "Mapped ticker not found"
                            logger.info(f"starting {ticker}")
                            await localdb.db_updater(ticker,serverside=True)
                            screener = screen.MarketScreener()
                            if n['rsi'] == None:
                                screener.get_osebx_rsi()
                            else:
                                screener.indexRSI = n['rsi']
                            json_result, image= await screener.scan(mapped_ticker, return_text=True)
                            header,body = await asyncio.wait_for(scrape_investtech.get_text(mapped_ticker), timeout=120)
                            investtech_image = await asyncio.wait_for(scrape_investtech.get_image(mapped_ticker, b64=False), timeout=120)
                            json_result['header'] = header
                            json_result['body'] = body
                            #get json from screen
                            response = json.dumps(json_result)
                            # response = json.dumps({'ticker': ticker, 'status': 'complete'})
                            #have function here to add data to database
                            update_report.insert_report_data(ticker,json_result, image, investtech_image)
                        except Exception as e:
                            print(e)
                            response = json.dumps({'ticker': ticker, 'status': "an error occured", 'minervini': 0})

                    elif n['order'] == "portfolio report":
                        try:
                            ticker=n['request']['ticker']
                            logger.info(f"starting {ticker}")
                            await localdb.db_updater(ticker,serverside=True)
                            screener = screen.MarketScreener()
                            if n['rsi'] == None:
                                screener.get_osebx_rsi()
                            else:
                                screener.indexRSI = n['rsi']
                            print("test1")
                            #json response, with header and body. fields: ema 8, ema21, sma50, trailing stop, volume sma
                            json_result = await screener.portfolio_scan(n['request'], return_text=True)
                            response = json.dumps({'ticker': ticker, 'status': 'complete'})
                            print(json_result)
                            portfolio_report.insert_report_data(ticker,json_result)
                        except Exception as e:
                            print(e)
                            response = json.dumps({'ticker': ticker, 'status': "an error occured", 'minervini': 0})
                    else:
                        await message.reject(requeue=True)
                        continue
                    await conn.exchange.publish(
                        Message(
                            body=response.encode(),
                            correlation_id=message.correlation_id,
                        ),
                        routing_key=message.reply_to,
                    )
                    print("Request complete")
            except asyncio.TimeoutError:
                await message.reject(requeue=True)
                print("Message was timed out and requeued")
            except Exception:
                logging.exception("Processing error for message %r", message)

async def test():
    tickermap = {"test": {"innertest": "innervalue"},"name": "EQUINOR", "ticker": "eqnr.ol", "investech": "https://www.investtech.com/no/market.php?CompanyID=100820", "investechID": "100820", "nordnet": "https://www.nordnet.no/market/stocks/16105420-equinor", "sektor": "energi", "bransje": "olje & gass - integrert", "icon": "https://images.ctfassets.net/6xe8ehctp75g/1g0ykLy6DuEW29ZDoCgtKF/e200733fbeb962a1fa24bea48acab31c/image.png", "nordnetID": "16105420", "nordnetName": "EQUINOR"}
    scrape_investtech = webscrape_investtech()
    header,body = await asyncio.wait_for(scrape_investtech.get_text(tickermap), timeout=10)
    investtech_image = await asyncio.wait_for(scrape_investtech.get_image(tickermap, b64=False), timeout=10)
    screener = screen.MarketScreener()
    screener.get_osebx_rsi()
    json_result, image= await screener.scan(tickermap, return_text=True)
    savereport = localdb.saveReport()
    # savereport.insert_report_data(ticker=tickermap['ticker'], json_data=json_result, image=image, investtech_img=investtech_image)
    dbDate, dbJson, dbInvesttech, dbimg = savereport.get_report_data(ticker=tickermap['ticker'])
    print(dbDate)
    imagefile = io.BytesIO(dbInvesttech)
    imagefile.seek(0)
    with open("testfile.png", 'wb') as file:
        file.write(imagefile.getvalue())

if __name__ == "__main__":
    conn = rabbitcon()
    asyncio.run(main(conn))
    # asyncio.run(test())