import discord
from discord.ext import commands
import yfinance as yf
import json
from discord import app_commands
import settings
import time
from localdb import tickermap, userdata
from reports import *
tickermapdb = tickermap.TickerMap()
userdatadb = userdata.UserData()

logger = settings.logging.getLogger("discord")
class Watchlist(app_commands.Group):
    @app_commands.command()
    async def add(self,interaction: discord.Interaction, symbol: str):
        inputs = symbol.split()
        discorduser = interaction.user
        discordusername = discorduser.name
        try:
            userdata = userdatadb.get_portfolio_data(discorduser.id) 
            if userdata['watchlist'] == None:
                userdata['watchlist'] = []
            watchlist = userdata['watchlist']
            present = True
        except:
            present = False
        if discorduser.nick != None:
            discordusername = discorduser.nick
        result = []
        for i in inputs:
            try:
                ticker = tickermapdb.get_map_data(i)
                if ticker == None:
                    raise Exception(f"{i} not found in tickermap. trying .ol extension")
            except Exception as e:
                logger.warning(e)
                ticker = tickermapdb.get_map_data(i+".ol")
            if ticker == None:
                logger.warning(f"{i} not in tickermap")
                return
            result.append(ticker['ticker'])
        if present == True:
            for i in result:
                if i not in watchlist:
                    watchlist.append(i)
                else:
                    logger.info(f"{i} already present")
            userdatadb.insert_portfolio_data(discorduser.id, userdata)
        elif present == False:
            logger.info("user not found, creating new user")
            new_dict = {"userid": discorduser.id, "watchlist": result}
            userdatadb.insert_portfolio_data(discorduser.id, new_dict)
        await interaction.response.send_message(" ".join(result)+f" added to {discordusername}", ephemeral=True, delete_after=60)

    @app_commands.command()
    async def view(self, interaction: discord.Interaction):
        userdata = userdatadb.get_portfolio_data(interaction.user.id)
        try:
            await interaction.response.send_message("found list of "+" ".join(userdata['watchlist']), ephemeral=True, delete_after=60)
        except:
            await interaction.response.send_message("You have no list", ephemeral=True, delete_after=60)

    @app_commands.command()
    async def remove(self,interaction: discord.Interaction, symbol: str):
        inputs = symbol.split()
        discorduser = interaction.user
        discordusername = discorduser.name
        userdata = userdatadb.get_portfolio_data(discorduser.id)
        if userdata == None or userdata['watchlist'] == None:
            await interaction.response.send_message("You have no list", ephemeral=True, silent=True, delete_after=60)
            return
        if discorduser.nick != None:
            discordusername = discorduser.nick
        
        
        result = []
        for i in inputs:
            try:
                ticker = tickermapdb.get_map_data(i)
                if ticker == None:
                    raise Exception(f"{i} not found in tickermap. trying .ol extension")
            except Exception as e:
                logger.warning(e)
                ticker = tickermapdb.get_map_data(i+".ol")
            if ticker == None:
                logger.warning(f"{i} not in tickermap")
                return
            result.append(ticker['ticker'])

        for i in result:
            if i in userdata['watchlist']:
                userdata['watchlist'].remove(i)
            else:
                logger.info(f"{i} not in list")
        userdatadb.insert_portfolio_data(userid=discorduser.id, json_data=userdata)
        await interaction.response.send_message(" ".join(result)+f" removed from {discordusername}", ephemeral=True, delete_after=60)
    
    @app_commands.command()
    async def report(self, interaction: discord.Interaction):
        await interaction.response.send_message("Building Report", ephemeral=True, delete_after=60)
        userdata = userdatadb.get_portfolio_data(interaction.user.id) 
        if userdata == None:
            await interaction.response.send_message("No watchlist found", ephemeral=True, delete_after=60)
        userlist = userdata['watchlist']
        userlist.sort()
        embeds,images,embeds2,images2 = await report_db(userlist)
        logger.info(f"retrieved watchlist report for {interaction.user.name}")
        logger.info("length: " ,len(embeds))
        await interaction.edit_original_response(content="report in DM")
        length = 6
        for i in range(0, len(embeds2), length):
            x=i
            emb = embeds2[x:x+length]
            im = images2[x:x+length]
            await interaction.user.send(embeds=emb, files=im, silent=True)
        if len(embeds) > 0:
            for i in range(0, len(embeds), length):
                x=i
                emb = embeds[x:x+length]
                im = images[x:x+length]
                await interaction.user.send(embeds=emb, files=im, silent=True)


async def setup(bot):
    bot.tree.add_command(Watchlist(name="watchlist", description="Access watchlist"), guild=settings.GUILD_ID)
    logger.info("watchlist added")
