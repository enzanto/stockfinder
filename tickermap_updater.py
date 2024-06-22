import asyncio
from rabbitmq_server import webscrape_nordnet
from screener.market_screener import MarketScreener
from localdb import tickermap
import settings
import json
import time
logger = settings.logger
async def new():
    screen = MarketScreener()
    screen.get_osebx_tickers()
    ticker_map = tickermap.TickerMap()
    new_stocks = []
    nordnet = webscrape_nordnet()
    nordnet.get_cookie()
    for index, row in screen.stocklist.iterrows():
        ticker = row['Symbol']
        data = ticker_map.get_map_data(ticker)
        if data is None:
            new_stocks.append(ticker)
            jsondata = {'name': row['Name'], 'ticker': row['Symbol'].lower(), 'market': row['Market']}
            print(type(jsondata))
            nordnetData = await nordnet.get_logo(jsondata)
            nordnetData = json.loads(nordnetData)
            nordnetInfo = await nordnet.get_info(nordnetData)
            nordnetInfo = json.loads(nordnetInfo)
            keys_to_transfer = ['sektor','bransje','ISIN']
            for key in keys_to_transfer:
                if key in nordnetInfo:
                    nordnetData[key] = nordnetInfo[key]
            ticker_map.insert_map_data(nordnetData['ticker'], nordnetData)

async def investech():
    screen = MarketScreener()
    screen.get_osebx_tickers()
    ticker_map = tickermap.TickerMap()
    nordnet = webscrape_nordnet()
    investech_stocks= []
    investech_keys=['icon']
    for index,row in screen.stocklist.iterrows():
        ticker = row['Symbol']
        data = ticker_map.get_map_data(ticker)
        if all(key in data for key in investech_keys):
            continue
        else:
            logger.debug(f"Missing Investech keys for {ticker}")
            nordnetData = await nordnet.get_logo(data)
            nordnetData = json.loads(nordnetData)
            if "icon" in nordnetData:
                data['icon'] = nordnetData['icon']
            else:
                logger.warning(f"{ticker} does not have an icon")
                time.sleep(3)
            ticker_map.insert_map_data(ticker, data)
            # url = input(f"Provide the URL for {ticker}: ")
            # investech_id = url.split(sep="=")[1]
            # answer = input(f"is {url} and {investech_id} correct?")
            # if answer.lower() == "y":
                # data['investech'] = url
                # data['investechID'] = investech_id
                # ticker_map.insert_map_data(ticker, data)
            # else:
            #     continue

async def test():
    ticker_map = tickermap.TickerMap()
    data = ticker_map.get_map_data("prot.ol")
    print(type(data))
    print(data)
asyncio.run(investech())
# asyncio.run(new())
# asyncio.run(test())