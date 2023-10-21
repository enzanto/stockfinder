from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import discord
from discord.ext import commands, tasks
import aiocron
from screen import MarketScreener
import asyncio,functools,typing
import time
import concurrent.futures
import settings
from threading import Thread
import datetime
logger = settings.logging.getLogger("discord")
# intents = discord.Intents.all()
# bot = commands.Bot(case_insensitive=True, command_prefix='!', intents=intents, help_command=None)

CHANNEL_ID=1161668764341907556
# CHANNEL_ID=1156506339019857920 #Test channel
# warnings.simplefilter('ignore', RuntimeWarning)
# timezone = datetime.timezone.tzname("Europe/Oslo")
time_of_day = datetime.time(hour=23, minute=23)


class CronJobs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        logger.info("Ready")
        self.scheduler = AsyncIOScheduler()
        self.func.start()
        self.scheduler.add_job(self.run_func, trigger="cron", day_of_week="0-4", hour="16", minute="45")

        # starting the scheduler
        self.scheduler.start()



    @tasks.loop(time=time_of_day) 
    async def func(self):
        channel = self.bot.get_channel(CHANNEL_ID)
        result = MarketScreener()
        await result.rabbit.connect() #awaited
        await result.database(engine=settings.engine)#awaited
        logger.info("database done")
        await result.rabbit.disconnect()

async def setup(bot):
    await bot.add_cog(CronJobs(bot))