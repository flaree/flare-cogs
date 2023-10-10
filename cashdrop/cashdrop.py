import asyncio
import datetime
import operator
import random

from redbot.core import Config, bank, commands
from redbot.core.utils.predicates import MessagePredicate


class Cashdrop(commands.Cog):
    __version__ = "0.1.2"
    __author__ = "flare(flare#0001)"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808)
        self.config.register_guild(
            active=False,
            maths=True,
            chance=1,
            interval=60,
            timestamp=None,
            credits_max=550,
            credits_min=50,
        )
        self.cache = {}
        asyncio.create_task(self.init_loop())

    def random_calc(self):
        ops = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            #'/':operator.truediv
        }
        num1 = random.randint(0, 12)
        num2 = random.randint(1, 10)
        op = random.choice(list(ops.keys()))
        answer = ops.get(op)(num1, num2)
        return "What is {} {} {}?\n".format(num1, op, num2), answer

    async def init_loop(self):
        await self.bot.wait_until_ready()
        await self.generate_cache()
        # while True:
        #     await asyncio.sleep(60)
        # await self.save()

    def cog_unload(self):
        self.bg_config_loop.cancel()
        asyncio.create_task(self.save_triggers())

    async def generate_cache(self):
        self.cache = await self.config.all_guilds()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if message.guild.id not in self.cache:
            return
        if not self.cache[message.guild.id]["active"]:
            return
        if random.randint(0, 100) > self.cache[message.guild.id]["chance"]:
            return
        if self.cache[message.guild.id]["timestamp"] is None:
            self.cache[message.guild.id]["timestamp"] = datetime.datetime.now(
                tz=datetime.timezone.utc
            )
        if (
            datetime.datetime.now(tz=datetime.timezone.utc)
            - self.cache[message.guild.id]["timestamp"]
        ).total_seconds() < self.cache[message.guild.id]["interval"]:
            return
        self.cache[message.guild.id]["timestamp"] = datetime.datetime.now(tz=datetime.timezone.utc)
        if self.cache[message.guild.id]["maths"]:
            string, answer = self.random_calc()
            msg = await message.channel.send(string)
            try:
                pred = MessagePredicate.lower_contained_in(
                    str(answer), channel=message.channel, user=None
                )
                await self.bot.wait_for("message", check=pred, timeout=10)
            except asyncio.TimeoutError:
                await msg.edit(content="Too slow!")
                return
            if not pred.result:
                creds = random.randint(
                    self.cache[message.guild.id]["credits_min"],
                    self.cache[message.guild.id]["credits_max"],
                )
                await msg.edit(
                    content=f"Correct! You got {creds} {await bank.get_currency_name(guild=message.guild)}!"
                )
                await bank.deposit_credits(message.author, creds)
        else:
            msg = await message.channel.send(
                f"Some {await bank.get_currency_name(guild=message.guild)} have fallen, type `pickup` to pick them up!"
            )
            pred = MessagePredicate.lower_contained_in(
                "pickup", channel=message.channel, user=None
            )
            try:
                await self.bot.wait_for("message", check=pred, timeout=10)
            except asyncio.TimeoutError:
                await msg.edit(content="Too slow!")
                return

            if not pred.result:
                creds = random.randint(
                    self.cache[message.guild.id]["credits_min"],
                    self.cache[message.guild.id]["credits_max"],
                )
                await msg.edit(
                    content=f"You picked up {creds} {await bank.get_currency_name(guild=message.guild)}!"
                )
                await bank.deposit_credits(message.author, creds)

    @commands.group(name="cashdrop", aliases=["cd"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def _cashdrop(self, ctx):
        """
        Manage the cashdrop
        """

    @_cashdrop.command(name="toggle")
    async def _toggle(self, ctx):
        """
        Toggle the cashdrop
        """
        guild = ctx.guild
        active = await self.config.guild(guild).active()
        if active:
            await self.config.guild(guild).active.set(False)
            await ctx.send("Cashdrop is now disabled")
        else:
            await self.config.guild(guild).active.set(True)
            await ctx.send("Cashdrop is now enabled")
        await self.generate_cache()

    @_cashdrop.command(name="chance")
    async def _chance(self, ctx, chance: int):
        """
        Set the chance percent of the cashdrop
        """
        if chance < 0 or chance > 100:
            await ctx.send("Chance must be between 0 and 100")
            return
        guild = ctx.guild
        await self.config.guild(guild).chance.set(chance)
        await ctx.send(f"Chance set to {chance}%")
        await self.generate_cache()

    @_cashdrop.command(name="interval")
    async def _interval(self, ctx, interval: int):
        """
        Set the interval in seconds between cashdrops
        """
        if interval < 0:
            await ctx.send("Interval must be greater than 0")
            return
        guild = ctx.guild
        await self.config.guild(guild).interval.set(interval)
        await ctx.send(f"Interval set to {interval} seconds")
        await self.generate_cache()

    @_cashdrop.command(name="max")
    async def _max(self, ctx, max: int):
        """
        Set the max credits
        """

        if max < 0:
            await ctx.send("Max must be greater than 0")
            return
        mincredits = await self.config.guild(ctx.guild).credits_min()
        if max < mincredits:
            await ctx.send("Max must be greater than min")
            return
        guild = ctx.guild
        await self.config.guild(guild).credits_max.set(max)
        await ctx.send(f"Max credits set to {max}")
        await self.generate_cache()

    @_cashdrop.command(name="min")
    async def _min(self, ctx, min: int):
        """
        Set the min credits
        """

        if min < 0:
            await ctx.send("Min must be greater than 0")
            return
        maxcredits = await self.config.guild(ctx.guild).credits_max()
        if maxcredits < min:
            await ctx.send("Min must be less than min")
            return
        guild = ctx.guild
        await self.config.guild(guild).credits_min.set(min)
        await ctx.send(f"Min credits set to {min}")
        await self.generate_cache()

    @_cashdrop.command(name="maths")
    async def _maths(self, ctx, toggle: bool):
        """
        Toggle maths mode
        """
        guild = ctx.guild
        if toggle:
            await self.config.guild(guild).maths.set(True)
            await ctx.send("Maths mode is now enabled")
        else:
            await self.config.guild(guild).maths.set(False)
            await ctx.send("Maths mode is now disabled")
        await self.generate_cache()
