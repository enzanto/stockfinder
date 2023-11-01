import pandas as pd
import pandas_ta as ta
import numpy as np
from sqlalchemy import create_engine

engine = create_engine('sqlite:///data/TEST_DB.db')

def macd(df):
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # try:
    #     df = pd.read_sql(stock_db,engine)
    #     if df.empty:
    #         return None
    df.ta.macd(close='Adj Close', fast=12, slow=26, signal=9, append=True)
    df["SMA_200"]=round(df['Adj Close'].rolling(window=200).mean(),2)
    df["EMA_200"]=round(df["Adj Close"].ewm(span=200,min_periods=200).mean())
    sma200 = df["SMA_200"].iloc[-1]
    sma200_20old = df["SMA_200"].iloc[-20]
    ema200 = df['EMA_200'].iloc[-1]
    if df['Adj Close'].iloc[-1] > sma200 or df['Adj Close'].iloc[-1] > ema200:
        df = df.tail(20)
        if df['MACDh_12_26_9'].iloc[-1] > 0 and df['MACDh_12_26_9'].iloc[-2] < 0 and df['MACD_12_26_9'].iloc[-1] < 0:
            return "started climbing! "+str(df['MACDh_12_26_9'].iloc[-1])
        elif df['MACDh_12_26_9'].iloc[-1] < 0 and df['MACDh_12_26_9'].iloc[-2] > 0 and df['MACD_12_26_9'].iloc[-1] > 0:
            return 'started declining '+str(df['MACDh_12_26_9'].iloc[-1])
    # except:
    #     print('no info on '+stock)
    #     print("---------------------------------")
    #     print("")

def new_20day_high(df):
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # try:
    #     df = pd.read_sql(stock_db,engine)
    #     if df.empty:
    #         return None
    df["SMA_200"]=round(df["Adj Close"].rolling(window=200).mean(),2)
    moving_average_200=df["SMA_200"].iloc[-1]
    try:
        moving_average_200_20past=df['SMA_200'].iloc[-20]
    except:
        moving_average_200_20past=0
    tail = df.tail(20)
    high20 = tail['Adj Close'].iloc[:-1].max()
    if tail['Adj Close'].iloc[-1] > high20:# and tail['Adj Close'].iloc[-2] < high20: #and moving_average_200 > moving_average_200_20past:
        return True
        # print(stock+' is a new 20 day max')
        # print('https://finance.yahoo.com/chart/'+stock)
    # except:
    #     print('no data on '+stock) 
    #     print("---------------------------------")
    #     print("")

def bollinger_band(df):
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # df = pd.read_sql(stock_db,engine)
    # if df.empty:
    #     return None
    df['ma20'] = df.Close.rolling(20).mean()
    df['vol'] = df.Close.rolling(20).std()
    df['upper_bb'] = df.ma20 + (2 * df.vol)
    df['lower_bb'] = df.ma20 - (2* df.vol)
    df['rsi'] = ta.momentum.rsi(df.Close, window=6)
    
    conditions = [(df.rsi < 30) & (df.Close < df.lower_bb),
            (df.rsi > 70) & (df.Close > df.upper_bb)]
    choices = ['Buy', 'Sell']
    df['Signal'] = np.select(conditions,choices)
    if df['Signal'].iloc[-1] == ("Sell" or "Buy"):
        #print(df['Signal'].iloc[-1])
        return  "is outside Bollinger Band"
        # print('https://finance.yahoo.com/chart/'+stock)

def trend_template(df):
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # df = pd.read_sql(stock_db,engine)
    tests_passed=0
    if df.empty:
        print("empty dataframe passed to trend template")
        return None
    smaUsed=[50,150,200]
    for x in smaUsed:
        sma=x
        df["SMA_"+str(sma)]=round(df["Adj Close"].rolling(window=sma).mean(),2)
    # print(df)
    currentClose=df["Adj Close"].iloc[-1]
    moving_average_50=df["SMA_50"].iloc[-1]
    moving_average_150=df["SMA_150"].iloc[-1]
    moving_average_200=df["SMA_200"].iloc[-1]
    low_of_52week=min(df["Adj Close"][-260:])
    high_of_52week=max(df["Adj Close"][-260:])

    try:
        moving_average_200_20past=df["SMA_200"].iloc[-20]
    except Exception:
        moving_average_200_20past=0
    #Condition 1: Current Price > 150 SMA and > 200 SMA
    if(currentClose>moving_average_150 and currentClose > moving_average_200):
        cond_1=True
        tests_passed += 1
    else:
        cond_1=False
    #Condition 2: 150 SMA and > 200 SMA
    if(moving_average_150>moving_average_200):
        cond_2=True
        tests_passed += 1
    else:
        cond_2=False
    #Condition 3: 200 SMA trending up for at least 1 month (ideally 4-5 months)
    if(moving_average_150>moving_average_200_20past):
        cond_3=True
        tests_passed += 1
    else:
        cond_3=False
    #Condition 4: 50 SMA> 150 SMA and 50 SMA> 200 SMA
    if(moving_average_50>moving_average_150 and moving_average_50> moving_average_200):
        cond_4=True
        tests_passed += 1
    else:
        cond_4=False
    #Condition 5: Current Price > 50 SMA
    if(currentClose>moving_average_50):
        cond_5=True
        tests_passed += 1
    else:
        cond_5=False
    #Condition 6: Current Price is at least 30% above 52 week low (Many of the best are up 100-300% before coming out of consolidation)
    if(currentClose>(1.3*low_of_52week)):
        cond_6=True
        tests_passed += 1
    else:
        cond_6=False
    #Condition 7: Current Price is within 25% of 52 week high
    if(currentClose>(0.75*high_of_52week)):
        cond_7=True
        tests_passed += 1
    else:
        cond_7=False
    #Condition 8: IBD RS rating >70 and the higher the better
    # if(RS_Rating > 100):
    #     cond_8=True
    # else:
    #     cond_8=False
    # if(cond_1 and cond_2 and cond_3 and cond_4 and cond_5 and cond_6 and cond_7):# and cond_8):
    #     return "Passed Mark Minervis Trend Template"
    return tests_passed

def pivot_point(df):
    #stock = stocklist["Symbol"][i]+".ol"
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # df = pd.read_sql(stock_db, engine, index_col="Date")
    # if df.empty:
    #     return None
    pd.set_option('mode.chained_assignment', None)

    df["Pivot"] = np.nan
    pivots= []
    dates = []
    # index = []
    counter = 0
    lastPivot = 0

    Range=[0,0,0,0,0,0,0,0,0,0]
    # indexRange=[0,0,0,0,0,0,0,0,0,0]
    dateRange=[0,0,0,0,0,0,0,0,0,0]

    for i in df.index:
        currentMax = max(Range,default=0)
        value = df["High"][i].round(1)
        # date = df["Date"][i]
        Range=Range[1:9]
        Range.append(value)
        # indexRange = indexRange[1:9]
        # indexRange.append(i)
        dateRange=dateRange[1:9]
        dateRange.append(i)


        if currentMax == max(Range, default=0):
            counter+=1
        else:
            counter=0
        if counter==5:
            lastPivot=currentMax
            dateLoc=Range.index(lastPivot)
            # lastIndex=indexRange[indexloc]
            lastDate=dateRange[dateLoc]
            pivots.append(lastPivot)
            # index.append(lastIndex)
            dates.append(lastDate)
        df["Pivot"][i]=lastPivot
            
    if df['High'].iloc[-1] > df['Pivot'].iloc[-1] and df['Adj Close'].iloc[-2] < df['Pivot'].iloc[-2]:
        return  lastPivot

def trailing_stop(df, return_df = False):
    if len(df) < 50:
        return
    pd.set_option('mode.chained_assignment', None)
    df.ta.atr(length=14, append=True)
    df.dropna()
    atr_multiplier = 3
    df['stop'] = None
    df['trend'] = 'Uptrend'
    if "Adj Close" in df.columns:
        df['stop'].iloc[0] = df['Adj Close'].iloc[0] - atr_multiplier * df['ATRr_14'].iloc[0]
    else:
        df['stop'].iloc[0] = df['Close'].iloc[0] - atr_multiplier * df['ATRr_14'].iloc[0]
    
    for i in range(1, len(df)):
        if "Adj Close" in df.columns:
            current_price = df['Adj Close'].iloc[i]
        else:
            current_price = df['Close'].iloc[i]
        previous_stop = df['stop'].iloc[i-1]
        atr = df['ATRr_14'].iloc[i]
        current_trend = df["trend"].iloc[i-1]

        if current_price < previous_stop and current_trend == "Uptrend":
            df['trend'].iloc[i] = 'Downtrend'
            df['stop'].iloc[i] = current_price + atr_multiplier * atr
            continue
        elif current_price > previous_stop and current_trend == "Downtrend":
            df['trend'].iloc[i] = 'Uptrend'
            df['stop'].iloc[i] = current_price - atr_multiplier * atr
            continue
        else:
            df['trend'].iloc[i] = df['trend'].iloc[i-1]
        
        if df['trend'].iloc[i] == 'Uptrend':
            df['stop'].iloc[i] = max(current_price - atr_multiplier * atr, previous_stop)
        if df['trend'].iloc[i] == 'Downtrend':
            df['stop'].iloc[i] = min(current_price + atr_multiplier * atr, previous_stop)
            
    df.dropna()
    if return_df:
        return df
    elif df['trend'].iloc[-1] != df['trend'].iloc[-2]:
        trend = df['trend'].iloc[-1]
        return f"Broke trailing stop. Now in: {trend}"
    else:
        return round(df['stop'].iloc[-1], 2)