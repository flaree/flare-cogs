import logging
from datetime import datetime, timedelta

import discord
from redbot.core import Config, commands
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_timedelta, pagify

log = logging.getLogger("red.flare.antispam")


class AntiSpam(commands.Cog):
    """Blacklist those who spam commands."""

    __version__ = "0.0.3"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(mute_length=300, amount=5, per=5, mod_bypass=True)
        self.cache = {}
        self.blacklist = {}
        bot.add_check(self.check)

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
        return False

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if await self.bot.is_owner(ctx.author) or (
            self.config_cache["mod_bypass"] and await self.bot.is_mod(ctx.author)
        ):
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
                    f"Slow down {ctx.author.name}! You're now on a {humanize_timedelta(seconds=self.config_cache['mute_length'])} cooldown from commands.",
                    delete_after=self.config_cache["mute_length"],
                )

    @commands.is_owner()
    @commands.group()
    async def antispamset(self, ctx):
        """Settings for antispam"""

    @antispamset.command()
    async def length(self, ctx, *, length: TimedeltaConverter):
        """How long to blacklist a user from using commands."""
        duration_seconds = length.total_seconds()
        await self.config.mute_length.set(duration_seconds)
        await ctx.send(
            f"The spam filter blacklist timer has been set to {humanize_timedelta(seconds=duration_seconds)}."
        )
        await self.gen_cache()

    @antispamset.command()
    async def per(self, ctx, *, length: TimedeltaConverter):
        """How long of a timeframe to keep track of command spamming."""
        duration_seconds = length.total_seconds()
        await self.config.per.set(duration_seconds)
        await ctx.send(
            f"The spam filter has been set to check commands during a  {humanize_timedelta(seconds=duration_seconds)} period."
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
    async def bypass(self, ctx, on_or_ff: int):
        """Toggle whether mods or admins bypass the spam filter."""
        await self.config.mod_bypass.set(on_or_ff)
        if on_or_ff:
            await ctx.send(
                f"The spam filter will now allow for mods and admins to bypass the filter."
            )
        else:
            await ctx.send("Mods and admins will no longer bypass the filter.")
        await self.gen_cache()

    @antispamset.command()
    async def list(self, ctx):
        """Show those currently blacklisted from using commands."""
        if not self.blacklist:
            return await ctx.send("No users currently blacklisted.")
        msg = []
        for user in self.blacklist:
            if self.blacklist[user]["expiry"] > datetime.now():
                msg += f"{self.bot.get_user(self.blacklist[user]['id'])}: {humanize_timedelta(timedelta=self.blacklist[user]['expiry'] - datetime.now())}"
        if not msg:
            return await ctx.send("No users currently blacklisted.")
        for page in pagify("\n".join(msg)):
            await ctx.maybe_send_embed(page)

    @antispamset.command()
    async def settings(self, ctx):
        """Show current antispam settings"""
        await self.gen_cache()
        msg = f"**Blacklist Length**: {humanize_timedelta(seconds=self.config_cache['mute_length'])}\n**Per** {humanize_timedelta(seconds=self.config_cache['per'])}\n**Amount**: {self.config_cache['amount']}\n**Mod/Admin Bypass**: {'Yes' if self.config_cache['mod_bypass'] else 'No'}"
        await ctx.maybe_send_embed(msg)
