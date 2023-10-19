from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import discord
from discord.ext import commands, tasks
import aiocron
from screen import MarketScreener
import asyncio,functools,typing
import time
# intents = discord.Intents.all()
# bot = commands.Bot(case_insensitive=True, command_prefix='!', intents=intents, help_command=None)

CHANNEL_ID=1161668764341907556
# CHANNEL_ID=1156506339019857920

# def to_thread(func: typing.Callable) -> typing.Coroutine:
#     @functools.wraps(func)
#     async def wrapper(*args, **kwargs):
#         return await asyncio.to_thread(func, *args, **kwargs)
#     return wrapper

class CronJobs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        print("Ready")
        self.scheduler = AsyncIOScheduler()

        self.scheduler.add_job(self.func, trigger="cron", day_of_week="0-4", hour="17", minute="43")

        #starting the scheduler
        self.scheduler.start()

    async def func(self):
        print(self.bot)
        channel = self.bot.get_channel(CHANNEL_ID)
        result = MarketScreener()
        await result.rabbit.connect()
        await result.database()
        print("database done")
        tasks = [result.scan(i) for i in result.stocklist.index]
        print("all scan tasks appended, now we wait")
        for task in asyncio.as_completed(tasks):
            try:
                await task
            except Exception as e:
                print(f"Error occured: {e}")
        print("done awaiting tasks")
        embeds = []
        embeds2 = []
        images = []
        images2 = []
        finished_result = sorted(result.result['result'], key=lambda x: x['stock'])
        for i in finished_result:
            if i['trend'] >= 7 and "image investtech" in i:
                embeds2.extend(i['embed'])
                images2.extend(i['image'])
            elif i['trend'] >= 7 and "image investtech" not in i:
                embeds.append(i['embed'])
                images.append(i['image'])
        print(embeds)
        length=6
        for i in range(0, len(embeds2), length):
            x=i
            print(i,x)
            emb = embeds2[x:x+length]
            im = images2[x:x+length]
            await channel.send(embeds=emb, files=im, silent=True, delete_after=20)
        if len(embeds) > 0:
            for i in range(0, len(embeds), length):
                x=i
                print(i,x)
                emb = embeds[x:x+length]
                im = images[x:x+length]
                await channel.send(embeds=emb, files=im, silent=True, delete_after=20)
        print("done sending")
        await result.rabbit.disconnect()

async def setup(bot):
    await bot.add_cog(CronJobs(bot))