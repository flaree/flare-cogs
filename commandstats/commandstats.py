import asyncio
import datetime
from collections import OrderedDict
from copy import deepcopy
from typing import Counter

import discord
import tabulate
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


class CommandStats(commands.Cog):
    """Command Statistics."""

    __version__ = "0.0.4"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 1398467138476, force_registration=True)
        default_global = {"globaldata": Counter({}), "guilddata": {}}
        self.config.register_global(**default_global)
        self.cache = {"guild": {}, "session": Counter({})}
        self.session = Counter()
        self.session_time = datetime.datetime.utcnow()

    def cog_unload(self):
        asyncio.create_task(self.update_data())
        asyncio.create_task(self.update_global())

    @commands.Cog.listener()
    async def on_command(self, ctx):
        command = str(ctx.command)
        guild = ctx.message.guild
        if not ctx.message.author.bot:
            if guild is not None:
                if str(guild.id) not in self.cache["guild"]:
                    self.cache["guild"][str(guild.id)] = Counter({})
                if command not in self.cache["guild"][str(guild.id)]:
                    self.cache["guild"][str(guild.id)][command] = 1
                else:
                    self.cache["guild"][str(guild.id)][command] += 1
            if command not in self.cache["session"]:
                self.cache["session"][command] = 1
            else:
                self.cache["session"][command] += 1
            if command not in self.session:
                self.session[command] = 1
            else:
                self.session[command] += 1

    @commands.is_owner()
    @commands.group(invoke_without_command=True)
    async def cmd(self, ctx, *, command: str = None):
        """Group command for command stats.

        This command does not log the issuing command.
        """
        await self.update_global()
        data = await self.config.globaldata()
        if not data:
            return await ctx.send("No commands have been used yet.")
        if command is None:
            data = OrderedDict(sorted(data.items(), key=lambda t: t[1], reverse=True))
            stats = []
            for cmd, amount in data.items():
                stats.append([f"{cmd}", f"{amount} time{'s' if amount > 1 else ''}!"])
            a = chunks(stats, 15)
            embeds = []
            for items in a:
                stats = []
                for item in items:
                    stats.append(item)
                embed = discord.Embed(
                    title="Commands used",
                    colour=await self.bot.get_embed_color(ctx.channel),
                    description=box(
                        tabulate.tabulate(stats, headers=["Command", "Times Used"]), lang="prolog"
                    ),
                )
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)

        else:
            if command in data:
                await ctx.send(f"`{command}` has been used {data[command]} times!")
            else:
                await ctx.send(f"`{command}` hasn't been used yet!")

    @cmd.command(aliases=["server"])
    async def guild(self, ctx, *, command: str = None):
        """Guild Command Stats."""
        await self.update_data()
        data = await self.config.guilddata()
        data = data[str(ctx.guild.id)]
        if not data:
            return await ctx.send("No commands have been used in this guild yet.")
        if command is None:
            data = OrderedDict(sorted(data.items(), key=lambda t: t[1], reverse=True))
            stats = []
            for cmd, amount in data.items():
                stats.append([f"{cmd}", f"{amount} time{'s' if amount > 1 else ''}!"])
            a = chunks(stats, 15)
            embeds = []
            for items in a:
                stats = []
                for item in items:
                    stats.append(item)
                embed = discord.Embed(
                    title="Commands used in this guild",
                    colour=await self.bot.get_embed_color(ctx.channel),
                    description=box(
                        tabulate.tabulate(stats, headers=["Command", "Times Used"]), lang="prolog"
                    ),
                )
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)

        else:
            if command in data:
                await ctx.send(
                    f"`{command}` has been used {data[command]} time{'s' if data[command] > 1 else ''} in {ctx.guild}!"
                )
            else:
                await ctx.send(f"`{command}` hasn't been used in {ctx.guild}!")

    @cmd.command()
    async def session(self, ctx, *, command: str = None):
        """Session command stats."""
        data = deepcopy(self.session)
        if str(ctx.command) in data:
            data[str(ctx.command)] += 1
        else:
            data[str(ctx.command)] = 1
        if not data:
            return await ctx.send("No commands have been used in this session")
        if command is None:
            data = OrderedDict(sorted(data.items(), key=lambda t: t[1], reverse=True))
            stats = []
            for cmd, amount in data.items():
                stats.append([f"{cmd}", f"{amount} time{'s' if amount > 1 else ''}!"])
            a = chunks(stats, 15)
            embeds = []
            for items in a:
                stats = []
                for item in items:
                    stats.append(item)
                embed = discord.Embed(
                    title="Commands used in this session",
                    colour=await self.bot.get_embed_color(ctx.channel),
                    description=box(
                        tabulate.tabulate(stats, headers=["Command", "Times Used"]), lang="prolog"
                    ),
                    timestamp=self.session_time,
                )
                embed.set_footer(text="Recording sessions commands since")
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)

        else:
            if command in data:
                await ctx.send(
                    f"`{command}` has been used {data[command]} time{'s' if data[command] > 1 else ''} in this session!"
                )
            else:
                await ctx.send(f"`{command}` hasn't been used in this session!")

    async def update_data(self):
        async with self.config.guilddata() as guilddata:
            for guild in self.cache["guild"]:
                if guild in guilddata:
                    olddata = Counter(guilddata[guild])
                else:
                    olddata = Counter({})
                data = Counter(olddata + self.cache["guild"][guild])
                self.cache["guild"][guild] = Counter()
                guilddata[guild] = data

    async def update_global(self):
        globaldata = await self.config.globaldata()
        data = globaldata + self.cache["session"]
        await self.config.globaldata.set(data)
        self.cache["session"] = Counter({})
