import pandas as pd
from sqlalchemy import create_engine
import yfinance as yf

engine = create_engine('sqlite:///TEST_DB.db')

def db_updater(symbol, engine=engine, start='2021-01-01'):
    tableName = "ticker-" + symbol.lower().replace(".","_")
    print(symbol)
    try:
        max_date = pd.read_sql(f'SELECT MAX(DATE) FROM {tableName}',engine).values[0][0]
        print(max_date)
        try:
            new_data = yf.download(symbol, start=pd.to_datetime(max_date))
            new_rows = new_data[new_data.index > max_date]
            new_rows.to_sql(tableName, engine, if_exists='append')
            print(str(len(new_rows))+ ' new rows imported to db')
        except:
            print('No data on ' + symbol + 'But it has DB table')
    except:
        try:
            new_data = yf.download(symbol, start=start)
            new_data.to_sql(tableName, engine)
            print(f'New table created for {tableName} with {str(len(new_data))} rows')
        except:
            print("No data on " + symbol)
            

def get_table(symbol, engine=engine):
    tableName = "ticker-" + symbol.lower().replace(".","_")
    df = pd.read_sql(tableName,engine, index_col="Date")
    return df

