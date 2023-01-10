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
import ta
from io import StringIO
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

#### get updated list of ticker symbols
#
# provide your own stocklist in a pandas dataframe named stocklist, required columns: Name, Symbol, Market
# or modify the webscrape to get stocklist from your preferred exhchange
#
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
stocklist['Symbol'] = stocklist["Symbol"]+".ol"
stocklist = stocklist.sort_values('Name')
####### End of stocklist gather, change the above code to your liking

####### Get OSEBEX prices and calculate RSI
now = dt.datetime.now()
start = now - dt.timedelta(days=30)
end_date = now.strftime("%Y-%m-%d")
start_date = start.strftime("%Y-%m-%d")

url = "https://live.euronext.com/en/ajax/AwlHistoricalPrice/getFullDownloadAjax/NO0007035327-XOSL"

payload = "format=csv&decimal_separator=.&date_form=d%2Fm%2FY&startdate="+start_date+"&startdate="+start_date+"&enddate="+end_date+"&enddate="+end_date
headers = {
    "authority": "live.euronext.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://live.euronext.com",
    "referer": "https://live.euronext.com/en/product/indices/NO0007035327-XOSL",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.76"
}

response = requests.request("POST", url, data=payload, headers=headers)
response=response.text

osebx_df = pd.read_csv(StringIO(response), header=3, index_col=False, dayfirst=True, sep=";").set_index("Date")
osebx_df.index = pd.to_datetime(osebx_df.index, dayfirst=True)
osebx_df = osebx_df.sort_index()
osebx_df['RSI'] = ta.momentum.rsi(osebx_df['Close'], window=6)
indexRSI = osebx_df['RSI'].iloc[-1]
###### End of OSEBEX RSI
stocklist = stocklist.tail(20)
for i in stocklist.index:
    stock = str(stocklist["Symbol"][i])
    db_updater(stock, engine)
message = today + "\n"
for i in stocklist.index:
    stock = stocklist["Symbol"][i]
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
    if df['High'].iloc[-1] == df['Low'].iloc[-1]:
        closingRange = 50
    else:
        closingRange = round(((df['Close'].iloc[-1]-df['Low'].iloc[-1])/(df['High'].iloc[-1]-df["Low"].iloc[-1]))*100,2)
    df['RSI'] = ta.momentum.rsi(df["Close"], window=6)
    trend = trend_template(df)
    if trend != None:
        rs = (df['RSI'].iloc[-1] / indexRSI) * 100
        macd_out = macd(df)
        new_high = new_20day_high(df)
        bollinger_band_out = bollinger_band(df)
        pivotPoint = pivot_point(df)
        message = message + "\n" + stockname + " " + str(df["Adj Close"].iloc[-1].round(2)) + "kr " + str(priceChange) + "% and closing range: " + str(closingRange) + "%"
        message = message + "\n" + str(vwap) + "m NOK " + str(volumeChange)+"% of volume SMA20 RS= " + str(rs.round(2)) + "\n" + trend
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