from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import discord
from discord.ext import commands, tasks
import aiocron
from screen import MarketScreener
import asyncio

# intents = discord.Intents.all()
# bot = commands.Bot(case_insensitive=True, command_prefix='!', intents=intents, help_command=None)

CHANNEL_ID=1161668764341907556


class CronJobs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        print("Ready")
        scheduler = AsyncIOScheduler()

        scheduler.add_job(CronJobs.func, args=[self], trigger=CronTrigger(day_of_week="0-4", hour="17", minute="20")) 

        #starting the scheduler
        scheduler.start()
        
    async def func(self):
        print(self.bot)
        channel = self.bot.get_channel(CHANNEL_ID)
        result = MarketScreener()
        await result.rabbit.connect()
        tasks = []
        await result.database()
        for i in result.stocklist.index:
            tasks.append(asyncio.create_task(result.scan(i)))
        await asyncio.gather(*tasks)
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
        print("done sending")
        await result.rabbit.disconnect()
        # await channel.send("goood moorning", silent=True, delete_after=30)


# @bot.event
# async def on_ready():
#     print("Ready")

#     #initializing scheduler
#     scheduler = AsyncIOScheduler()


#     scheduler.add_job(func, CronTrigger(day_of_week="0-4", hour="21", minute="59", second="0")) 

#     #starting the scheduler
#     scheduler.start()

async def setup(bot):
    await bot.add_cog(CronJobs(bot))