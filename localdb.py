import pandas as pd
from sqlalchemy import create_engine
import yfinance as yf
from datetime import date, timedelta, datetime
import settings
logger = settings.logging.getLogger("bot")

engine = create_engine('sqlite:///TEST_DB.db')
start_date = date.today() - timedelta(days= 365*3)
def db_updater(symbol, engine=engine, start=start_date):
    tableName = "ticker_" + symbol.lower().replace(".","_")
    logger.info(f"Updating table for {symbol}")
    try:
        max_date = pd.read_sql(f'SELECT MAX("Date") FROM {tableName}',engine).values[0][0]
        max_date = pd.to_datetime(max_date)
        last_volume = pd.read_sql(f'SELECT * FROM {tableName} WHERE Date=(SELECT max("Date") FROM {tableName})',engine)
        last_volume = last_volume['Volume'][0]
        try:
            new_data = yf.download(symbol, start=max_date)
            new_volume = new_data['Volume'].iloc[0]
            if new_volume != last_volume and date.today() == pd.Timestamp(max_date).date():
                raise Exception("Todays volume is not equal, updating db")
            elif new_volume == last_volume and date.today() == pd.Timestamp(max_date).date():
                raise Exception("DB already at newest data")
            new_rows = new_data[new_data.index > max_date]
            new_rows.to_sql(tableName, engine, if_exists='append')
            logger.info(str(len(new_rows))+ ' new rows imported to db')
        except Exception as e:
            if str(e)== "Todays volume is not equal, updating db":
                print(e)
                new_data = yf.download(symbol, start=start)
                new_data.to_sql(tableName, engine, if_exists='replace')
            elif str(e) == "DB already at newest data":
                print(e)
            else:
                print(e)
        
    except Exception as e:
        print(e)
        try:
            new_data = yf.download(symbol, start=start)
            new_data.to_sql(tableName, engine)
            print(f'New table created for {tableName} with {str(len(new_data))} rows')
        except Exception as e:
            print(e)
            print("No data on " + symbol)
            

def get_table(symbol, engine=engine):
    tableName = "ticker_" + symbol.lower().replace(".","_")
    df = pd.read_sql(tableName,engine, index_col="Date")
    return df
# for testing
if __name__ == "__main__":
    db_updater("2020.ol")

    

