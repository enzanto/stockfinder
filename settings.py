import os,pathlib
import logging
from logging.config import dictConfig
import discord

discord_token=os.environ['discord_token']
GUILD_ID = discord.Object(id=int(os.environ['GUILD_ID']))

BASE_DIR = pathlib.Path(__file__).parent

CMDS_DIR = BASE_DIR / "cmds"

COGS_DIR = BASE_DIR / "cogs"

SLASH_DIR = BASE_DIR / "slashcmds"

LOGGING_CONFIG = {
    "version": 1,
    "disabled_existing_loggers": False,
    "formatters": {
        "verbose":{
            "format": "%(levelname)-10s - %(asctime)s - %(name)-15s : %(message)s"
        },
        "standard":{
            "format": "%(levelname)-10s - %(name)-15s : %(message)s"
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