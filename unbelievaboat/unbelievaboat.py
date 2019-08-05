import datetime
import random

import discord
from redbot.core import Config, bank, checks, commands
from redbot.core.utils.chat_formatting import humanize_timedelta
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .defaultreplies import work, crimes


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


def check_global_setting_admin():
    async def predicate(ctx):
        author = ctx.author
        if not await bank.is_global():
            if not isinstance(ctx.channel, discord.abc.GuildChannel):
                return False
            if await ctx.bot.is_owner(author):
                return True
            if author == ctx.guild.owner:
                return True
            if ctx.channel.permissions_for(author).manage_guild:
                return True
            admin_roles = set(await ctx.bot.db.guild(ctx.guild).admin_role())
            for role in author.roles:
                if role.id in admin_roles:
                    return True
        else:
            return await ctx.bot.is_owner(author)

    return commands.check(predicate)


class Unbelievaboat(commands.Cog):
    __version__ = "0.0.4"

    def __init__(self, bot):
        self.bot = bot
        defaults = {
            "cooldowns": {"workcd": 14400, "crimecd": 14400, "robcd": 86400},
            "defaultreplies": True,
            "replies": {"crimereplies": [], "workreplies": []},
            "rob": [],
            "payouts": {"crime": {"max": 300, "min": 10}, "work": {"max": 250, "min": 10}},
            "failrates": {"crime": 50, "rob": 70},
            "fines": {"max": 250, "min": 10},
        }
        defaults_member = {"cooldowns": {"workcd": None, "crimecd": None, "robcd": None}}
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(**defaults)
        self.config.register_guild(**defaults)
        self.config.register_member(**defaults_member)
        self.config.register_user(**defaults_member)

    async def configglobalcheck(self, ctx):
        if await bank.is_global():
            return self.config
        else:
            return self.config.guild(ctx.guild)

    async def configglobalcheckuser(self, ctx):
        if await bank.is_global():
            return self.config.user(ctx.author)
        else:
            return self.config.member(ctx.author)

    async def cdcheck(self, ctx, job):
        conf = await self.configglobalcheck(ctx)
        userconf = await self.configglobalcheckuser(ctx)
        cd = await userconf.cooldowns()
        jobcd = await conf.cooldowns()
        if cd[job] is None:
            async with userconf.cooldowns() as cd:
                cd[job] = int(datetime.datetime.utcnow().timestamp())
            return True
        time = int(datetime.datetime.utcnow().timestamp()) - cd[job]
        if time < jobcd[job]:
            return (False, humanize_timedelta(seconds=jobcd[job] - time))
        async with userconf.cooldowns() as cd:
            cd[job] = int(datetime.datetime.utcnow().timestamp())
        return True

    async def fine(self, ctx, job):
        conf = await self.configglobalcheck(ctx)
        fines = await conf.fines()
        randint = random.randint(fines["min"], fines["max"])
        amount = str(randint) + " " + await bank.get_currency_name(ctx.guild)
        try:
            await bank.withdraw_credits(ctx.author, randint)
            embed = discord.Embed(
                colour=discord.Color.red(),
                description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}",
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        except ValueError:
            await bank.set_balance(ctx.author, 0)
            embed = discord.Embed(
                colour=discord.Color.red(),
                description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}. You did not have enough cash to pay the fine and are now bankrupt.",
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="set-cooldown")
    async def cooldown_set(
        self,
        ctx,
        job,
        time: commands.TimedeltaConverter(
            minimum=datetime.timedelta(seconds=0),
            maximum=datetime.timedelta(days=2),
            default_unit="minutes",
        ),
    ):
        """Set the cooldown for the work, crime or rob commands. Minimum cooldown is 30 seconds."""
        if job not in ["work", "crime", "rob"]:
            return await ctx.send("Invalid job.")
        seconds = time.total_seconds()
        if seconds < 30:
            return await ctx.send("The miniumum interval is 30 seconds.")
        jobcd = {"work": "workcd", "crime": "crimecd", "rob": "robcd"}
        conf = await self.configglobalcheck(ctx)
        async with conf.cooldowns() as cooldowns:
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
        conf = await self.configglobalcheck(ctx)
        async with conf.payouts() as payouts:
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
        conf = await self.configglobalcheck(ctx)
        async with conf.failrates() as failrates:
            failrates[job] = amount
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="set-fine-rate", usage="<min | max> <amount>")
    async def fine_set(self, ctx, min_or_max: str, amount: int):
        """Set the min or max fine rate for crimes"""
        if min_or_max not in ["max", "min"]:
            return await ctx.send("You must choose between min or max.")
        conf = await self.configglobalcheck(ctx)
        async with conf.fines() as fines:
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
        conf = await self.configglobalcheck(ctx)
        payouts = await conf.payouts()
        wage = random.randint(payouts["work"]["min"], payouts["work"]["max"])
        wagesentence = str(wage) + " " + await bank.get_currency_name(ctx.guild)
        if await conf.defaultreplies():
            job = random.choice(work)
            line = job.format(amount=wagesentence)
            linenum = work.index(job)
        else:
            replies = await conf.replies()
            if not replies["workreplies"]:
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
        conf = await self.configglobalcheck(ctx)
        failrates = await conf.failrates()
        fail = random.randint(1, 100)
        if fail < failrates["crime"]:
            return await self.fine(ctx, "crime")
        payouts = await conf.payouts()
        wage = random.randint(payouts["crime"]["min"], payouts["crime"]["max"])
        wagesentence = str(wage) + " " + await bank.get_currency_name(ctx.guild)
        if await conf.defaultreplies():
            job = random.choice(crimes)
            line = job.format(amount=wagesentence)
            linenum = crimes.index(job)
        else:
            replies = await conf.replies()
            if not replies["crimereplies"]:
                return await ctx.send(
                    "You have custom replies enabled yet haven't added any replies yet."
                )
            job = random.choice(replies["crimereplies"])
            line = job.format(amount=wagesentence)
            linenum = replies["crimereplies"].index(job)
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
        conf = await self.configglobalcheck(ctx)
        failrates = await conf.failrates()
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
    @check_global_setting_admin()
    @commands.command(name="add-reply")
    async def add_reply(self, ctx, job, *, reply: str):
        """Add a custom reply for working or crime. Put {amount} in place of where you want the amount earned to be."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        if "{amount}" not in reply:
            return await ctx.send("{amount} must be present in the reply.")
        conf = await self.configglobalcheck(ctx)
        jobreplies = {"work": "workreplies", "crime": "crimereplies"}
        async with conf.replies() as replies:
            if reply in replies[jobreplies[job]]:
                return await ctx.send("That is already a response.")
            replies[jobreplies[job]].append(reply)
            ind = replies[jobreplies[job]].index(reply)
        await ctx.send("Your reply has been added and is reply ID #{}".format(ind))

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="del-reply")
    async def del_reply(self, ctx, job, *, id: int):
        """Delete a custom reply."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        jobreplies = {"work": "workreplies", "crime": "crimereplies"}
        conf = await self.configglobalcheck(ctx)
        async with conf.replies() as replies:
            if not replies[jobreplies[job]]:
                return await ctx.send("This job has no custom replies.")
            if id > len(replies[jobreplies[job]]):
                return await ctx.send("Invalid ID.")
            replies[jobreplies[job]].pop(id)
        await ctx.send("Your reply has been removed")

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="list-replies")
    async def list_reply(self, ctx, job):
        """List custom replies."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        jobreplies = {"work": "workreplies", "crime": "crimereplies"}
        conf = await self.configglobalcheck(ctx)
        async with conf.replies() as replies:
            if not replies[jobreplies[job]]:
                return await ctx.send("This job has no custom replies.")
            a = chunks(replies[jobreplies[job]], 10)
            embeds = []
            for item in a:
                items = []
                for i, strings in enumerate(item):
                    items.append(f"Reply {i}: {strings}")
                embed = discord.Embed(colour=discord.Color.red(), description="\n".join(items))
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)

    @checks.admin()
    @check_global_setting_admin()
    @commands.command(name="default-replies", usage="<enable | disable>")
    async def default_replies(self, ctx, enable: bool):
        """Whether to use the default replies to work and crime."""
        conf = await self.configglobalcheck(ctx)
        if enable:
            await ctx.send("Default replies are enabled.")
            await conf.defaultreplies.set(enable)
        else:
            await ctx.send("Default replies are now disabled.")
            await conf.defaultreplies.set(enable)

    @commands.command()
    async def cooldowns(self, ctx):
        """List all the current cooldowns."""
        conf = await self.configglobalcheck(ctx)
        cooldowns = await conf.cooldowns()
        workcd = humanize_timedelta(seconds=cooldowns["workcd"])
        robcd = humanize_timedelta(seconds=cooldowns["robcd"])
        crimecd = humanize_timedelta(seconds=cooldowns["crimecd"])
        msg = "Work Cooldown: `{}`\nCrime Cooldown: `{}`\nRob Cooldown: `{}`".format(
            workcd, crimecd, robcd
        )
        await ctx.maybe_send_embed(msg)
