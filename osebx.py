import requests
import pandas as pd
from bs4 import BeautifulSoup
import ta
from io import StringIO
import datetime as dt


def get_osebx_tickers():
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

    return stocklist

def get_osebx_rsi():
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

    return indexRSI