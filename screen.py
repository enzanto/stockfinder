import asyncio
import datetime as dt
import os
import discord
import gspread
import settings
from screener import market_screener
from reports import report_db, report_portfolio
from localdb import userdata
logger = settings.logging.getLogger("discord")
# setup
try:#google sheet
    gc = gspread.service_account("/usr/src/app/credentials.json")
    sh = gc.open('oslobors')
    ws = sh.worksheet('oslobors')
    googleSheet = True
except:
    print("Google sheets not selected")
    googleSheet = False

discord_token = os.environ['discord_token']
print("discord_webhook_url ENV OK")
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
channel_id = 1161668764341907556
today = dt.date.today()
today = str(today)





#main is for running a minervini scan as a kubernetes cronjob 
async def main():
    testing = market_screener.MarketScreener()
    testing.get_osebx_tickers()
    testing.get_osebx_rsi()
    await testing.rabbit.connect()
    ticker_dict_list = testing.stocklist.to_dict(orient='records')
    tickers = []
    for i in ticker_dict_list:
        tickers.append(i['Symbol'])
    embeds,images,embeds2,images2 = await(report_db(tickers, minervini=True))
    print(len(embeds2))


    @bot.event
    async def on_ready():
        channel = bot.get_channel(channel_id)
        logger.info("Bot is ready")
        length=6
        for i in range(0, len(embeds2), length):
            x=i
            emb = embeds2[x:x+length]
            im = images2[x:x+length]
            await channel.send(embeds=emb, files=im, silent=True)
        if len(embeds) > 0:
            for i in range(0, len(embeds), length):
                x=i
                emb = embeds[x:x+length]
                im = images[x:x+length]
                await channel.send(embeds=emb, files=im, silent=True)
        logger.info("done sending")
        await asyncio.sleep(30)
        await bot.close()

    await bot.start(discord_token)
    await testing.rabbit.disconnect()
    print("ALL DONE GOING TO BED")

async def portfolio_report():
    testing = market_screener.MarketScreener()
    userdata_db = userdata.UserData()
    user_data = userdata_db.get_userids()
    print(user_data)
    embed_dict = []
    for user in user_data:
        tickerlist = []
        if user['portfolio'] == None:
            continue
        for i in user['portfolio']:
            print(i)
            tickerlist.append(i)
        embeds= await(report_portfolio(tickerlist))
        embed_dict.append({'user': user['userid'], 'embeds': embeds})
    #fetch from DB


    @bot.event
    async def on_ready():
        logger.info("Bot is ready")
        for user in embed_dict:
            discord_user = await bot.fetch_user(user['user'])
            print(discord_user.name)
            length=6
            embeds = user['embeds']
            if len(embeds) > 0:
                for i in range(0, len(embeds), length):
                    x=i
                    emb = embeds[x:x+length]
                    await discord_user.send(embeds=emb, silent=True)
        logger.info("done sending")
        await asyncio.sleep(30)
        await bot.close()

    await bot.start(discord_token)
    print("ALL DONE GOING TO BED")

if __name__ == "__main__":
    logger = settings.logging.getLogger("bot")
    scan = os.environ['SCAN']
    if scan == "minervini":
        asyncio.run(main())
    elif scan == "portfolio":
        print(scan)
        asyncio.run(portfolio_report())