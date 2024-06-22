import asyncio
import datetime as dt
import os
import discord
import gspread
import settings
from screener import market_screener
from reports import report_db, report_portfolio
from localdb import userdata
logger = settings.logger
# setup
try:#google sheet
    gc = gspread.service_account("/usr/src/app/credentials.json")
    sh = gc.open('oslobors')
    ws = sh.worksheet('oslobors')
    googleSheet = True
except:
    logger.warning("Google sheets not selected")
    googleSheet = False

discord_token = os.environ['discord_token']
logger.info("discord_webhook_url ENV OK")
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
channel_id = 1161668764341907556
today = dt.date.today()
today = str(today)
completed_rapports = {'minervini': None, 'portfolio': None, 'watchlist': None}





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
    completed_rapports['minervini'] = {'embeds': embeds, 'images': images, 'embeds2': embeds2, 'images2': images2}
    await testing.rabbit.disconnect()

async def portfolio_report():
    userdata_db = userdata.UserData()
    user_data = userdata_db.get_userids()
    logger.info(user_data)
    embed_dict = []
    for user in user_data:
        tickerlist = []
        if user['portfolio'] == None:
            continue
        for i in user['portfolio']:
            tickerlist.append(i)
        embeds= await(report_portfolio(tickerlist))
        embed_dict.append({'user': user['userid'], 'embeds': embeds})
    completed_rapports['portfolio'] = embed_dict

async def watchlist_report():
    userdata_db = userdata.UserData()
    user_data = userdata_db.get_userids()
    logger.info(user_data)
    embed_dict = []
    for user in user_data:
        tickerlist = []
        if user['watchlist'] == None:
            continue
        for i in user['watchlist']:
            #change to i['symbol'] when updating the watchlist structure
            tickerlist.append(i)
        logger.info(user['userid'])
        embeds,images,embeds2,images2 = await(report_db(user['watchlist']))
        embed_dict.append({'user': user['userid'], 'embeds': embeds, 'images': images, 'embeds2': embeds2, 'images2': images2})
        completed_rapports['watchlist'] = embed_dict

async def send_embeds():
    '''
    Sends created embeds to discord
    '''
    @bot.event
    async def on_ready():
        logger.info("Bot ready to send rapports")
        await send_minervini(completed_rapports['minervini'])
        await send_watchlist(completed_rapports['watchlist'])
        await send_portfolio(completed_rapports['portfolio'])
        await asyncio.sleep(30)
        await bot.close()

    async def send_minervini(rapports):
        if rapports == None:
            logger.info("minervini == None")
            return
        embeds = rapports['embeds']
        images = rapports['images']
        embeds2 = rapports['embeds2']
        images2 = rapports['images2']
        channel = bot.get_channel(channel_id)
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
        logger.info("done sending minervini")
        await asyncio.sleep(30)

    async def send_watchlist(rapports):
        if rapports == None:
            logger.info("watchlist == None")
            return
        for user in rapports:
            discord_user = await bot.fetch_user(user['user'])
            logger.info(discord_user.name)
            length=6
            embeds = user['embeds']
            images = user['images']
            embeds2 = user['embeds2']
            images2 = user['images2']
            for i in range(0, len(embeds2), length):
                x=i
                emb = embeds2[x:x+length]
                im = images2[x:x+length]
                await discord_user.send(embeds=emb, files=im, silent=True)
            if len(embeds) > 0:
                for i in range(0, len(embeds), length):
                    x=i
                    emb = embeds[x:x+length]
                    im = images[x:x+length]
                    await discord_user.send(embeds=emb, files=im, silent=True)
        logger.info("done sending watchlist in DM")

    async def send_portfolio(rapports):
        if rapports == None:
            logger.info("Portfolio == None")
            return
        for user in rapports:
            discord_user = await bot.fetch_user(user['user'])
            logger.info(discord_user.name)
            length=6
            embeds = user['embeds']
            if len(embeds) > 0:
                for i in range(0, len(embeds), length):
                    x=i
                    emb = embeds[x:x+length]
                    await discord_user.send(embeds=emb, silent=True)
        logger.info("done sending")

    await bot.start(discord_token)

if __name__ == "__main__":
    logger = settings.logger
    scan = os.environ['SCAN']
    if scan == "minervini":
        asyncio.run(main())
        asyncio.run(watchlist_report())
    elif scan == "portfolio":
        logger.info(scan)
        asyncio.run(portfolio_report())
    elif scan == "watchlist":
        logger.info(scan)
        asyncio.run(watchlist_report())
    elif scan == "debug":
        logger.info(scan)
        channel_id = 1254060220804628671
        logger.debug(f"set discord channel to {channel_id}")
        asyncio.run(main())
    asyncio.run(send_embeds())
