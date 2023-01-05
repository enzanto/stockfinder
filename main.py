import pandas as pd
from sqlalchemy import create_engine
from localdb import db_updater
from indicators import macd,new_20day_high,bollinger_band,trend_template,pivot_point
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import sys, os
from discord import Webhook, RequestsWebhookAdapter
import requests
from bs4 import BeautifulSoup
# setup
try: 
    discord_url = os.environ['discord_url']
    print("discord_url ENV OK")
    discord=True
except:
    print("Discord URL not provided, will only print resluls")
    discord=False
try:
    DBUSER = os.environ['DBUSER']
    print("DBUSER ENV ok")
    DBPASSWORD = os.environ['DBPASSWORD']
    print("DBPASSWORD ENV ok")
    DBADDRESS = os.environ['DBADDRESS']
    print('DBADDRESS ENV OK')
    DBNAME = os.environ['DBNAME']
    try:
        DBPORT = os.environ['DBPORT']
        print('DBPORT ENV ok')
    except:
        DBPORT = 5432
        print('DBPORT set to standard 5432')
    engine = create_engine('postgresql+psycopg2://'+DBUSER+':'+DBPASSWORD+'@'+DBADDRESS+':'+DBPORT+'/'+DBNAME)
except KeyError as err:
    print("DB variables not present, using sqlite local db")
    engine = create_engine('sqlite:///TEST_DB.db')

if discord:
    webhook = Webhook.from_url(discord_url, adapter=RequestsWebhookAdapter())
today = dt.date.today()
today = str(today)

# get updated list of ticker symbols
url = "https://live.euronext.com/en/pd_es/data/stocks"

querystring = {"mics":"XOSL,MERK,XOAS"}

payload = "iDisplayLength=999&iDisplayStart=0"
headers = {
    "cookie": "visid_incap_2784297=ycNtzE%2BcTqWSMVRPd8UR9i2rsWMAAAAAQUIPAAAAAADJL%2B4cY%2FbTQYmUc9f1OSqh; incap_ses_1103_2784297=fWbSHE%2B93H0vtC9dcKVODy2rsWMAAAAAWbJT65mx4E3P75XtK25IkA%3D%3D",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54"
}

response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
jsonresponse = response.json()
stocklist = pd.DataFrame(columns = ['Name', 'Symbol', 'Market'])
for i in jsonresponse['aaData']:
    bsname = BeautifulSoup(i[1], "lxml")
    name = bsname.text
    symbol = i[3]
    bsexchange = BeautifulSoup(i[4], "lxml")
    htmlexchange = bsexchange.find("div")
    exchange = htmlexchange.attrs['title']
    df2 = pd.DataFrame([[name,symbol,exchange]],columns=['Name','Symbol','Market'])
    stocklist = pd.concat([df2,stocklist], ignore_index=True)
stocklist = stocklist.sort_values('Name')


for i in stocklist.index:
    stock = str(stocklist["Symbol"][i])+".ol"
    db_updater(stock, engine)
message = today + "\n"
for i in stocklist.index:
    stock = stocklist["Symbol"][i]+".ol"
    market = stocklist["Market"][i]
    stockname = stocklist["Name"][i]
    stock_db = "ticker_" + stock.lower().replace(".","_")
    df = pd.read_sql(stock_db,engine)
    if len(df) < 200:
        continue
    df['Volume_SMA_20'] = round(df['Volume'].rolling(window=20).mean(),2)
    ap = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1])/3
    vwap = round((ap * df['Volume'].iloc[-1])/1000000,2)
    volumeChange = round(((df['Volume'].iloc[-1] / df['Volume_SMA_20'].iloc[-1]))*100,2)
    priceChange = round(((df['Adj Close'].iloc[-1] / df['Adj Close'].iloc[-2]) -1)*100,2)
    trend = trend_template(df)
    if trend != None:
        macd_out = macd(df)
        new_high = new_20day_high(df)
        bollinger_band_out = bollinger_band(df)
        pivotPoint = pivot_point(df)
        message = message + "\n" + stockname + " " + str(df["Adj Close"].iloc[-1].round(2)) + "kr " + str(priceChange) + "%"
        message = message + "\n" + str(vwap) + "mNOK " + str(volumeChange)+"% of volume SMA20\n" + trend
        if pivotPoint != None:
            message = message + "\n" + pivotPoint
        if macd_out != None:
            message = message + "\n" + macd_out
        if new_high != None:
            message = message + "\n" + new_high
        if bollinger_band_out != None:
            message = message + "\n" + bollinger_band_out
        message = message + '\nhttps://finance.yahoo.com/chart/'+stock
        message = message + "\n" + market
        message = message + "\n" + "---------------------------------"
        message = message + "\n" + ""
        if len(message) > 1800:
            if discord:
                webhook.send(content=message)
            print(message)
            message = ""
if discord:
    webhook.send(content=message)
print(message)