import settings
import discord
from discord.ext import commands
import sys, signal

logger = settings.logger

async def is_owner(ctx):
    return ctx.author.id == ctx.guild.owner.id

CHANNEL_ID=1155922005565116426



def run():
    intents= discord.Intents.all()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix="!", intents=intents)



    @bot.event
    async def on_ready():
        logger.info(f"user: {bot.user} (userID: {bot.user.id})")
        logger.info(f"Guild: {bot.guilds[0]} (guild ID: {bot.guilds[0].id})")
        logger.info(settings.engine)
        
        # for cog_file in settings.COGS_DIR.glob("*.py"):
        #     if cog_file.name != "__init__.py":
        #         await bot.load_extension(f"cogs.{cog_file.name[:-3]}")
        for slash_file in settings.SLASH_DIR.glob("*.py"):
            if slash_file.name != "__init__.py":
                # print(slash_file.name)
                await bot.load_extension(f"slashcmds.{slash_file.name[:-3]}")

        
        await bot.tree.sync(guild=settings.GUILD_ID)
    @bot.command(
        aliases=['p'],
        help="This is help",
        description="This is description",
        brief="Brief")
    async def ping(ctx):
        
        """ Answers with pong"""
        await ctx.send("pong")

    def signal_handler(sig, frame):
        logger.warning(f"Recieved signal: {sig}")
        settings.engine.dispose()
        bot.close()
        sys.exit(0)
    signal.signal(signal.SIGTERM, signal_handler)
    bot.run(settings.discord_token) #removed root_logger=true
    
if __name__ == "__main__":
    run()