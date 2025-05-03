import pandas as pd
from bs4 import BeautifulSoup
import rabbitmq_client as rabbitmq
import asyncio
import numpy as np
import mplfinance as mpf
import discord
import requests

import ta
from io import StringIO, BytesIO
import datetime as dt

import settings
import localdb
from localdb import portfolio_report, scan_report, ticker_db, tickermap, userdata
from screener.indicators import macd,new_20day_high,bollinger_band,trend_template,pivot_point,trailing_stop

logger = settings.logger
# setup
today = dt.date.today()
today = str(today)
engine = settings.engine

class MarketScreener:
    def __init__(self):
        # with open('data/map.json','r') as mapfile:
        #     data = json.load(mapfile)
        #     self.tickermap = data['stocks']
        self.tickermapdb = tickermap.TickerMap()
        self.result = {"result": [], 'portfolio': [],"metadata": {"time": None}}
        self.indexRSI = None
        self.stocklist = pd.DataFrame(columns = ['Name', 'Symbol', 'Market'])
        self.exportdf = pd.DataFrame(columns = ['Stock', 'Ticker', 'Close', 'Change', 'Closing range', 'vwap', 'Volume vs sma20', 'RS', 'Market', 'Yahoo'])
        self.json_response = None
        self.json_portfolio = None
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


    def create_chart(self,stock=None, df=pd.DataFrame(), save=True):
        today = dt.datetime.now()
        start = today - dt.timedelta(days=365)
        filename = "images/" + stock.lower().replace(".","_")+".jpg"
        
        if df.empty:
            stock_db = "ticker_" + stock.lower().replace(".","_")
            df = pd.read_sql(stock_db,engine, index_col="Date", parse_dates={"Date": {"format": "%d/%m/%y"}})
        df["SMA_50"]=round(df["Close"].rolling(window=50).mean(),2)
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
                if np.sum([abs(level - y )< mean for y in hlines]) == 0 and level > (df['Low'].iloc[-1] - (mean*3)) and level < (df['Close'].iloc[-1]):
                    hlines.append((level))
                    hline_type.append("green")
            if df['High'].iloc[i] > df['High'].iloc[i - 1] and df['High'].iloc[i] > df['High'].iloc[i + 1] and df['High'].iloc[i + 1] > df['High'].iloc[i + 2] and df['High'].iloc[i - 1] > df['High'].iloc[i - 2]:
                level = df['High'].iloc[i].round(2)
                if np.sum([abs(level - y )< mean for y in hlines]) == 0 and level < (df['High'].iloc[-1] + (mean*3)) and level > (df['Close'].iloc[-1]):
                    hlines.append((level))
                    hline_type.append("red")
        kwargs = dict(type='candle',volume=True,figratio=(16,8),figscale=1.8, tight_layout=True,hlines=dict(hlines=hlines, linestyle='dotted',colors=hline_type))
        apdict = mpf.make_addplot(df['SMA_50'])
        if save:
            mpf.plot(df,**kwargs,style='yahoo',addplot=apdict, alines=dict(alines=pivotlines), savefig=filename)
        else:
            image_bytes = BytesIO()
            mpf.plot(df,**kwargs,style='yahoo',addplot=apdict, alines=dict(alines=pivotlines), show_nontrading=True, savefig=image_bytes)
            image_bytes.seek(0)
            return image_bytes.getvalue()

    async def database(self, engine=engine):
        self.get_osebx_tickers()
        self.get_osebx_rsi()
        update_tasks = []
        for i in self.stocklist.index:
            stock = str(self.stocklist["Symbol"][i])
            update_tasks.append(asyncio.create_task(ticker_db.db_updater(stock, engine, rabbit=self.rabbit,logger=logger)))
        try:
            result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*update_tasks), timeout=600))
        except asyncio.TimeoutError:
            logger.warning("timed out of gather")
            cancel = 0
            for task in update_tasks:
                if not task.done():
                    cancel += 1
                    task.cancel()
            logger.warning(f"{cancel} tasks canceled")
            return
        for task_result in result:
            if isinstance(task_result, Exception):
                logger.warning(f"An exception occurred in one of the tasks: {task_result}")
        # start investtech gather here?

    async def fullscan(self):
        tasks = [self.scan(i) for i in self.stocklist.index]
        try:
            result = await asyncio.shield(asyncio.wait_for(asyncio.gather(*tasks), timeout=3600))
        except asyncio.TimeoutError:
            logger.warning("timed out of gather")
            cancel = 0
            for task in tasks:
                if not task.done():
                    task.cancel()
                    cancel += 1
            logger.warning(f"{cancel} tasks canceled")
            return
        for task_result in result:
            if isinstance(task_result, Exception):
                logger.warning(f"An exception occurred in one of the tasks: {task_result}")
        

    #json response, with header and body. fields: ema 8, ema21, sma50, trailing stop, volume sma
    async def portfolio_scan(self, i, return_text=False):
            if self.indexRSI == None:
                self.get_osebx_rsi()
            today = dt.date.today()
            stock = i['ticker']
            market = i['market']
            stockname = i['name']
            watchlist = True
            mapped_ticker = self.tickermapdb.get_map_data(ticker=stock)
            stock_db = "ticker_" + stock.lower().replace(".","_")
            filename = stock.lower().replace(".","_")+".jpg"
            df = pd.read_sql(stock_db,engine, index_col="Date", parse_dates={"Date": {"format": "%d/%m/%y"}})
            latest_date = df.index.max()
            latest_date_str = latest_date.strftime('%d-%m-%Y')
            emas = [8,21]
            smas = [50]
            fields = []
            score = 0
            price = df['Close'].iloc[-1]
            month_check = [1,3]
            if price > 10:
                price = round(price, 2)
            else:
                price = round(price, 3)
            df['Volume_SMA_20'] = round(df['Volume'].rolling(window=20).mean(),2)
            volumeChange = round(((df['Volume'].iloc[-1] / df['Volume_SMA_20'].iloc[-1]))*100,2)
            priceChange = round(((df['Close'].iloc[-1] / df['Close'].iloc[-2]) -1)*100,2)
            trailing = trailing_stop(df)
            #set up emojis
            def check_trend(price, value):
                '''
                check if there is inclining or declining trend

                :params price: referance value
                :value: current value to check trend
                '''
                def is_invalid(value):
                    return value is None or value == "---" or (isinstance(value, float) and np.isnan(value))
                if is_invalid(price) or is_invalid(value):
                    logger.warning(f"price: {price}, value: {value}")
                    icon = ""
                    return icon
                logger.debug(f"{value} is valid")
                icon = ":chart_with_upwards_trend:" if value > price else ":chart_with_downwards_trend:"
                return icon
            def check_pass(reference_value, current_value):
                def is_invalid(value):
                    return value is None or value == "---" or (isinstance(value, float) and np.isnan(value))
                if is_invalid(reference_value) or is_invalid(current_value):
                    logger.warning(f"reference value: {reference_value}, current_value: {current_value}")
                    icon = ""
                    return icon
                if isinstance(reference_value, str):
                    icon = ":white_check_mark:" if "Uptrend" in reference_value else ":red_circle:"
                    return icon
                icon = ":white_check_mark:" if reference_value < current_value else ":red_circle:"
                return icon
            for ema in emas:
                df[f"EMA_{ema}"]=round(df["Close"].ewm(span=ema,min_periods=ema).mean(),2)
                emavalue = df[f"EMA_{ema}"].iloc[-1]
                if np.isnan(emavalue):
                    emavalue = "---"
                fields.append({'title': f"EMA {ema} {check_pass(emavalue, price)}", "field": emavalue})
                if price < df[f'EMA_{ema}'].iloc[-1]:
                    score +=1
            for sma in smas:
                df[f"SMA_{sma}"]=round(df['Close'].rolling(window=sma).mean(),2)
                smavalue = df[f"SMA_{sma}"].iloc[-1]
                if np.isnan(smavalue):
                    smavalue = "---"
                fields.append({'title': f"SMA {sma} {check_pass(smavalue, price)}", "field": smavalue})
                if price < df[f'SMA_{sma}'].iloc[-1]:
                    score +=1
            for month in month_check:
                df_backtrack = month*21
                if len(df) <= df_backtrack:
                    month_change = "---"
                    month_price = "---"
                else:
                    month_price = df['Close'].iloc[-df_backtrack]
                    month_change = round(((price/month_price)-1) * 100,2)
                fields.append({'title': f'{month} change {check_trend(month_price, value=price)}', 'field': f'{month_change}%'})
            try:
                if price < trailing:
                    score+=1
            except:
                if trailing == None:
                    logger.warning(f"Trailing for {stock} is {trailing} setting it to \"---\"")
                    trailing = "---"
                    score+=1
                elif "Downtrend" in trailing:
                    score +=1

            header = f"{latest_date_str} - {stockname} - {stock}: {price}kr  {priceChange}%"
            body = f"Daily portfolio report \nchecking against indicators. see fields"
            self.json_portfolio = {'ticker': stock, 'name': f"{stockname} {check_trend(0,priceChange)}", 'header': header, 'header url': mapped_ticker['nordnet'], 'body': body, 'fields': [ \
                                    {'title': f'Volume SMA20 {check_trend(100, volumeChange)}', 'field': str(volumeChange)+'%'}, {'title': f'Trailing Stop {check_pass(trailing, price)}', 'field': trailing}],\
                                    'yahoo': "https://finance.yahoo.com/chart/"+stock, 'score': score}
            if "icon" in mapped_ticker:
                self.json_portfolio['icon'] = mapped_ticker['icon']
            for field in fields:
                self.json_portfolio['fields'].append(field)
            logger.info(self.json_portfolio)
            if return_text:
                return self.json_portfolio
    async def scan(self, i, return_text=False, minerviniscan=False):
            x = i
            notfound=False
            watchlist = False
            if self.indexRSI == None:
                self.get_osebx_rsi()
            # get from stocklist when doing full scan
            if type(i) == int:
                    stock = self.stocklist["Symbol"][i]
                    market = self.stocklist["Market"][i]
                    stockname = self.stocklist["Name"][i]

            else:
                try:
                    stock = i["Symbol"]
                    market = i["Market"]
                    stockname = i["Name"]
                except:
                    stock = i['ticker']
                    market = i['market'] 
                    stockname = i['name']
                    watchlist = True
            stock_db = "ticker_" + stock.lower().replace(".","_")
            filename = stock.lower().replace(".","_")+".jpg"
            filename_investtech = stock.lower().replace(".","_")+"-investtech.png"
            df = pd.read_sql(stock_db,engine, index_col="Date", parse_dates={"Date": {"format": "%d/%m/%y"}})
            price = df['Close'].iloc[-1]
            if price > 10:
                price = round(price, 2)
            else:
                price = round(price, 3)
            if len(df) < 200 and watchlist == False:
                logger.warning(f"Under 200 days of data on {stock} - {stockname}, skipping")
                return
            df['Volume_SMA_20'] = round(df['Volume'].rolling(window=20).mean(),2)
            ap = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1])/3
            vwap = round((ap * df['Volume'].iloc[-1])/1000000,2)
            if vwap < 1 and watchlist == False:
                logger.info(f"Too low volume on {stockname}, skipping")
                return
            volumeChange = round(((df['Volume'].iloc[-1] / df['Volume_SMA_20'].iloc[-1]))*100,2)
            priceChange = round(((df['Close'].iloc[-1] / df['Close'].iloc[-2]) -1)*100,2)
            if df['High'].iloc[-1] == df['Low'].iloc[-1]:
                closingRange = 50
            else:
                closingRange = round(((df['Close'].iloc[-1]-df['Low'].iloc[-1])/(df['High'].iloc[-1]-df["Low"].iloc[-1]))*100,2)
            trend = trend_template(df)
            if minerviniscan == True and trend > 7:
                logger.info(f"{stock} failed minervini scan")
                return
            #################3 part 2
            # for tickers in self.tickermap:
            #     if stock.lower() == tickers['ticker']:
            #         mapped_ticker = tickers
            #         notfound=False
            mapped_ticker = self.tickermapdb.get_map_data(ticker=stock)
            if mapped_ticker == None:
                notfound = True
            if notfound:
                mapped_ticker = None
                self.missing.append(x)
                logger.warning(f"{stockname}, {stock}, not in tickermap!")
                return
            # await asyncio.sleep(5)
            if return_text:
                image = self.create_chart(stock=stock, df=df, save=False)
            else:
                self.create_chart(stock=stock, df=df)
            df['RSI'] = ta.momentum.rsi(df["Close"], window=6)
            rs = (df['RSI'].iloc[-1] / self.indexRSI) * 100
            macd_out = macd(df)
            new_high = new_20day_high(df)
            bollinger_band_out = bollinger_band(df)
            pivotPoint = pivot_point(df)
            trailing = trailing_stop(df)
            if "investechID" in mapped_ticker and return_text == False:
                header,body= await self.rabbit.get_investtech(mapped_ticker)
            else:
                header = "header"
                body = "Body"
            gsheet_dict = {'Stock': '=hyperlink(\"https://finance.yahoo.com/chart/'+stock+'\",\"'+stockname+'\")', 'Ticker': stock, 'Close' : df["Close"].iloc[-1].round(2), 'Change': str(priceChange)+"%", 'Closing range': closingRange, \
                        'vwap': vwap, 'Volume vs sma20': str(volumeChange)+"%", 'RS': rs.round(2), 'Market': market, 'Yahoo': "https://finance.yahoo.com/chart/"+stock, \
                        'PivotPoint': False, 'MACD': False, '20Day high': False, 'Minervini': trend}
            self.json_response = {'ticker': stock, 'name': stockname, 'rs': rs, 'header': header,'header url': mapped_ticker['nordnet'], 'body': body, 'fields': [ {'title': 'Close', 'field': str(price)+"kr\n"+str(priceChange)+"%"}, {'title': 'Closing Range', 'field': str(closingRange)}, {'title': 'vwap', 'field': str(vwap)},\
                        {'title': 'Volume SMA20', 'field': str(volumeChange)+'%'}, {'title': 'RS', 'field': str(rs.round(2))}], \
                        'market': market, 'yahoo': "https://finance.yahoo.com/chart/"+stock, \
                        'minervini': trend, 'vwap': vwap, 'color': None}
            #################################################################### discord embed ###############################
            if pivotPoint != None:
                gsheet_dict['PivotPoint'] = True
                self.json_response['fields'].append({'title': 'pivot point :white_check_mark:', 'field': pivotPoint})
                self.json_response['color'] = 'blue'
                self.json_response['name'] = f"{stockname} :bell:"
            if macd_out != None:
                if "climb" in macd_out:
                    gsheet_dict['MACD'] = "Climb"
                    self.json_response['fields'].append({'title': 'macd :chart_with_upwards_trend:', 'field': macd_out})
                    self.json_response['color'] = 'blue'
                    self.json_response['name'] = f"{stockname} :bell:"
                elif "decline" in macd_out:
                    gsheet_dict['MACD'] = "Decline"
                    self.json_response['fields'].append({'title': 'macd :chart_with_downwards_trend:', 'field': macd_out})
            if new_high != None:
                gsheet_dict['20Day high'] = True
                self.json_response['fields'].append({'title': '20day high :white_check_mark:', 'field': new_high})
                self.json_response['name'] = f"{stockname} :bell:"
                self.json_response['color'] = 'blue'
            if bollinger_band_out != None:
                self.json_response['fields'].append({'title': 'bollinger', 'field': bollinger_band_out})
            if trailing != None:
                gsheet_dict['Trailing'] = True
                if isinstance(trailing, str) and "Uptrend" in trailing:
                    self.json_response['fields'].append({'title': 'trailing stop :white_check_mark:', 'field': trailing})
                    self.json_response['color'] = 'blue'
                    self.json_response['name'] = f"{stockname} :bell:"
                elif isinstance(trailing, str) and "Downtrend" in trailing:
                    self.json_response['fields'].append({'title': 'trailing stop :red_circle:', 'field': trailing})
                else:
                    self.json_response['fields'].append({'title': 'trailing stop', 'field': trailing})
            if "icon" in mapped_ticker:
                self.json_response['icon'] = mapped_ticker['icon']
            new_row = pd.Series(gsheet_dict)
            self.exportdf = pd.concat([self.exportdf, new_row.to_frame().T], ignore_index=True)
            if return_text:
                return self.json_response, image 
            # await self.rabbit.disconnect()
    async def create_embeds(self, image, investtech_image=None, json_data=None):
            # fetch data from 
            if json_data == None:
                json_data = self.json_response
            stock = json_data['ticker']
            stockname = json_data['name']
            header = json_data['header']
            header_url = json_data['header url']
            body = json_data['body']
            market = json_data['market']
            fields = json_data['fields']
            trend = json_data['minervini']
            url = json_data['yahoo']
            rs = json_data['rs']
            imagename = json_data['ticker'].replace('.','_')
            imageIO = BytesIO(image)
            color = discord.Color.blue() if json_data['color'] == "blue" else  discord.Color.green() if rs >= 100 else discord.Color.orange() if rs >= 50 else discord.Color.red()

            img = discord.File(imageIO, filename=imagename+'.png')
            mbd=discord.Embed(title=stockname, url=url, description=body,color=color)
            mbd.set_image(url="attachment://"+imagename+'.png')
            try:
                mbd.set_thumbnail(url=json_data['icon'])
            except Exception as e:
                logger.warning(e)
            try:
                mbd2=discord.Embed(url=url)
                investtech_imageIO = BytesIO(investtech_image)
                img_investtech = discord.File(investtech_imageIO, filename=imagename+'_investtech.png')
                mbd2.set_image(url="attachment://"+imagename+'_investtech.png')
            except Exception as e:
                logger.warning(e)
            mbd.set_author(name=header, url=header_url)
            for i in fields:
                mbd.add_field(name=i['title'], value=i['field'])
            mbd.set_footer(text=market)
            try:
                response_dict = {"stock":stock,"market": market, "embed": [mbd,mbd2], "image": [img,img_investtech], "image investtech": img_investtech, "trend": trend}
            except Exception as e:
                logger.warning(e)
                response_dict = {"stock":stock,"market": market, "embed": [mbd], "image": [img], "trend": trend}
            self.result['result'].append(response_dict)
            # return response_dict
    async def create_portfolio_embeds(self, json_data, image=None):
            logger.debug(json_data)
            stock = json_data['ticker']
            stockname = json_data['name']
            header = json_data['header']
            header_url = json_data['header url']
            body = json_data['body']
            fields = json_data['fields']
            url = json_data['yahoo']
            score = json_data['score']
            color = discord.Color.green() if score == 0 else discord.Color.orange() if score < 3 else discord.Color.red()
            mbd=discord.Embed(title=stockname, url=url, description=body,color=color)
            mbd.set_author(name=header, url=header_url)
            try:
                mbd.set_thumbnail(url=json_data['icon'])
            except Exception as e:
                logger.warning(e)
            for i in fields:
                mbd.add_field(name=i['title'], value=i['field'])
            response_dict = {"stock":stock, "embed": [mbd]}
            self.result['portfolio'].append(response_dict)



