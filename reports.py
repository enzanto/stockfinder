# from investech_scrape import get_img,get_text
from screen import MarketScreener
import discord
import json
import pandas as pd
from sqlalchemy import create_engine
from indicators import *
from osebx import *
import asyncio


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
            embeds.append(i['embed'])
            images.append(i['image'])
    await screener.rabbit.disconnect()
    print("done with report")
    return embeds,images,embeds2,images2



if __name__ == "__main__":
    with open('data/map.json', 'r') as mapfile:
        data=json.load(mapfile)
    stocks = data['stocks'][:3]
    stocks[0]['yahoo'] = "https://finance.yahoo.com/chart/"+stocks[0]['ticker']
    print(data['stocks'][:3])