import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_timedelta, pagify

log = logging.getLogger("red.flare.antispam")


class AntiSpam(commands.Cog):
    """Blacklist those who spam commands."""

    __version__ = "0.0.10"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(
            mute_length=300, amount=5, per=5, mod_bypass=True, logging=None
        )
        self.cache = {}
        self.blacklist = {}
        bot.add_check(self.check)
        self.antispam_loop_task: Optional[asyncio.Task] = None

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    def cog_unload(self):
        if self.antispam_loop_task:
            self.antispam_loop_task.cancel()

    async def init(self):
        self.antispam_loop_task = self.bot.loop.create_task(self.antispam_loop())
        await self.gen_cache()

    async def antispam_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                to_delete = []
                for user in self.blacklist:
                    if self.blacklist[user]["expiry"] < datetime.now():
                        to_delete.append(user)
                for entry in to_delete:
                    del self.blacklist[entry]
                await asyncio.sleep(60)
            except Exception as exc:
                log.error("Exception occured in snipe loop: ", exc_info=exc)
                break

    async def gen_cache(self):
        self.config_cache = await self.config.all()

    def check(self, ctx):
        user = self.blacklist.get(ctx.author.id)
        if user is None:
            return True
        if self.blacklist[ctx.author.id]["expiry"] < datetime.now():
            del self.blacklist[ctx.author.id]
            log.debug(f"{ctx.author}({ctx.author.id}) has been removed from the spam blacklist.")
            return True
        if isinstance(ctx.command, commands.commands._AlwaysAvailableCommand):
            return True
        return False

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if await self.bot.is_owner(ctx.author) or (
            self.config_cache["mod_bypass"] and await self.bot.is_mod(ctx.author)
        ):
            return
        if not ctx.valid:
            return
        author = ctx.author
        ctx.guild
        now = datetime.now()
        if author.id not in self.cache:
            self.cache[author.id] = {"count": 1, "time": now}
        else:
            if now - self.cache[author.id]["time"] > timedelta(seconds=self.config_cache["per"]):
                self.cache[author.id] = {"count": 1, "time": now}
                return
            self.cache[author.id]["count"] += 1
            if (
                self.cache[author.id]["count"] >= self.config_cache["amount"]
                and author.id not in self.blacklist
            ):
                log.debug(
                    f"{ctx.author}({ctx.author.id}) has been blacklisted from using commands for {self.config_cache['mute_length']} seconds."
                )
                expiry = datetime.now() + timedelta(seconds=self.config_cache["mute_length"])
                self.blacklist[author.id] = {"id": author.id, "expiry": expiry}
                await ctx.send(
                    f"Slow down {ctx.author.mention}! You're now on a {humanize_timedelta(seconds=self.config_cache['mute_length'])} cooldown from commands.",
                    delete_after=self.config_cache["mute_length"],
                )
                if self.config_cache.get("logging", None) is not None:
                    channel = self.bot.get_channel(self.config_cache["logging"])
                    if channel:
                        server_msg = f"{ctx.channel.mention} ({ctx.guild})" if ctx.guild else "DMs"
                        await channel.send(
                            f"{ctx.author}({ctx.author.id}) has been blacklisted from using commands for {self.config_cache['mute_length']} seconds.\nLast command was in {server_msg}."
                        )

    @commands.is_owner()
    @commands.group()
    async def antispamset(self, ctx):
        """Settings for antispam"""

    @antispamset.command()
    async def length(self, ctx, *, length: TimedeltaConverter):
        """How long to blacklist a user from using commands.

        Accepts: seconds, minutes, hours, days, weeks
        Examples:
            `[p]antispamset length 1d2h30m`
            `[p]antispamset length 1 day 2 hours 30 minutes`
        """
        if not length:
            return await ctx.send("You must provide a value greater than 0.")
        duration_seconds = length.total_seconds()
        await self.config.mute_length.set(duration_seconds)
        await ctx.send(
            f"The spam filter blacklist timer has been set to {humanize_timedelta(seconds=duration_seconds)}."
        )
        await self.gen_cache()

    @antispamset.command()
    async def per(self, ctx, *, length: TimedeltaConverter):
        """How long of a timeframe to keep track of command spamming.

        Accepts: seconds, minutes, hours, days, weeks
        Examples:
            `[p]antispamset per 1d2h30m`
            `[p]antispamset per 1 day 2 hours 30 minutes`
        """
        if not length:
            return await ctx.send("You must provide a value greater than 0.")
        duration_seconds = length.total_seconds()
        await self.config.per.set(duration_seconds)
        await ctx.send(
            f"The spam filter has been set to check commands during a {humanize_timedelta(seconds=duration_seconds).rstrip('s')} period."
        )
        await self.gen_cache()

    @antispamset.command()
    async def amount(self, ctx, amount: int):
        """How many commands it takes to trigger a muting."""
        if amount < 1:
            return await ctx.send("You must provide a value greater than 0.")
        await self.config.amount.set(amount)
        await ctx.send(
            f"The spam filter will now check for {amount} commands during the configured time."
        )
        await self.gen_cache()

    @antispamset.command()
    async def bypass(self, ctx, on_or_off: bool):
        """Toggle whether mods or admins bypass the spam filter."""
        await self.config.mod_bypass.set(on_or_off)
        if on_or_off:
            await ctx.send(
                "The spam filter will now allow for mods and admins to bypass the filter."
            )
        else:
            await ctx.send("Mods and admins will no longer bypass the filter.")
        await self.gen_cache()

    @antispamset.command()
    async def logging(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to send antispam logs."""
        await self.config.logging.set(None if channel is None else channel.id)
        if channel:
            await ctx.send(f"Logged antispam actions will now be sent to {channel}.")
        else:
            await ctx.send("Logging will no longer be posted.")
        await self.gen_cache()

    @antispamset.command(name="list")
    async def _list(self, ctx):
        """Show those currently blacklisted from using commands."""
        if not self.blacklist:
            return await ctx.send("No users currently blacklisted.")
        msg = []
        for user in self.blacklist:
            if self.blacklist[user]["expiry"] > datetime.now():
                msg.append(
                    f"{self.bot.get_user(self.blacklist[user]['id'])}: {humanize_timedelta(timedelta=self.blacklist[user]['expiry'] - datetime.now())}"
                )
        if not msg:
            return await ctx.send("No users currently blacklisted.")
        for page in pagify("\n".join(msg)):
            await ctx.maybe_send_embed(page)

    @antispamset.command()
    async def settings(self, ctx):
        """Show current antispam settings"""
        await self.gen_cache()
        if self.config_cache["logging"]:
            channel = self.bot.get_channel(self.config_cache["logging"])
        else:
            channel = None
        msg = (
            f"**Blacklist Length**: {humanize_timedelta(seconds=self.config_cache['mute_length'])}\n"
            f"**Per** {humanize_timedelta(seconds=self.config_cache['per'])}\n"
            f"**Amount**: {self.config_cache['amount']}\n"
            f"**Mod/Admin Bypass**: {'Yes' if self.config_cache['mod_bypass'] else 'No'}\n"
            f"**Logging**: {'Yes - {}'.format(channel.mention) if channel else 'No'}"
        )
        await ctx.maybe_send_embed(msg)

    @antispamset.command()
    async def remove(self, ctx, user: discord.Member):
        """Remove a user from the anti-spam blacklist."""
        if user.id in self.blacklist:
            del self.blacklist[user.id]
            await ctx.tick()
            return
        await ctx.send(f"{user} isn't blocked from using commands.")

    @antispamset.command()
    async def clear(self, ctx):
        """Clear the antispam list."""
        self.blacklist = {}
        await ctx.tick()

    @antispamset.command()
    async def add(
        self, ctx, users: commands.Greedy[discord.Member], *, length: TimedeltaConverter
    ):
        """Manually blacklist a user for a set time."""
        expiry = datetime.now() + length
        for user in users:
            self.blacklist[user.id] = {"id": user.id, "expiry": expiry}
        await ctx.tick()
