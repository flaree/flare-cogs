import datetime
import random

import discord
from redbot.cogs.bank import check_global_setting_admin
from redbot.core import Config, bank, checks, commands
from redbot.core.utils.chat_formatting import humanize_timedelta

from .defaultreplies import work, crimes


class Unbelievaboat(commands.Cog):
    __version__ = "0.0.1"

    def __init__(self, bot):
        self.bot = bot
        defaults = {
            "cooldowns": {"workcd": 14400, "crimecd": 14400, "robcd": 14400},
            "defaultreplies": True,
            "replies": {"crimereplies": [], "workreplies": []},
            "rob": [],
            "payouts": {"crime": {"max": 300, "min": 10}, "work": {"max": 250, "min": 10}},
            "failrates": {"crime": 50, "rob": 70},
            "fines": {"max": 250, "min": 10},
        }
        defaults_member = {"cooldowns": {"workcd": None, "crimecd": None, "robcd": None}}
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_guild(**defaults)
        self.config.register_member(**defaults_member)

    async def cdcheck(self, ctx, job):
        cd = await self.config.member(ctx.author).cooldowns()
        jobcd = await self.config.guild(ctx.guild).cooldowns()
        if cd[job] is None:
            async with self.config.member(ctx.author).cooldowns() as cd:
                cd[job] = int(datetime.datetime.utcnow().timestamp())
            return True
        time = int(datetime.datetime.utcnow().timestamp()) - cd[job]
        if time < jobcd[job]:
            return (False, humanize_timedelta(seconds=jobcd[job] - time))
        async with self.config.member(ctx.author).cooldowns() as cd:
            cd[job] = int(datetime.datetime.utcnow().timestamp())
        return True

    async def fine(self, ctx, job):
        fines = await self.config.guild(ctx.guild).fines()
        randint = random.randint(fines["min"], fines["max"])
        amount = str(randint) + " " + await bank.get_currency_name(ctx.guild)
        try:
            await bank.withdraw_credits(ctx.author, randint)
            embed = discord.Embed(
                colour=discord.Color.red(),
                description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the polce and fined {amount}",
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        except ValueError:
            await bank.set_balance(ctx.author, 0)
            embed = discord.Embed(
                colour=discord.Color.red(),
                description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the polce and fined {amount}. You did not have enough cash to pay the fine and are now bankrupt.",
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @checks.admin()
    @commands.command(name="set-cooldown")
    async def cooldown_set(
        self,
        ctx,
        job,
        time: commands.TimedeltaConverter(
            minimum=datetime.timedelta(seconds=0),
            maximum=datetime.timedelta(hours=6),
            default_unit="minutes",
        ),
    ):
        """Set the cooldown for the work, crime or rob commands. Minimum cooldown is 30 seconds."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        seconds = time.total_seconds()
        if seconds < 30:
            return await ctx.send("The miniumum interval is 30 seconds.")
        jobcd = {"work": "workcd", "crime": "crimecd"}
        async with self.config.guild(ctx.guild).cooldowns() as cooldowns:
            cooldowns[jobcd[job]] = int(seconds)
        await ctx.tick()

    async def cdnotice(self, user, cooldown, job):
        response = {
            "work": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot work for another {cooldown}.",
            "crime": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot commit a crime for another {cooldown}.",
            "rob": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot rob a person for another {cooldown}.",
        }
        embed = discord.Embed(colour=discord.Color.red(), description=response[job])
        embed.set_author(name=user, icon_url=user.avatar_url)
        return embed

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="set-payout", usage="<work | crime> <min | max> <amount>")
    async def payout_set(self, ctx, job: str, min_or_max: str, amount: int):
        """Set the min or max payout for working or crimes"""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        if min_or_max not in ["max", "min"]:
            return await ctx.send("You must choose between min or max.")
        async with self.config.guild(ctx.guild).payouts() as payouts:
            payouts[job][min_or_max] = amount
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="set-failure-rate", usage="<rob | crime> <amount>")
    async def failure_set(self, ctx, job: str, amount: int):
        """Set the failure rate for crimes and robbing"""
        if job not in ["rob", "crime"]:
            return await ctx.send("Invalid job.")
        if amount < 50 or amount > 100:
            return await ctx.send("Amount must be higher than 50 or less than 100")
        async with self.config.guild(ctx.guild).failrates() as failrates:
            failrates[job] = amount
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="set-fine-rate", usage="<min | max> <amount>")
    async def fine_set(self, ctx, min_or_max: str, amount: int):
        """Set the min or max fine rate for crimes"""
        if min_or_max not in ["max", "min"]:
            return await ctx.send("You must choose between min or max.")
        async with self.config.guild(ctx.guild).fines() as fines:
            fines[min_or_max] = amount
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(aliases=["addcashrole"])
    async def addmoneyrole(self, ctx, amount: int, role: discord.Role):
        """Add money to the balance of all users within a role."""
        for user in role.members:
            try:
                await bank.deposit_credits(user, amount)
            except (ValueError, TypeError):
                pass
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(aliases=["removecashrole"])
    async def removemoneyrole(self, ctx, amount: int, role: discord.Role):
        """Remove money from the balance of all users within a role."""
        for user in role.members:
            try:
                await bank.withdraw_credits(user, amount)
            except ValueError:
                await bank.set_balance(user, 0)
        await ctx.tick()

    @commands.command()
    async def work(self, ctx):
        """Work for some cash."""
        cdcheck = await self.cdcheck(ctx, "workcd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "work")
            return await ctx.send(embed=embed)
        payouts = await self.config.guild(ctx.guild).payouts()
        wage = random.randint(payouts["work"]["min"], payouts["work"]["max"])
        wagesentence = str(wage) + " " + await bank.get_currency_name(ctx.guild)
        if await self.config.guild(ctx.guild).defaultreplies():
            job = random.choice(work)
            line = job.format(amount=wagesentence)
            linenum = work.index(job)
        else:
            replies = await self.config.guild(ctx.guild).replies()
            if len(replies["workreplies"]) == 0:
                return await ctx.send(
                    "You have custom replies enabled yet haven't added any replies yet."
                )
            job = random.choice(replies["workreplies"])
            linenum = replies["workreplies"].index(job)
            line = job.format(amount=wagesentence)
        embed = discord.Embed(
            colour=discord.Color.green(), description=line, timestamp=datetime.datetime.now()
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Reply #{}".format(linenum))
        await bank.deposit_credits(ctx.author, wage)
        await ctx.send(embed=embed)

    @commands.command()
    async def crime(self, ctx):
        """Commit a crime, more risk but higher payout."""
        cdcheck = await self.cdcheck(ctx, "crimecd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "crime")
            return await ctx.send(embed=embed)
        failrates = await self.config.guild(ctx.guild).failrates()
        fail = random.randint(1, 100)
        if fail < failrates["crime"]:
            return await self.fine(ctx, "crime")
        payouts = await self.config.guild(ctx.guild).payouts()
        wage = random.randint(payouts["crime"]["min"], payouts["crime"]["max"])
        wagesentence = str(wage) + " " + await bank.get_currency_name(ctx.guild)
        if await self.config.guild(ctx.guild).defaultreplies():
            job = random.choice(crimes)
            line = job.format(amount=wagesentence)
            linenum = crimes.index(job)
        else:
            replies = await self.config.guild(ctx.guild).replies()
            if len(replies["crimereplies"]) == 0:
                return await ctx.send(
                    "You have custom replies enabled yet haven't added any replies yet."
                )
            job = random.choice(replies["crimereplies"])
            line = job.format(amount=wagesentence)
            linenum = replies["workreplies"].index(job)
        embed = discord.Embed(
            colour=discord.Color.green(), description=line, timestamp=datetime.datetime.now()
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Reply #{}".format(linenum))
        await bank.deposit_credits(ctx.author, wage)
        await ctx.send(embed=embed)

    @commands.command()
    async def rob(self, ctx, user: discord.Member):
        """Rob another user."""
        cdcheck = await self.cdcheck(ctx, "robcd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "rob")
            return await ctx.send(embed=embed)
        failrates = await self.config.guild(ctx.guild).failrates()
        fail = random.randint(1, 100)
        if fail < failrates["rob"]:
            return await self.fine(ctx, "rob")
        userbalance = await bank.get_balance(user)
        if userbalance <= 50:
            embed = discord.Embed(
                colour=discord.Color.red(),
                description="You steal {}'s wallet but there was nothing of value inside.".format(
                    user.name
                ),
                timestamp=datetime.datetime.now(),
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            return await ctx.send(embed=embed)
        stolen = random.randint(1, int(userbalance * 0.075))
        await bank.withdraw_credits(user, stolen)
        await bank.deposit_credits(ctx.author, stolen)
        embed = discord.Embed(
            colour=discord.Color.green(),
            description="You steal {}'s wallet and find {} inside.".format(user.name, stolen),
            timestamp=datetime.datetime.now(),
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @checks.admin()
    @commands.command(name="add-reply")
    async def add_reply(self, ctx, job, *, reply: str):
        """Add a custom reply for working or crime. Put {amount} in place of where you want the amount earned to be."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        if "{amount}" not in reply:
            return await ctx.send("{amount} must be present in the reply.")
        jobreplies = {"work": "workreplies", "crime": "crimereplies"}
        async with self.config.guild(ctx.guild).replies() as replies:
            if reply in replies[jobreplies[job]]:
                return await ctx.send("That is already a response.")
            replies[jobreplies[job]].append(reply)
            ind = replies[jobreplies[job]].index(reply)
        await ctx.send("Your reply has been added and is reply ID #{}".format(ind))

    @checks.admin()
    @commands.command(name="del-reply")
    async def del_reply(self, ctx, job, *, id: int):
        """Delete a custom reply."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        jobreplies = {"work": "workreplies", "crime": "crimereplies"}
        async with self.config.guild(ctx.guild).replies() as replies:
            if len(replies[jobreplies[job]]) == 0:
                return await ctx.send("This job has no custom replies.")
            if id > len(replies[jobreplies[job]]):
                return await ctx.send("Invalid ID.")
            replies[jobreplies[job]].pop(id)
        await ctx.send("Your reply has been removed")

    @checks.admin()
    @commands.command(name="default-replies", usage="<enable | disable>")
    async def default_replies(self, ctx, enable: bool):
        """Whether to use the default replies to work and crime."""
        if enable:
            await ctx.send("Default replies are enabled.")
            await self.config.guild(ctx.guild).defaultreplies.set(enable)
        else:
            await ctx.send("Default replies are now disabled.")
            await self.config.guild(ctx.guild).defaultreplies.set(enable)
