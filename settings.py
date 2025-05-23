import os,pathlib
import logging
from logging.config import dictConfig
import discord
from sqlalchemy import create_engine
import pytz


LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "verbose":{
            "format": "%(levelname)-10s - %(asctime)s [%(filename)-10s - %(lineno)-4s - %(funcName)-10s ] %(message)s"
        },
        "standard":{
            "format": "%(levelname)-10s [%(filename)-10s - %(lineno)-4s - %(funcName)-10s ] %(message)s"
        }
    },
    "handlers":{
        "console-debug":{
            'level': "DEBUG",
            'class': "logging.StreamHandler",
            'formatter': "verbose"
        },
        "console-info":{
            'level': "INFO",
            'class': "logging.StreamHandler",
            'formatter': "standard"
        },
        "console2":{
            'level': "WARNING",
            'class': "logging.StreamHandler",
            'formatter': "standard"

        },
        "file":{
            'level': "DEBUG",
            'class': "logging.FileHandler",
            'formatter': "verbose",
            'filename':"logs/infos.log",
            'mode': "w"
        }
    },
    "loggers":{
        "DEBUG": {
            'handlers': ['console-debug'],
            'level': "DEBUG",
            'propagate': False
        },
        "INFO": {
            'handlers': ['console-info'],
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



logger = logging.getLogger(os.environ['LOGLEVEL'])
try: #discord
    discord_token=os.environ['discord_token']
    GUILD_ID = discord.Object(id=int(os.environ['GUILD_ID']))
except KeyError:
    logger.warning("discord not set up")
try:#database
    DBUSER = os.environ['DBUSER']
    logger.info("DBUSER ENV ok")
    DBPASSWORD = os.environ['DBPASSWORD']
    logger.info("DBPASSWORD ENV ok")
    DBADDRESS = os.environ['DBADDRESS']
    logger.info('DBADDRESS ENV OK')
    DBNAME = os.environ['DBNAME']
    try:
        DBPORT = os.environ['DBPORT']
        logger.info('DBPORT ENV ok')
    except:
        DBPORT = "5432"
        logger.info('DBPORT set to standard 5432')
    db_connect_address = f'postgresql+psycopg2://{DBUSER}:{DBPASSWORD}@{DBADDRESS}:{DBPORT}/{DBNAME}'
    engine = create_engine('postgresql+psycopg2://'+DBUSER+':'+DBPASSWORD+'@'+DBADDRESS+':'+DBPORT+'/'+DBNAME)
except KeyError as err:
    logger.warning("DB variables not present, using sqlite local db")
    engine = create_engine('sqlite:///data/TEST_DB.db')

try: #rabbit connection
    rabbit_user = os.environ['RABBIT_USER']
    rabbit_password = os.environ['RABBIT_PASSWORD']
except:
    rabbit_user = "pod"
    rabbit_password = "pod"

try: #timezone
    tz = pytz.timezone(os.environ['TZ'])
except KeyError:
    tz = pytz.timezone('Europe/Oslo')

BASE_DIR = pathlib.Path(__file__).parent

CMDS_DIR = BASE_DIR / "cmds"

COGS_DIR = BASE_DIR / "cogs"

SLASH_DIR = BASE_DIR / "slashcmds"
