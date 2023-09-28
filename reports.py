from investech_scrape import get_img,get_text
import discord
import json
import pandas as pd
from sqlalchemy import create_engine
from indicators import *
from osebx import *


def report_simple(tickers):
    embed_images = []
    embeds = []
    length = 6
    for ticker in tickers:
        # print(ticker)
        get_img(ticker)
        header, message = get_text(ticker)
        img = discord.File("images/"+ticker['investechID']+".jpg", filename=ticker['investechID']+".jpg")
        mbd=discord.Embed(title=ticker['name'], url="https://finance.yahoo.com/chart/"+ticker['ticker'], description=message)
        mbd.set_image(url="attachment://"+ticker['investechID']+".jpg")
        mbd.set_author(name=header, url=ticker['investech'])
        embed_images.append(img)
        embeds.append(mbd)
    print(len(embeds))
    for i in range(0, len(embeds), length):
        x=i
        emb = embeds[x:x+length]
        im = embed_images[x:x+length]
    return emb,im

def report_full(tickers):
    if isinstance(tickers, list) == False:
            tickers = [tickers]
    embed_images = []
    embeds = []
    length = 6
    indexRSI = get_osebx_rsi()
    engine = create_engine('sqlite:///TEST_DB.db')
    for ticker in tickers:
        print(ticker)
        stock = ticker['ticker']
        # market = ticker['market']
        stockname = ticker['name']
        stock_db = "ticker_"+stock.lower().replace(".","_")
        df = pd.read_sql(stock_db,engine)
        df['Volume_SMA_20'] = round(df['Volume'].rolling(window=20).mean(),2)
        ap = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1])/3
        vwap = round((ap * df['Volume'].iloc[-1])/1000000,2)
        volumeChange = round(((df['Volume'].iloc[-1] / df['Volume_SMA_20'].iloc[-1]))*100,2)
        priceChange = round(((df['Adj Close'].iloc[-1] / df['Adj Close'].iloc[-2]) -1)*100,2)
        if df['High'].iloc[-1] == df['Low'].iloc[-1]:
            closingRange = 50
        else:
            closingRange = round(((df['Close'].iloc[-1]-df['Low'].iloc[-1])/(df['High'].iloc[-1]-df["Low"].iloc[-1]))*100,2)
        trend = trend_template(df)
        
        df['RSI'] = ta.momentum.rsi(df["Close"], window=6)
        rs = (df['RSI'].iloc[-1] / indexRSI) * 100
        macd_out = macd(df)
        new_high = new_20day_high(df)
        bollinger_band_out = bollinger_band(df)
        pivotPoint = pivot_point(df)
        if rs >= 100:
            color=discord.Color.green()
        elif rs >= 50:
            color=discord.Color.orange()
        else:
            color=discord.Color.red()
        ### Make embed based on investtech
        get_img(ticker)
        header,body = get_text(ticker)
        img = discord.File("images/"+ticker['investechID']+".jpg", filename=ticker['investechID']+".jpg")
        mbd=discord.Embed(title=stockname, url="https://finance.yahoo.com/chart/"+stock, description=body,color=color)
        mbd.set_image(url="attachment://"+ticker['investechID']+".jpg")
        mbd.set_author(name=header, url=ticker['investech'])
        mbd.add_field(name="price", value=str(df["Adj Close"].iloc[-1].round(1))+"kr\n"+str(priceChange)+"%")
        mbd.add_field(name="Closing Range", value=str(closingRange)+"%")
        mbd.add_field(name="vwap", value=str(vwap)+"mNOK")
        mbd.add_field(name="Volume sma20", value=str(volumeChange)+"%")
        mbd.add_field(name="RS", value=rs.round(2))
        # mbd.set_footer(text=market)
        embed_images.append(img)
        embeds.append(mbd)
    
    return embeds,embed_images



if __name__ == "__main__":
    with open('map.json', 'r') as mapfile:
        data=json.load(mapfile)
    stocks = data['stocks'][:3]
    stocks[0]['yahoo'] = "https://finance.yahoo.com/chart/"+stocks[0]['ticker']
    print(data['stocks'][:3])