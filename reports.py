import asyncio

import json

from datetime import datetime, time
from screener import market_screener
import rabbitmq_client
from localdb import tickermap, scan_report, portfolio_report 
from settings import logger



async def report_full(tickers):
    '''
    Currently unused, might make use of this later
    '''
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    screener = market_screener.MarketScreener()
    await screener.rabbit.connect()
    screener.get_osebx_rsi()
    tasks = [screener.scan(i) for i in tickers]
    for task in asyncio.as_completed(tasks):
        try:
            await task
        except Exception as e:
            logger.warning(f"Error occured: {e}")
    logger.info("done awaiting tasks")
    embeds = []
    embeds2 = []
    images = []
    images2 = []
    finished_result = sorted(screener.result['result'], key=lambda x: x['stock'])
    for i in finished_result:
        if "image investtech" in i:
            embeds2.extend(i['embed'])
            images2.extend(i['image'])
        elif "image investtech" not in i:
            embeds.extend(i['embed'])
            images.extend(i['image'])
    await screener.rabbit.disconnect()
    logger.info("done with report")
    return embeds,images,embeds2,images2

async def report_db(tickers, minervini=False):
    '''
    Checks if there is a fresh report available. If not, creates one and store it in DB.
    Returns Discord embeds with images

    :param tickers: single ticker or list of tickers
    :param minervini: If True, returns only tickers that pass the minervini test.
    :return: Discord embeds and images (embeds, images, embeds2, images2, tickersReported)
    '''
    today = datetime.now()
    work = await rabbitmq_client.rabbitmq().connect()
    map_db = tickermap.TickerMap()
    report_db = scan_report.ScanReport()
    mapped_tickers = []
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    screener = market_screener.MarketScreener()
    await screener.rabbit.connect()
    screener.get_osebx_rsi()
    for i in tickers:
        try:
            mapped = map_db.get_map_data(i)
            mapped_tickers.append(mapped)
        except:
            logger.warning('ticker not in map')
    async def fetch_embeds(i):
        try:
            ticker = i['ticker']
            reportdate, json_data, investtech, pivots = report_db.get_report_data(ticker=ticker)
            if reportdate == None or today.date() > reportdate.date():
                await work.build_report(i, screener.indexRSI)
                reportdate, json_data, investtech, pivots = report_db.get_report_data(ticker=ticker)
            elif reportdate.time() < time(16,15):
                await work.build_report(i, screener.indexRSI)
                reportdate, json_data, investtech, pivots = report_db.get_report_data(ticker=ticker)
            if minervini:
                if json_data['minervini'] < 7 or json_data['vwap'] < 1:
                    return
                else:
                    logger.info(f"{ticker} added with a score of {json_data['minervini']}")
            await screener.create_embeds(json_data=json_data, image=pivots, investtech_image=investtech)
        except Exception as e:
            logger.warning(e)
    db_tasks = []
    for i in mapped_tickers:
        db_tasks.append(asyncio.create_task(fetch_embeds(i)))
    try:
        result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*db_tasks), timeout=600))
    except asyncio.TimeoutError:
        logger.warning("timed out of gather")
        cancel = 0
        for task in db_tasks:
            if not task.done():
                cancel += 1
                task.cancel()
        logger.warning(f"{cancel} tasks canceled")
    embeds = []
    embeds2 = []
    images = []
    images2 = []
    tickersReported = []
    finished_result = sorted(screener.result['result'], key=lambda x: x['stock'])
    for i in finished_result:
        if "image investtech" in i:
            embeds2.extend(i['embed'])
            images2.extend(i['image'])
            tickersReported.append(i['stock'])
        elif "image investtech" not in i:
            embeds.extend(i['embed'])
            images.extend(i['image'])
            tickersReported.append(i['stock'])
    await screener.rabbit.disconnect()
    logger.info("done with report")
    return embeds,images,embeds2,images2, tickersReported

async def report_portfolio(tickers):
    '''
    Checks if there is a fresh report available. If not, creates one and store it in DB.
    Returns Discord embed

    :param tickers: single ticker or list of tickers
    :return: Discord embed
    '''
    today = datetime.now()
    work = await rabbitmq_client.rabbitmq().connect()
    map_db = tickermap.TickerMap()
    report_db = portfolio_report.PortfolioReport()
    mapped_tickers = []
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    screener = market_screener.MarketScreener()
    await screener.rabbit.connect()
    screener.get_osebx_rsi()
    for i in tickers:
        mapped = map_db.get_map_data(i)
        mapped_tickers.append(mapped)
    async def fetch_embeds(i):
        ticker = i['ticker']
        reportdate, json_data = report_db.get_report_data(ticker=ticker) ###### change report data to new
        logger.info(reportdate)
        if reportdate == None or today.date() > reportdate.date():
            logger.info("today is not newest")
            await work.portfolio_report(i)
            reportdate, json_data = report_db.get_report_data(ticker=ticker)
        elif reportdate.time() < time(15,45): 
            logger.info("updating report,")
            await work.portfolio_report(i)
            reportdate, json_data = report_db.get_report_data(ticker=ticker)
        else:
            logger.info("today is newest")
        logger.info(json_data)
        await screener.create_portfolio_embeds(json_data=json_data)
    db_tasks = []
    for i in mapped_tickers:
        db_tasks.append(asyncio.create_task(fetch_embeds(i)))
    try:
        result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*db_tasks), timeout=600))
    except asyncio.TimeoutError:
        logger.warning("timed out of gather")
        cancel = 0
        for task in db_tasks:
            if not task.done():
                cancel += 1
                task.cancel()
        logger.warning(f"{cancel} tasks canceled")
    embeds = []
    finished_result = sorted(screener.result['portfolio'], key=lambda x: x['stock'])
    for i in finished_result:
            embeds.extend(i['embed'])
    await screener.rabbit.disconnect()
    logger.info("done with report")
    return embeds




if __name__ == "__main__":
    with open('data/map.json', 'r') as mapfile:
        data=json.load(mapfile)
    stocks = data['stocks'][:3]
    stocks[0]['yahoo'] = "https://finance.yahoo.com/chart/"+stocks[0]['ticker']
    logger.info(data['stocks'][:3])