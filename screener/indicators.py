import pandas as pd
import pandas_ta as ta
import numpy as np
from sqlalchemy import create_engine


def macd(df):
    '''
    Calculates MACD of yahoo dataframe, returns if MACD indicates change to climb or change to decline
    
    :params df: Dataframe fetched from yfinance
    :params return: string with info of incline or decline
    '''
    df.ta.macd(close='Close', fast=12, slow=26, signal=9, append=True)
    df["SMA_200"]=round(df['Close'].rolling(window=200).mean(),2)
    df["EMA_200"]=round(df["Close"].ewm(span=200,min_periods=200).mean())
    sma200 = df["SMA_200"].iloc[-1]
    sma200_20old = df["SMA_200"].iloc[-20]
    ema200 = df['EMA_200'].iloc[-1]
    if df['Close'].iloc[-1] > sma200 or df['Close'].iloc[-1] > ema200:
        df = df.tail(20)
        if df['MACDh_12_26_9'].iloc[-1] > 0 and df['MACDh_12_26_9'].iloc[-2] < 0 and df['MACD_12_26_9'].iloc[-1] < 0:
            return "started climbing! "+str(df['MACDh_12_26_9'].iloc[-1])
        elif df['MACDh_12_26_9'].iloc[-1] < 0 and df['MACDh_12_26_9'].iloc[-2] > 0 and df['MACD_12_26_9'].iloc[-1] > 0:
            return 'started declining '+str(df['MACDh_12_26_9'].iloc[-1])

def new_20day_high(df):
    '''
    Checks if latest day is a new high price of the last 20 says

    :params df: DataFrame from yfinance
    :params return: returns True if True
    '''
    tail = df.tail(20)
    high20 = tail['Close'].iloc[:-1].max()
    if tail['Close'].iloc[-1] > high20:
        return True

def bollinger_band(df):
    '''
    Checks if latest day is outside bolliger band

    :params df: DataFrame from yfinance
    :params return: String with info
    '''
    df['ma20'] = df.Close.rolling(20).mean()
    df['vol'] = df.Close.rolling(20).std()
    df['upper_bb'] = df.ma20 + (2 * df.vol)
    df['lower_bb'] = df.ma20 - (2* df.vol)
    df['rsi'] = ta.momentum.rsi(df.Close, window=6)
    
    conditions = [(df.rsi < 30) & (df.Close < df.lower_bb),
            (df.rsi > 70) & (df.Close > df.upper_bb)]
    choices = ['Buy', 'Sell']
    df['Signal'] = np.select(conditions,choices, default='')
    if df['Signal'].iloc[-1] == ("Sell" or "Buy"):
        return  "is outside Bollinger Band"

def trend_template(df):
    '''
    The minervini scan, checks if the stock fullfills the 7(of 8) rules of minervini

    :params df: Dataframe from yfinance
    :params return: Number of tests passed
    '''
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # df = pd.read_sql(stock_db,engine)
    tests_passed=0
    if df.empty:
        return None
    smaUsed=[50,150,200]
    for x in smaUsed:
        sma=x
        df["SMA_"+str(sma)]=round(df["Close"].rolling(window=sma).mean(),2)
    currentClose=df["Close"].iloc[-1]
    moving_average_50=df["SMA_50"].iloc[-1]
    moving_average_150=df["SMA_150"].iloc[-1]
    moving_average_200=df["SMA_200"].iloc[-1]
    low_of_52week=min(df["Close"][-260:])
    high_of_52week=max(df["Close"][-260:])

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
    '''
    Calculates pivots points on the DF and checks if current day breaches the pivot point

    :params df: DataFrame from yfinance
    :params return: returns last pivot point if price breaches
    '''
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
        df.loc[i, "Pivot"]=lastPivot
            
    if df['Close'].iloc[-1] > df['Pivot'].iloc[-1] and df['Close'].iloc[-2] < df['Pivot'].iloc[-2]:
        return  lastPivot

def trailing_stop(df, return_df = False):
    '''
    Calculates trailing stop for provided DataFrame. Can return dataframe with trailing stop columns

    :params df: DataFrame from yfinance
    :params return_df: if True, returns dataframe with extra columns
    :params return: returns trailing stop value, or dataframe
    '''
    if len(df) < 50:
        return
    pd.set_option('mode.chained_assignment', None)
    df.ta.atr(length=14, append=True)
    df.dropna()
    atr_multiplier = 3
    df['stop'] = None
    df['trend'] = 'Uptrend'
    if "Close" in df.columns:
        df.loc[df.index[0], "stop"] = df['Close'].iloc[0] - atr_multiplier * df['ATRr_14'].iloc[0]
    else:
        df.loc[df.index[0], "stop"] = df['Close'].iloc[0] - atr_multiplier * df['ATRr_14'].iloc[0]
    
    for i in df.index[1:]:
        previous_index = df.index[df.index.get_loc(i) -1]
        if "Close" in df.columns:
            current_price = df.loc[i, 'Close'] 
        else:
            current_price = df.loc[i, 'Close'] 
        previous_stop = df.loc[previous_index, 'stop'] 
        atr = df.loc[i, 'ATRr_14']
        current_trend = df.loc[previous_index, 'trend']

        if current_price < previous_stop and current_trend == "Uptrend":
            df.loc[i, 'trend'] = 'Downtrend'
            df.loc[i, 'stop'] = current_price + atr_multiplier * atr
            continue
        elif current_price > previous_stop and current_trend == "Downtrend":
            df.loc[i, 'trend'] = 'Uptrend'
            df.loc[i, 'stop'] = current_price - atr_multiplier * atr
            continue
        else:
            df.loc[i, 'trend'] = df.loc[previous_index, 'trend']
        
        if df.loc[i, 'trend'] == 'Uptrend':
            df.loc[i, 'stop'] = max(current_price - atr_multiplier * atr, previous_stop)
        if df.loc[i, 'trend'] == 'Downtrend':
            df.loc[i, 'stop'] = min(current_price + atr_multiplier * atr, previous_stop)
            
    df.dropna()
    if return_df:
        return df
    elif df['trend'].iloc[-1] != df['trend'].iloc[-2]:
        trend = df['trend'].iloc[-1]
        return f"Broke trailing stop. Now in: {trend}"
    else:
        return round(df['stop'].iloc[-1], 2)


def extended(df):
    """ function to check if the last price has extended to far from the moving averages.
        will be used to look for places to sell in to strength
        10% from 10 sma
        20% from 21 ema
        50% from 50 sma
        100% from 200sma
    """

    smaUsed=[10,50,200]
    for x in smaUsed:
        sma=x
        df["SMA_"+str(sma)]=round(df["Close"].rolling(window=sma).mean(),2)
    df["EMA_21"]=round(df["Close"].ewm(span=21,min_periods=22).mean())
    last_row = df.iloc[-1]
    adj_close = last_row['Close']
    sma_10 = last_row['SMA_10']
    sma_50 = last_row['SMA_50']
    sma_200 = last_row['SMA_200']
    ema_21 = last_row['EMA_21']

    # Calculate percentage differences
    diff_sma_10 = (adj_close - sma_10) / sma_10 * 100
    diff_sma_50 = (adj_close - sma_50) / sma_50 * 100
    diff_sma_200 = (adj_close - sma_200) / sma_200 * 100
    diff_ema_21 = (adj_close - ema_21) / ema_21 * 100

    # Initialize an empty list to store the result strings
    results = []

    # Check conditions and append appropriate strings
    if diff_sma_10 >= 10:
        results.append(f'{diff_sma_10:.2f}% above SMA_10')
    if diff_ema_21 >= 20:
        results.append(f'{diff_ema_21:.2f}% above EMA_21')
    if diff_sma_50 >= 50:
        results.append(f'{diff_sma_50:.2f}% above SMA_50')
    if diff_sma_200 >= 100:
        results.append(f'{diff_sma_200:.2f}% above SMA_200')

    # Join the results into a single string
    if len(results) > 0:
        result_string = ', '.join(results)
    else:
        result_string = "stock not extended"
    logger.info(result_string)
