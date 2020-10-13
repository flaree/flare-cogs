import asyncio
import datetime
import logging
from collections import OrderedDict
from copy import deepcopy
from io import StringIO
from typing import Counter, Optional

import discord
import pandas
from redbot.core import Config, commands

from .menus import EmbedFormat, GenericMenu


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


log = logging.getLogger("red.flare.commandstats")


class CommandStats(commands.Cog):
    """Command Statistics."""

    __version__ = "0.1.0"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 1398467138476, force_registration=True)
        default_global = {"globaldata": Counter({}), "guilddata": {}, "automated": Counter({})}
        self.config.register_global(**default_global)
        self.cache = {"guild": {}, "session": Counter({}), "automated": Counter({})}
        self.session = Counter()
        self.session_time = datetime.datetime.utcnow()
        self.bg_loop_task = self.bot.loop.create_task(self.bg_loop())

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                await self.update_global()
                await self.update_data()
                await asyncio.sleep(300)
            except Exception as exc:
                log.error("Exception in bg_loop: ", exc_info=exc)
                self.bg_loop_task.cancel()

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        asyncio.create_task(self.update_data())
        asyncio.create_task(self.update_global())

    def record(self, ctx, name):
        guild = ctx.message.guild
        if not ctx.message.author.bot:
            if getattr(ctx, "assume_yes", False):
                if name not in self.cache["automated"]:
                    self.cache["automated"][name] = 1
                else:
                    self.cache["automated"][name] += 1
                return
            if guild is not None:
                if str(guild.id) not in self.cache["guild"]:
                    self.cache["guild"][str(guild.id)] = Counter({})
                if name not in self.cache["guild"][str(guild.id)]:
                    self.cache["guild"][str(guild.id)][name] = 1
                else:
                    self.cache["guild"][str(guild.id)][name] += 1
            if name not in self.cache["session"]:
                self.cache["session"][name] = 1
            else:
                self.cache["session"][name] += 1
            if name not in self.session:
                self.session[name] = 1
            else:
                self.session[name] += 1

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Record standard command events."""
        if not ctx.valid:
            return
        name = str(ctx.command)
        self.record(ctx, name)

    @commands.Cog.listener()
    async def on_commandstats_action(self, ctx):
        """Record action events (i.e. other cog emits 'commandstats_action')."""
        name = str(ctx.command)
        self.record(ctx, name)

    def build_data(self, data):
        data = OrderedDict(sorted(data.items(), key=lambda t: t[1], reverse=True))
        stats = []
        for cmd, amount in data.items():
            stats.append([f"{cmd}", f"{amount} time{'s' if amount != 1 else ''}"])
        return list(chunks(stats, 15))

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
            await GenericMenu(
                source=EmbedFormat(self.build_data(data)),
                title="Commands Used",
                _type="Command",
                ctx=ctx,
            ).start(
                ctx=ctx,
                wait=False,
            )

        else:
            if command in data:
                await ctx.send(f"`{command}` has been used {data[command]} times!")
            else:
                await ctx.send(f"`{command}` hasn't been used yet!")

    @cmd.command()
    async def automated(self, ctx):
        """Automated command stats.

        Commands that have `ctx.assume_yes` will qualify as automated."""
        await self.update_global()
        data = await self.config.automated()
        if not data:
            return await ctx.send("No commands have been used yet.")
        await GenericMenu(
            source=EmbedFormat(self.build_data(data)),
            title="Automatic Commands Used",
            _type="Command",
            ctx=ctx,
        ).start(
            ctx=ctx,
            wait=False,
        )

    @cmd.command(aliases=["server"])
    async def guild(
        self,
        ctx,
        server: Optional[commands.GuildConverter] = None,
        *,
        command: str = None,
    ):
        """Guild Command Stats."""
        if not server:
            server = ctx.guild
        await self.update_data()
        data = await self.config.guilddata()
        try:
            data = data[str(server.id)]
        except KeyError:
            return await ctx.send(f"No commands have been used in {server.name} yet.")
        if command is None:
            await GenericMenu(
                source=EmbedFormat(self.build_data(data)),
                title=f"Commands Used in {server.name}",
                _type="Command",
                ctx=ctx,
            ).start(
                ctx=ctx,
                wait=False,
            )

        else:
            if command in data:
                await ctx.send(
                    f"`{command}` has been used {data[command]} time{'s' if data[command] > 1 else ''} in {ctx.guild}!"
                )
            else:
                await ctx.send(f"`{command}` hasn't been used in {server.name}!")

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
            await GenericMenu(
                source=EmbedFormat(self.build_data(data)),
                title="Commands Used during session",
                _type="Command",
                ctx=ctx,
                timestamp=self.session_time,
            ).start(
                ctx=ctx,
                wait=False,
            )

        else:
            if command in data:
                await ctx.send(
                    f"`{command}` has been used {data[command]} time{'s' if data[command] > 1 else ''} in this session!"
                )
            else:
                await ctx.send(f"`{command}` hasn't been used in this session!")

    @cmd.group(invoke_without_command=True)
    async def cogstats(self, ctx, *, cogname: str = None):
        """Show command stats per cog, all cogs or per session."""
        await self.update_global()
        if cogname is not None:
            cog = self.bot.get_cog(cogname)
            if cog is None:
                await ctx.send("No such cog.")
                return
            commands = set([x.qualified_name for x in cog.walk_commands()])
            data = await self.config.globaldata()
            a = {}
            for command in data:
                if command in commands:
                    a[command] = data[command]
            if not a:
                await ctx.send(f"No commands used from {cogname} as of yet.")
                return
            await GenericMenu(
                source=EmbedFormat(self.build_data(a)),
                title=f"{cogname} Commands Used",
                _type="Command",
                ctx=ctx,
            ).start(
                ctx=ctx,
                wait=False,
            )
        else:
            data = await self.config.globaldata()
            a = {}
            for cogn in self.bot.cogs:
                cog = self.bot.get_cog(cogn)
                commands = set([x.qualified_name for x in cog.walk_commands()])
                a[cogn] = 0
                for command in data:
                    if command in commands:
                        a[cogn] += data[command]
            if not a:
                await ctx.send(f"No commands used from any cog as of yet.")
                return
            await GenericMenu(
                source=EmbedFormat(self.build_data(a)),
                title="Cogs Used",
                _type="Cog",
                ctx=ctx,
            ).start(
                ctx=ctx,
                wait=False,
            )

    @cogstats.command(name="session")
    async def _session(self, ctx, *, cogname: str = None):
        """Cog stats in this session."""
        await self.update_global()
        if cogname is not None:
            cog = self.bot.get_cog(cogname)
            if cog is None:
                await ctx.send("No such cog.")
                return
            commands = set([x.qualified_name for x in cog.walk_commands()])
            data = deepcopy(self.session)
            a = {}
            for command in data:
                if command in commands:
                    a[command] = data[command]
            if not a:
                await ctx.send(f"No commands used from {cogname} as of yet.")
                return
            await GenericMenu(
                source=EmbedFormat(self.build_data(a)),
                title=f"{cogname} Commands Used During Session",
                _type="Command",
                ctx=ctx,
                timestamp=self.session_time,
            ).start(
                ctx=ctx,
                wait=False,
            )
        else:
            data = deepcopy(self.session)
            a = {}
            for cogn in self.bot.cogs:
                cog = self.bot.get_cog(cogn)
                commands = set([x.qualified_name for x in cog.walk_commands()])
                a[cogn] = 0
                for command in data:
                    if command in commands:
                        a[cogn] += data[command]
            if not a:
                await ctx.send(f"No commands used from any cog as of yet.")
                return
            await GenericMenu(
                source=EmbedFormat(self.build_data(a)),
                title="Cogs Used During Session",
                _type="Cog",
                ctx=ctx,
            ).start(
                ctx=ctx,
                wait=False,
            )

    @cmd.command()
    async def csv(self, ctx):
        """Return a CSV of all command actions."""
        await self.update_global()
        data = await self.config.globaldata()
        df = pandas.DataFrame.from_dict(data, orient="index", columns=["Usage"])
        df.index.name = "Commands"
        s_buf = StringIO()
        df.to_csv(s_buf)
        s_buf.name = "commandstats.csv"
        s_buf.seek(0)
        await ctx.send(file=discord.File(s_buf))

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

        autodata = await self.config.automated()
        data = autodata + self.cache["automated"]
        await self.config.automated.set(data)
        self.cache["automated"] = Counter({})
