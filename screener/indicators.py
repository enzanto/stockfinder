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
    df['rsi'] = ta.momentum.rsi(df.Close, window=6) # type: ignore
    
    conditions = [(df.rsi < 30) & (df.Close < df.lower_bb),
            (df.rsi > 70) & (df.Close > df.upper_bb)]
    choices = ['Buy', 'Sell']
    df['Signal'] = np.select(conditions,choices, default='')
    if df['Signal'].iloc[-1] == ("Sell" or "Buy"):
        return  "is outside Bollinger Band"

def trend_template(df: pd.DataFrame) -> int | None:
    """
    Implements the Mark Minervini trend template stock screener.

    Evaluates a stock against 7 of the 8 Minervini trend rules to identify stocks in
    healthy uptrends. Rules check: price position relative to moving averages (50/150/200),
    moving average alignment, 200-SMA trending, price strength vs 52-week range, and 
    consolidation patterns. Higher scores indicate stronger trend confirmation.

    :param df: OHLCV DataFrame from yfinance with at least 260 periods of data (1-year history)
    :return: Integer count of rules passed (0-7), or None if DataFrame is empty
    """
    # stock_db = "ticker_" + stock.lower().replace(".","_")
    # df = pd.read_sql(stock_db,engine)
    tests_passed=0
    if df.empty:
        return None
    smaUsed=[50,150,200]
    try:
        for x in smaUsed:
            sma=x
            df["SMA_"+str(sma)] = df["Close"].rolling(window=sma).mean().round(2)
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
            tests_passed += 1
        #Condition 2: 150 SMA and > 200 SMA
        if(moving_average_150>moving_average_200):
            tests_passed += 1
        #Condition 3: 200 SMA trending up for at least 1 month (ideally 4-5 months)
        if(moving_average_150>moving_average_200_20past):
            tests_passed += 1
        #Condition 4: 50 SMA> 150 SMA and 50 SMA> 200 SMA
        if(moving_average_50>moving_average_150 and moving_average_50> moving_average_200):
            tests_passed += 1
        #Condition 5: Current Price > 50 SMA
        if(currentClose>moving_average_50):
            tests_passed += 1
        #Condition 6: Current Price is at least 30% above 52 week low (Many of the best are up 100-300% before coming out of consolidation)
        if(currentClose>(1.3*low_of_52week)):
            tests_passed += 1
        #Condition 7: Current Price is within 25% of 52 week high
        if(currentClose>(0.75*high_of_52week)):
            tests_passed += 1
    except Exception as e:
        print(str(e))
    return tests_passed

def pivot_point(df: pd.DataFrame) -> float | None:
    """
    Identifies pivot point breakouts using a rolling 10-period high window.

    Detects when the highest closing price in a 10-period window remains static for 5
    consecutive periods (indicating a pivot point), then checks if the current price has
    broken above that pivot (bullish) or below it (bearish) on the most recent bar.

    :param df: OHLCV DataFrame from yfinance with at least 10 periods of data
    :return: The pivot point value if price breaches it, None otherwise
    """
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

    try:
        for i in df.index:
            currentMax = max(Range,default=0)
            value = df["High"][i].round(1)
            # date = df["Date"][i]
            Range=Range[1:9]
            Range.append(value) # type: ignore
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
    except Exception as e:
        print(str(e))

def trailing_stop(df: pd.DataFrame, return_df: bool = False) -> pd.DataFrame | str | float | None:
    """
    Calculates ATR-based trailing stops with automatic trend detection and breakout signals.

    Uses 14-period ATR (multiplied by 3) to set dynamic stops that trail the price in both
    uptrends and downtrends. Automatically switches trends when price crosses the stop level.
    Returns the current stop value, a trend breakout signal, or the full DataFrame with stop
    and trend columns appended.

    :param df: OHLCV DataFrame from yfinance with at least 50 periods of data
    :param return_df: If True, return DataFrame with 'stop' and 'trend' columns; if False (default),
                      return stop value (float), trend breakout message (str), or None
    :return: DataFrame if return_df=True, trend breakout message if trend changed, trailing stop
             value (float) if no change, or None if DataFrame has fewer than 50 periods
    """
    if len(df) < 50:
        return
    try:
        pd.set_option('mode.chained_assignment', None)
        df.ta.atr(length=14, append=True)
        df.dropna()
        atr_multiplier = 3
        df['stop'] = None
        df['trend'] = 'Uptrend'
        df.loc[df.index[0], "stop"] = df['Close'].iloc[0] - atr_multiplier * df['ATRr_14'].iloc[0]
        
        for i in df.index[1:]:
            previous_index = df.index[df.index.get_loc(i) -1] # type: ignore
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
    except Exception as e:
        print(str(e))


def extended(df: pd.DataFrame) -> str:
    """
    Identifies overbought conditions by detecting price extension beyond moving averages.

    Calculates how far the current price has extended above multiple moving averages and
    returns conditions that exceed defined thresholds. Useful for identifying potential
    pullback or profit-taking opportunities in strong uptrends.

    Extension thresholds:
    - SMA 10: 10% above
    - EMA 21: 20% above
    - SMA 50: 50% above
    - SMA 200: 100% above

    :param df: OHLCV DataFrame from yfinance with at least 200 periods of data
    :return: Comma-separated string listing all exceeded extension conditions (e.g., "15.5% above SMA_10, 25.3% above EMA_21"),
             or "stock not extended" if no thresholds are exceeded, or "An error occured" on exception
    """

    try:
        smaUsed=[10,50,200]
        for x in smaUsed:
            sma=x
            df["SMA_"+str(sma)]=df["Close"].rolling(window=sma).mean().round(2)
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
        return result_string
    except Exception as e:
        print(str(e))
        return "An error occured"
