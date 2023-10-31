import os,pathlib
import logging
from logging.config import dictConfig
import discord
from sqlalchemy import create_engine
import pytz

try:
    discord_token=os.environ['discord_token']
    GUILD_ID = discord.Object(id=int(os.environ['GUILD_ID']))
except KeyError:
    print("discord not set up")
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

try:
    tz = pytz.timezone(os.environ['TZ'])
except KeyError:
    tz = pytz.timezone('Europe/Oslo')

BASE_DIR = pathlib.Path(__file__).parent

CMDS_DIR = BASE_DIR / "cmds"

COGS_DIR = BASE_DIR / "cogs"

SLASH_DIR = BASE_DIR / "slashcmds"

LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "verbose":{
            "format": "%(levelname)-10s - %(asctime)s [%(filename)-10s - %(lineno)-4s - %(funcName)-10s ] %(name)-15s: %(message)s"
        },
        "standard":{
            "format": "%(levelname)-10s [%(filename)-10s - %(lineno)-4s - %(funcName)-10s ] %(name)-15s: %(message)s"
        }
    },
    "handlers":{
        "console":{
            'level': "DEBUG",
            'class': "logging.StreamHandler",
            'formatter': "standard"
        },
        "console2":{
            'level': "WARNING",
            'class': "logging.StreamHandler",
            'formatter': "standard"

        },
        "file":{
            'level': "INFO",
            'class': "logging.FileHandler",
            'formatter': "verbose",
            'filename':"logs/infos.log",
            'mode': "w"
        }
    },
    "loggers":{
        "bot": {
            'handlers': ['console'],
            'level': "INFO",
            'propagate': False
        },
        "discord": {
            'handlers': ['console2', "file"],
            'level': "INFO",
            'propagate': False
        }
    }
}
dictConfig(LOGGING_CONFIG)