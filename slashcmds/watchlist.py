import discord
from discord.ext import commands
import json
from discord import app_commands
import settings
import time
from investech_scrape import get_img,get_text
from reports import *

def get_ticker_map():
    with open('data/map.json', 'r') as mapfile:
        data=json.load(mapfile)
        return data
def get_watchlist():
    with open('data/watchlist.json', 'r') as watchfile:
        data=json.load(watchfile)
    return data
def update_watchlist(data):
    json_object = json.dumps(data, indent=4)
    with open('data/watchlist.json', 'w') as outfile:
        outfile.write(json_object)
class Watchlist(app_commands.Group):
    @app_commands.command()
    async def add(self,interaction: discord.Interaction, text: str):
        map = get_ticker_map()
        inputs = text.split()
        discorduser = interaction.user
        discordusername = discorduser.name
        data = get_watchlist()
        datalist = data['users']
        if discorduser.nick != None:
            discordusername = discorduser.nick
        result = []
        for i in inputs:
            ticker = next(item for item in map['stocks'] if item['ticker'].lower() == i.lower() or item['ticker'].lower() == i.lower()+".ol")
            result.append(ticker['ticker'])
        try:
            user = next(item for item in data['users'] if item['userid'] == discorduser.id)
            for i in result:
                if i not in user['tickers']:
                    user['tickers'].append(i)
                else:
                    print("already present")
        except:
            print("user not found")
            new_dict = {"username": discorduser.name, "userid": discorduser.id, "tickers": result}
            datalist.append(new_dict)
            data['users'] = datalist
        update_watchlist(data)
        await interaction.response.send_message(" ".join(result)+f" added to {discordusername}", ephemeral=True, delete_after=60)

    @app_commands.command()
    async def view(self, interaction: discord.Interaction):
        data = get_watchlist()
        try:
            userlist = next(item for item in data['users'] if item['userid'] == interaction.user.id)
            await interaction.response.send_message("found list of "+" ".join(userlist['tickers']), ephemeral=True, delete_after=60)
        except:
            await interaction.response.send_message("You have no list", ephemeral=True, delete_after=60)

    @app_commands.command()
    async def remove(self,interaction: discord.Interaction, text: str):
        map = get_ticker_map()
        inputs = text.split()
        discorduser = interaction.user
        discordusername = discorduser.name
        data = get_watchlist()
        if discorduser.nick != None:
            discordusername = discorduser.nick
        
        
        result = []
        for i in inputs:
            ticker = next(item for item in map['stocks'] if item['ticker'].lower() == i.lower() or item['ticker'].lower() == i.lower()+".ol")
            result.append(ticker['ticker'])
        try:
            user = next(item for item in data['users'] if item['userid'] == discorduser.id)
            for i in result:
                if i in user['tickers']:
                    user['tickers'].remove(i)
                else:
                    print("not in list")
            update_watchlist(data)
            await interaction.response.send_message(" ".join(result)+f" removed from {discordusername}", ephemeral=True, delete_after=60)
        except:
            await interaction.response.send_message("Item not in list, or you have no list", ephemeral=True, delete_after=60)
    
    @app_commands.command()
    async def report(self, interaction: discord.Interaction):
        await interaction.response.send_message("Building Report", ephemeral=True, delete_after=60)
        map = get_ticker_map()
        data = get_watchlist()
        user = next(item for item in data['users'] if item['userid'] == interaction.user.id)
        userlist = user['tickers']
        userlist.sort()
        watchlist = []
        for i in userlist:
            ticker = next(item for item in map['stocks'] if item['ticker'].lower() == i.lower())
            watchlist.append(ticker)
        embeds,embed_images = report_simple(watchlist)
        print(len(embeds))
        await interaction.edit_original_response(content="report in DM")
        length = 6
        for i in range(0, len(embeds), length):
            x=i
            print(i,x)
            emb = embeds[x:x+length]
            im = embed_images[x:x+length]
            await interaction.user.send(embeds=emb, files=im)

    @app_commands.command()
    async def fullreport(self, interaction: discord.Interaction):
        await interaction.response.send_message("Building Report", ephemeral=True, delete_after=60)
        map = get_ticker_map()
        data = get_watchlist()
        user = next(item for item in data['users'] if item['userid'] == interaction.user.id)
        userlist = user['tickers']
        userlist.sort()
        watchlist = []
        # time.sleep(10)
        for i in userlist:
            ticker = next(item for item in map['stocks'] if item['ticker'].lower() == i.lower())
            watchlist.append(ticker)
        # watchlist = watchlist.sort()
        embeds,embed_images = report_full(watchlist)
        # print(embeds)
        # print(watchlist)
        print("length: " ,len(embeds))
        await interaction.edit_original_response(content="report in DM")
        length = 6
        for i in range(0, len(embeds), length):
            x=i
            print(i,x)
            emb = embeds[x:x+length]
            im = embed_images[x:x+length]
            await interaction.user.send(embeds=emb, files=im)


async def setup(bot):
    bot.tree.add_command(Watchlist(name="watchlist", description="Says hello"), guild=settings.GUILD_ID)
    # print("setup")