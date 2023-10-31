import pandas as pd
import asyncio
import rabbitmq_client as rabbitmq_client
from sqlalchemy import create_engine, Column, Integer, JSON, BigInteger, String, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker,declarative_base
from sqlalchemy.types import TypeDecorator
import yfinance as yf
from datetime import date, timedelta, datetime
import settings
import json
logger2 = settings.logging.getLogger("discord")
tz = settings.tz

Base = declarative_base()
engine = settings.engine
start_date = date.today() - timedelta(days= 365*3)
async def db_updater(symbol, engine=engine, start=start_date, rabbit=None, serverside=False,logger=logger2):
    tableName = "ticker_" + symbol.lower().replace(".","_")
    logger.info(f"Updating table for {symbol}")
    if rabbit == None and serverside == False:
        rabbit = rabbitmq_client.rabbitmq()
        await rabbit.connect()
    try:
        max_date = pd.read_sql(f'SELECT MAX("Date") FROM {tableName}',engine).values[0][0]
        max_date = pd.to_datetime(max_date)
        last_volume = pd.read_sql(f'SELECT * FROM {tableName} WHERE "Date"=(SELECT max("Date") FROM {tableName})',engine)
        last_volume = last_volume['Volume'][0]
        try:
            if serverside == True:
                new_data = yf.download(symbol, max_date)
            else:
                new_data = await rabbit.get_yahoo(symbol, max_date)
            logger.info(f"max date {max_date} for {symbol}")
            new_volume = new_data['Volume'].iloc[0]
            new_data.index.name = "Date"
            if new_volume != last_volume and date.today() == pd.Timestamp(max_date).date():
                raise Exception(f"Todays volume is not equal, updating {symbol}")
            elif new_volume == last_volume and date.today() == pd.Timestamp(max_date).date():
                raise Exception(f"{symbol} already at newest data")
            new_rows = new_data[new_data.index > max_date]
            new_rows.to_sql(tableName, engine, if_exists='append')
            logger.info(str(len(new_rows))+ f' new rows imported to {symbol}')
        except Exception as e:
            if str(e)== f"Todays volume is not equal, updating {symbol}":
                print(e)
                if serverside == True:
                    new_data = yf.download(symbol, max_date)
                else:
                    new_data = await rabbit.get_yahoo(symbol, max_date)
                new_data.index.name = "Date"
                new_data.to_sql(tableName, engine, if_exists='replace')
                return
            elif str(e) == f"{symbol} already at newest data":
                print(e)
                return
            else:
                print(e)
                return
        
    except Exception as e:
        print(symbol,e)
        try:
            if serverside == True:
                new_data = yf.download(symbol, max_date)
            else:
                new_data = await rabbit.get_yahoo(symbol, max_date)
            new_data.index.name = "Date"
            new_data.to_sql(tableName, engine)
            print(f'New table created for {tableName} with {str(len(new_data))} rows')
        except Exception as e:
            print(e)
            print("No data on " + symbol)
            return
    # await rabbit.disconnect()

def get_table(symbol, engine=engine):
    tableName = "ticker_" + symbol.lower().replace(".","_")
    df = pd.read_sql(tableName,engine, index_col="Date")
    return df
# set and get tickermap
class tickermap:
    class jsonMap(Base):
        __tablename__ = 'tickermap'
        ticker = Column(String, primary_key=True)
        json_data = Column(JSON)

    def __init__(self):
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session=Session()
    def insert_map_data(self,ticker, json_data):
        record = self.session.query(self.jsonMap).filter_by(ticker=ticker.lower()).first()
        if record:
            record.json_data = json_data
        else:
            new_record = self.jsonMap(ticker=ticker.lower(), json_data=json_data)
            self.session.add(new_record)
        self.session.commit()
    def get_map_data(self,ticker):
        record = self.session.query(self.jsonMap).filter_by(ticker=ticker).first()
        if record:
            return record.json_data
        else:
            return None
class userdata:
    class userdata(Base):
        __tablename__ = 'userdata'
        userid = Column(BigInteger, primary_key=True)
        json_data = Column(JSON)

    def __init__(self):
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session=Session()
    def insert_portfolio_data(self,userid, json_data):
        required_keys = ['userid', 'portfolio','watchlist']
        for key in required_keys:
            if key not in json_data:
                json_data[key] = None
        record = self.session.query(self.userdata).filter_by(userid=userid).first()
        if record:
            record.json_data = json_data
        else:
            new_record = self.userdata(userid=userid, json_data=json_data)
            self.session.add(new_record)
        self.session.commit()
    def get_portfolio_data(self,userid):
        record = self.session.query(self.userdata).filter_by(userid=userid).first()
        if record:
            return record.json_data
        else:
            return None
class AwareDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
class scanReport:
    class report(Base):
        __tablename__ = 'report_test2'
        ticker = Column(String, primary_key=True)
        date_col = Column(DateTime, AwareDateTime(timezone=True), name="date")
        json_data = Column(JSON)
        investtech = Column(LargeBinary)
        pivots = Column(LargeBinary)

    def __init__(self):
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session=Session()

    def insert_report_data(self,ticker, json_data, image, investtech_img = None):
        record = self.session.query(self.report).filter_by(ticker=ticker).first()
        if record:
            record.json_data = json_data
            record.date_col = datetime.now(tz)
            record.investtech = investtech_img
            record.pivots = image
        else:
            new_record = self.report(ticker=ticker, json_data=json_data, date_col=datetime.now(tz), investtech=investtech_img, pivots=image)
            self.session.add(new_record)
        self.session.commit()
    def get_report_data(self, ticker):
        record = self.session.query(self.report).filter_by(ticker=ticker).first()
        if record:
            return record.date_col, record.json_data, record.investtech, record.pivots
        else:
            return None, None, None, None
# for testing
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db_updater("2020.ol"))

    

