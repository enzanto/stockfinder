import pandas as pd
import rabbitmq.rabbitmq_client as rabbitmq
import asyncio
from sqlalchemy import create_engine
from localdb import db_updater
from indicators import macd,new_20day_high,bollinger_band,trend_template,pivot_point,trailing_stop
# from investech_scrape import get_img,get_text
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import mplfinance as mpf
import sys, os
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import ta
from io import StringIO
import gspread
from gspread_dataframe import set_with_dataframe
import json
import time
import settings

logger = settings.logging.getLogger("discord")
# setup
try: #discord
    discord_token = os.environ['discord_token']
    print("discord_webhook_url ENV OK")
    discord_chk=True
except:
    print("Discord URL not provided, will only print resluls")
    discord_chk=False
try:#google sheet
    gc = gspread.service_account("/usr/src/app/credentials.json")
    sh = gc.open('oslobors')
    ws = sh.worksheet('oslobors')
    googleSheet = True
except:
    print("Google sheets not selected")
    googleSheet = False
try:#database
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
    engine = create_engine('sqlite:///data/TEST_DB.db')

if discord_chk:
    intents = discord.Intents.default()
    bot = discord.Client(intents=intents)
    channel_id = 1161668764341907556
today = dt.date.today()
today = str(today)

class MarketScreener:
    def __init__(self):
        with open('data/map.json','r') as mapfile:
            data = json.load(mapfile)
            self.tickermap = data['stocks']
        self.result = {"result": [], "metadata": {"time": None}}
        self.indexRSI = 0
        self.stocklist = pd.DataFrame(columns = ['Name', 'Symbol', 'Market'])
        self.exportdf = pd.DataFrame(columns = ['Stock', 'Ticker', 'Adj Close', 'Change', 'Closing range', 'vwap', 'Volume vs sma20', 'RS', 'Market', 'Yahoo'])
        self.missing = []
        self.rabbit = rabbitmq.rabbitmq()
        self.loop = asyncio.get_event_loop()

    def get_osebx_tickers(self):
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
            stocklist = pd.concat([stocklist,df2], ignore_index=True)
        stocklist['Symbol'] = stocklist["Symbol"].str.lower()+".ol"
        stocklist = stocklist.sort_values('Name')
        self.stocklist = stocklist

    def get_osebx_rsi(self):
        try:
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
            self.indexRSI = indexRSI
        except:
            self.indexRSI = 50


    def create_chart(self,stock=None, df=pd.DataFrame()):
        today = dt.datetime.now()
        start = today - dt.timedelta(days=365)
        filename = "images/" + stock.lower().replace(".","_")+".jpg"
        
        if df.empty:
            stock_db = "ticker_" + stock.lower().replace(".","_")
            df = pd.read_sql(stock_db,engine, index_col="Date", parse_dates={"Date": {"format": "%d/%m/%y"}})
        df["SMA_50"]=round(df["Adj Close"].rolling(window=50).mean(),2)
        df = df.loc[df.index > start]
        pivots =[]
        dates = []
        counter=0
        lastPivot=0
        Range=[0,0,0,0,0,0,0,0,0,0]
        dateRange=[0,0,0,0,0,0,0,0,0,0]
        for i in df.index:
            currentMax=max(Range, default=0)
            value=df["High"][i].round(2)
            Range=Range[1:9]
            Range.append(value)
            dateRange=dateRange[1:9]
            dateRange.append(i)
            if currentMax==max(Range, default=0):
                counter+=1
            else:
                counter=0
            if counter==5:
                lastPivot=currentMax
                dateloc=Range.index(lastPivot)
                lastDate=dateRange[dateloc]
                pivots.append(lastPivot) 
                dates.append(lastDate)
        timed=dt.timedelta(days=30)
        pivotlines = []
        for index in range(len(pivots)):
            pivotline = [(dates[index],pivots[index]), (dates[index]+timed, pivots[index])]
            if dates[index] + timed > df.index[-1]:
                pivotline = [(dates[index],pivots[index]), (df.index[-1], pivots[index])]
            pivotlines.append(pivotline)
        mean = np.mean(df['High'] - df['Low'])
        hlines = []
        hline_type = []
        for i in range(2, df.shape[0] -2):
            if df['Low'].iloc[i] < df['Low'].iloc[i - 1] and df['Low'].iloc[i] < df['Low'].iloc[i + 1] and df['Low'].iloc[i + 1] < df['Low'].iloc[i + 2] and df['Low'].iloc[i - 1] < df['Low'].iloc[i - 2]:
                level = df['Low'].iloc[i].round(2)
                if np.sum([abs(level - y )< mean for y in hlines]) == 0 and level > (df['Low'].iloc[-1] - (mean*3)) and level < (df['Adj Close'].iloc[-1]):
                    hlines.append((level))
                    hline_type.append("green")
            if df['High'].iloc[i] > df['High'].iloc[i - 1] and df['High'].iloc[i] > df['High'].iloc[i + 1] and df['High'].iloc[i + 1] > df['High'].iloc[i + 2] and df['High'].iloc[i - 1] > df['High'].iloc[i - 2]:
                level = df['High'].iloc[i].round(2)
                if np.sum([abs(level - y )< mean for y in hlines]) == 0 and level < (df['High'].iloc[-1] + (mean*3)) and level > (df['Adj Close'].iloc[-1]):
                    hlines.append((level))
                    hline_type.append("red")
        kwargs = dict(type='candle',volume=True,figratio=(16,8),figscale=1.8, tight_layout=True,hlines=dict(hlines=hlines, linestyle='dotted',colors=hline_type))
        apdict = mpf.make_addplot(df['SMA_50'])
        mpf.plot(df,**kwargs,style='yahoo',addplot=apdict, alines=dict(alines=pivotlines), savefig=filename)

    async def database(self, engine=engine):
        self.get_osebx_tickers()
        self.get_osebx_rsi()
        update_tasks = []
        for i in self.stocklist.index:
            stock = str(self.stocklist["Symbol"][i])
            update_tasks.append(asyncio.create_task(db_updater(stock, engine, rabbit=self.rabbit,logger=logger)))
        try:
            result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*update_tasks), timeout=600))
        except asyncio.TimeoutError:
            print("timed out of gather")
            cancel = 0
            for task in update_tasks:
                if not task.done():
                    cancel += 1
                    task.cancel()
            print(f"{cancel} tasks canceled")
            return
        for task_result in result:
            if isinstance(task_result, Exception):
                print(f"An exception occurred in one of the tasks: {task_result}")
        # start investtech gather here?

    async def fullscan(self):
        tasks = [self.scan(i) for i in self.stocklist.index]
        try:
            result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*tasks), timeout=3600))
        except asyncio.TimeoutError:
            print("timed out of gather")
            cancel = 0
            for task in tasks:
                if not task.done():
                    task.cancel()
                    cancel += 1
            print(f"{cancel} tasks canceled")
            return
        for task_result in result:
            if isinstance(task_result, Exception):
                print(f"An exception occurred in one of the tasks: {task_result}")
        


    async def scan(self, i):
            x = i
            notfound=True
            watchlist = False
            # get from stocklist when doing full scan
            try:
                stock = self.stocklist["Symbol"][i]
                market = self.stocklist["Market"][i]
                stockname = self.stocklist["Name"][i]
            except: #if called from watchlist
                stock = i['ticker']
                market = "placeholder"
                stockname = i['name']
                watchlist = True
            stock_db = "ticker_" + stock.lower().replace(".","_")
            filename = stock.lower().replace(".","_")+".jpg"
            filename_investtech = stock.lower().replace(".","_")+"-investtech.png"
            df = pd.read_sql(stock_db,engine, index_col="Date", parse_dates={"Date": {"format": "%d/%m/%y"}})
            if len(df) < 200 and watchlist == False:
                logger.warning(f"Under 200 days of data on {stockname}, skipping")
                return
            df['Volume_SMA_20'] = round(df['Volume'].rolling(window=20).mean(),2)
            ap = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1])/3
            vwap = round((ap * df['Volume'].iloc[-1])/1000000,2)
            if vwap < 1 and watchlist == False:
                logger.info(f"Too low volume on {stockname}, skipping")
                return
            volumeChange = round(((df['Volume'].iloc[-1] / df['Volume_SMA_20'].iloc[-1]))*100,2)
            priceChange = round(((df['Adj Close'].iloc[-1] / df['Adj Close'].iloc[-2]) -1)*100,2)
            if df['High'].iloc[-1] == df['Low'].iloc[-1]:
                closingRange = 50
            else:
                closingRange = round(((df['Close'].iloc[-1]-df['Low'].iloc[-1])/(df['High'].iloc[-1]-df["Low"].iloc[-1]))*100,2)
            trend = trend_template(df)
            #################3 part 2
            for tickers in self.tickermap:
                if stock.lower() == tickers['ticker']:
                    mapped_ticker = tickers
                    notfound=False
            if notfound:
                mapped_ticker = None
                self.missing.append(x)
                logger.warning(f"{stockname}, {stock}, not in tickermap!")
                return
            # await asyncio.sleep(5)
            self.create_chart(stock=stock, df=df)
            df['RSI'] = ta.momentum.rsi(df["Close"], window=6)
            rs = (df['RSI'].iloc[-1] / self.indexRSI) * 100
            macd_out = macd(df)
            new_high = new_20day_high(df)
            bollinger_band_out = bollinger_band(df)
            pivotPoint = pivot_point(df)
            trailing = trailing_stop(df)
            export_dict = {'Stock': '=hyperlink(\"https://finance.yahoo.com/chart/'+stock+'\",\"'+stockname+'\")', 'Ticker': stock, 'Adj Close' : df["Adj Close"].iloc[-1].round(2), 'Change': str(priceChange)+"%", 'Closing range': closingRange, \
                        'vwap': vwap, 'Volume vs sma20': str(volumeChange)+"%", 'RS': rs.round(2), 'Market': market, 'Yahoo': "https://finance.yahoo.com/chart/"+stock, \
                        'PivotPoint': False, 'MACD': False, '20Day high': False, 'Minervini': trend}
            #################################################################### discord embed ###############################
            
            if rs >= 100:
                color=discord.Color.green()
            elif rs >= 50:
                color=discord.Color.orange()
            else:
                color=discord.Color.red()
            if "investechID" in mapped_ticker:
                header,body= await self.rabbit.get_investtech(mapped_ticker)
            else:
                header = "header"
                body = "Body"
            # header,body = get_text(mapped_ticker)
            img = discord.File("images/"+filename, filename=filename)
            mbd=discord.Embed(title=stockname, url="https://finance.yahoo.com/chart/"+stock, description=body,color=color)
            mbd.set_image(url="attachment://"+filename)
            try:
                mbd2=discord.Embed(url="https://finance.yahoo.com/chart/"+stock)
                img_investtech = discord.File("images/"+filename_investtech, filename=filename_investtech)
                mbd2.set_image(url="attachment://"+filename_investtech)
            except Exception as e:
                print(e)
            mbd.set_author(name=header, url=mapped_ticker['investech'])
            mbd.add_field(name="price", value=str(df["Adj Close"].iloc[-1].round(1))+"kr\n"+str(priceChange)+"%")
            mbd.add_field(name="Closing Range", value=str(closingRange)+"%")
            mbd.add_field(name="vwap", value=str(vwap)+"mNOK")
            mbd.add_field(name="Volume sma20", value=str(volumeChange)+"%")
            mbd.add_field(name="RS", value=rs.round(2))
            if pivotPoint != None:
                export_dict['PivotPoint'] = True
                mbd.add_field(name="Pivot point breached", value=pivotPoint)
            if macd_out != None:
                if "climb" in macd_out:
                    export_dict['MACD'] = "Climb"
                    mbd.add_field(name="MACD", value=macd_out)
                elif "decline" in macd_out:
                    export_dict['MACD'] = "Decline"
                    mbd.add_field(name="MACD", value=macd_out)
            if new_high != None:
                export_dict['20Day high'] = True
                mbd.add_field(name="20-Day High", value=new_high)
            if bollinger_band_out != None:
                mbd.add_field(name="Bollinger Band", value=bollinger_band_out)
            if trailing != None:
                export_dict['Trailing'] = True
                mbd.add_field(name="Trailing stop", value=trailing)
            mbd.set_footer(text=market)
            try:
                self.result['result'].append({"stock":stock,"market": market, "embed": [mbd,mbd2], "image": [img,img_investtech], "image investtech": img_investtech, "trend": trend})
            except Exception as e:
                print(e)
                self.result['result'].append({"stock":stock,"market": market, "embed": [mbd], "image": [img], "trend": trend})
            new_row = pd.Series(export_dict)
            self.exportdf = pd.concat([self.exportdf, new_row.to_frame().T], ignore_index=True)
            # await self.rabbit.disconnect()


#main is striclty used as local debugging. As this file is called by other files
async def main():
    testing = MarketScreener()
    await testing.rabbit.connect()
    await testing.database() 
    await testing.fullscan()
    global finished_result
    finished_result = sorted(testing.result['result'], key=lambda x: x['stock'])

    @bot.event
    async def on_ready():
        global finished_result
        channel = bot.get_channel(channel_id)
        logger.info("Bot is ready")
        embeds = []
        embeds2 = []
        images = []
        images2 = []
        for i in finished_result:
            if i['trend'] >= 7 and "image investtech" in i:
                embeds2.extend(i['embed'])
                images2.extend(i['image'])
            elif i['trend'] >= 7 and "image investtech" not in i:
                embeds.append(i['embed'])
                images.append(i['image'])
        logger.info(embeds)
        length=6
        for i in range(0, len(embeds2), length):
            x=i
            emb = embeds2[x:x+length]
            im = images2[x:x+length]
            await channel.send(embeds=emb, files=im, silent=True)
        if len(embeds) > 0:
            for i in range(0, len(embeds), length):
                x=i
                emb = embeds[x:x+length]
                im = images[x:x+length]
                await channel.send(embeds=emb, files=im, silent=True)
        logger.info("done sending")
        await asyncio.sleep(30)
        await bot.close()

    await bot.start(discord_token)
    await testing.rabbit.disconnect()
    print("ALL DONE GOING TO BED")
if __name__ == "__main__":
    logger = settings.logging.getLogger("bot")
    logger.info("test")
    asyncio.run(main())