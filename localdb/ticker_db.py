# third party packages
import pandas as pd
import os
os.environ["YF_USE_CURL_CFFI"] = "0"
import yfinance as yf

# built in modules
from datetime import date, timedelta

import settings

logger = settings.logger
start_date = date.today() - timedelta(days=365 * 3)


async def db_updater(symbol, engine=settings.engine, start=start_date):
    """
    Updates DB with latest stock prices. Checks for newest price in DB, only fetches prices newer than latest price stored.
    :params symbol: ticker symbol
    :param engine: sqlalchemy engine
    :param start: start date for data fetch
    """
    tableName = "ticker_" + symbol.lower().replace(".", "_")
    logger.info(f"Updating table for {symbol}")
    try:
        max_date = pd.read_sql(f'SELECT MAX("Date") FROM {tableName}', engine).values[
            0
        ][0]
        max_date = pd.to_datetime(max_date)
        last_volume = pd.read_sql(
            f'SELECT * FROM {tableName} WHERE "Date"=(SELECT max("Date") FROM {tableName})',
            engine,
        )
        last_volume = last_volume["Volume"][0]
        try:
            new_data = yf.download(symbol, max_date, auto_adjust=True)
            new_data.columns = new_data.columns.get_level_values(0)
            logger.info(f"max date {max_date} for {symbol}")
            new_volume = new_data["Volume"].iloc[0]
            new_data.index.name = "Date"
            if (
                new_volume != last_volume
                and date.today() == pd.Timestamp(max_date).date()
            ):
                raise Exception(f"Todays volume is not equal, updating {symbol}")
            elif (
                new_volume == last_volume
                and date.today() == pd.Timestamp(max_date).date()
            ):
                raise Exception(f"{symbol} already at newest data")
            new_rows = new_data[new_data.index > max_date]
            new_rows.to_sql(tableName, engine, if_exists="append")
            logger.info(str(len(new_rows)) + f" new rows imported to {symbol}")
        except Exception as e:
            if str(e) == f"Todays volume is not equal, updating {symbol}":
                logger.warning(e)
                new_data = yf.download(symbol, start_date)
                new_data.columns = new_data.columns.get_level_values(0)
                new_data.index.name = "Date"
                new_data.to_sql(tableName, engine, if_exists="replace")
                return
            elif str(e) == f"{symbol} already at newest data":
                logger.warning(e)
                return
            else:
                logger.warning(e)
                return

    except Exception as e:
        logger.warning(symbol, e)
        try:
            new_data = yf.download(symbol, start_date)
            new_data.columns = new_data.columns.get_level_values(0)
            new_data.index.name = "Date"
            new_data.to_sql(tableName, engine)
            logger.info(
                f"New table created for {tableName} with {str(len(new_data))} rows"
            )
        except Exception as e:
            logger.warning(e)
            logger.warning("No data on " + symbol)
            return


def get_table(symbol, engine=settings.engine):
    """
    Fetched stock data from DB and returns it as a DF

    :params symbol: Ticker symbol
    :params return: Returns Dataframe
    """
    tableName = "ticker_" + symbol.lower().replace(".", "_")
    df = pd.read_sql(tableName, engine, index_col="Date")
    return df
