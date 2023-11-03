# from investech_scrape import get_img,get_text
from screen import MarketScreener
import discord
import json
import pandas as pd
from sqlalchemy import create_engine
from indicators import *
from osebx import *
import asyncio
from localdb import userdata, tickermap, scanReport, portfolioReport
from datetime import datetime, time
import rabbitmq_client


def report_simple(tickers):
    embed_images = []
    embeds = []
    length = 6
    for ticker in tickers:
        # print(ticker)
        filename = ticker['ticker'].lower().replace(".","_")+".jpg"
        MarketScreener.create_chart(ticker['ticker'])
        header, message = "header","message"
        img = discord.File("images/"+filename, filename=filename)
        mbd=discord.Embed(title=ticker['name'], url="https://finance.yahoo.com/chart/"+ticker['ticker'], description=message)
        mbd.set_image(url="attachment://"+filename)
        mbd.set_author(name=header, url=ticker['investech'])
        embed_images.append(img)
        embeds.append(mbd)
    print(len(embeds))
    for i in range(0, len(embeds), length):
        x=i
        emb = embeds[x:x+length]
        im = embed_images[x:x+length]
    return emb,im

async def report_full(tickers):
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    screener = MarketScreener()
    await screener.rabbit.connect()
    screener.get_osebx_rsi()
    tasks = [screener.scan(i) for i in tickers]
    for task in asyncio.as_completed(tasks):
        try:
            await task
        except Exception as e:
            print(f"Error occured: {e}")
    print("done awaiting tasks")
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
    print("done with report")
    return embeds,images,embeds2,images2

async def report_db(tickers, minervini=False):
    today = datetime.now()
    work = await rabbitmq_client.rabbitmq().connect()
    map_db = tickermap()
    report_db = scanReport()
    mapped_tickers = []
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    screener = MarketScreener()
    await screener.rabbit.connect()
    screener.get_osebx_rsi()
    for i in tickers:
        try:
            mapped = map_db.get_map_data(i)
            mapped_tickers.append(mapped)
        except:
            print('ticker not in map')
            return
    async def fetch_embeds(i):
        try:
            ticker = i['ticker']
            reportdate, json_data, investtech, pivots = report_db.get_report_data(ticker=ticker)
            # print(reportdate)
            if reportdate == None or today.date() > reportdate.date():
                # print("today is not newest")
                await work.build_report(i, screener.indexRSI)
                reportdate, json_data, investtech, pivots = report_db.get_report_data(ticker=ticker)
            elif reportdate.time() < time(17,15):
                # print("updating report,")
                await work.build_report(i, screener.indexRSI)
                reportdate, json_data, investtech, pivots = report_db.get_report_data(ticker=ticker)
            # else:
                # print("today is newest")
            if minervini:
                if json_data['minervini'] < 7 or json_data['vwap'] < 1:
                    # print(f"{json_data['ticker']} skipped. minervini score: {json_data['minervini']}")
                    return
                else:
                    print(f"{ticker} added with a score of {json_data['minervini']}")
            await screener.create_embeds(json_data=json_data, image=pivots, investtech_image=investtech)
        except Exception as e:
            print(i)
    db_tasks = []
    for i in mapped_tickers:
        db_tasks.append(asyncio.create_task(fetch_embeds(i)))
    try:
        result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*db_tasks), timeout=600))
    except asyncio.TimeoutError:
        print("timed out of gather")
        cancel = 0
        for task in db_tasks:
            if not task.done():
                cancel += 1
                task.cancel()
        print(f"{cancel} tasks canceled")
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
    print("done with report")
    return embeds,images,embeds2,images2

async def report_portfolio(tickers):
    today = datetime.now()
    work = await rabbitmq_client.rabbitmq().connect()
    map_db = tickermap()
    report_db = portfolioReport()
    mapped_tickers = []
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    screener = MarketScreener()
    await screener.rabbit.connect()
    screener.get_osebx_rsi()
    for i in tickers:
        mapped = map_db.get_map_data(i)
        mapped_tickers.append(mapped)
    async def fetch_embeds(i):
        ticker = i['ticker']
        reportdate, json_data = report_db.get_report_data(ticker=ticker) ###### change report data to new
        print(reportdate)
        if reportdate == None or today.date() > reportdate.date():
            print("today is not newest")
            await work.portfolio_report(i)
            reportdate, json_data = report_db.get_report_data(ticker=ticker)
        elif reportdate.time() < time(16,45):
            print("updating report,")
            await work.portfolio_report(i)
            reportdate, json_data = report_db.get_report_data(ticker=ticker)
        else:
            print("today is newest")
        print(json_data)
        await screener.create_portfolio_embeds(json_data=json_data)
    db_tasks = []
    for i in mapped_tickers:
        db_tasks.append(asyncio.create_task(fetch_embeds(i)))
    try:
        result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*db_tasks), timeout=600))
    except asyncio.TimeoutError:
        print("timed out of gather")
        cancel = 0
        for task in db_tasks:
            if not task.done():
                cancel += 1
                task.cancel()
        print(f"{cancel} tasks canceled")
    embeds = []
    # embeds2 = []
    # images = []
    # images2 = []
    finished_result = sorted(screener.result['portfolio'], key=lambda x: x['stock'])
    for i in finished_result:
        # if "image investtech" in i:
        #     embeds2.extend(i['embed'])
        #     images2.extend(i['image'])
        # elif "image investtech" not in i:
            embeds.extend(i['embed'])
        #     images.append(i['image'])
    await screener.rabbit.disconnect()
    print("done with report")
    return embeds




if __name__ == "__main__":
    with open('data/map.json', 'r') as mapfile:
        data=json.load(mapfile)
    stocks = data['stocks'][:3]
    stocks[0]['yahoo'] = "https://finance.yahoo.com/chart/"+stocks[0]['ticker']
    print(data['stocks'][:3])