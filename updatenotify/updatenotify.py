from redbot.core import commands, Config, checks
import discord
import aiohttp
import asyncio
import random
from prettytable import PrettyTable
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from tabulate import tabulate


class UpdateNotify(commands.Cog):
    def __init__(self, bot):
        defaults = {"channels": {}}
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_global(**defaults)
        self.bot = bot
        self.channels = [583457307866955779, 537706362445234177, 537713976331468841, 581603052331728907, 537709711152119840, 537713395525222421, 537718811340832789, 537807116925140992, 575734237945397259]

    @commands.command()
    async def pings(self, ctx, channel: discord.TextChannel):
        """add yourself to channel pings"""
        if channel.id not in self.channels:
            return await ctx.send("invalid channel")
        async with self.config.channels() as channels:
            if str(channel.id) not in channels:
                channels[str(channel.id)] = []
            if ctx.author.id in channels[str(channel.id)]:
                ind = channels[str(channel.id)].index(ctx.author.id)
                channels[str(channel.id)].pop(ind)
                await ctx.send("Ping removed")
            else:
                channels[str(channel.id)].append(ctx.author.id)
                await ctx.send("Ping added")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id not in self.channels:
            return
        bot = self.bot.get_user(406925865352560650)
        if message.author.id != bot.id:
            return
        if not message.embeds:
            return
        messages = ""
        async with self.config.channels() as channels:
            for user in channels[str(message.channel.id)]:
                messages += "<@{}>".format(user)
        await message.channel.send(messages)
        