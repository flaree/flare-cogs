import datetime
import random
from typing import Optional

import discord
from redbot.core import Config, bank, checks, commands
from redbot.core.utils.chat_formatting import humanize_timedelta, box
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
            admin_roles = set(await ctx.bot.get_admin_role_ids(ctx.guild.id))
            for role in author.roles:
                if role.id in admin_roles:
                    return True
        else:
            return await ctx.bot.is_owner(author)

    return commands.check(predicate)


def wallet_disabled_check():
    async def predicate(ctx):
        if await bank.is_global():
            return await ctx.bot.get_cog("Unbelievaboat").config.disable_wallet()
        return await ctx.bot.get_cog("Unbelievaboat").config.guild(ctx.guild).disable_wallet()

    return commands.check(predicate)


class Unbelievaboat(commands.Cog):
    """Unbelievaboat Commands."""

    __version__ = "0.2.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

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
            "interest": 5,
            "disable_wallet": False,
        }
        defaults_member = {
            "cooldowns": {"workcd": None, "crimecd": None, "robcd": None},
            "wallet": 0,
        }
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(**defaults)
        self.config.register_guild(**defaults)
        self.config.register_member(**defaults_member)
        self.config.register_user(**defaults_member)

    async def configglobalcheck(self, ctx):
        if await bank.is_global():
            return self.config
        return self.config.guild(ctx.guild)

    async def walletdisabledcheck(self, ctx):
        if await bank.is_global():
            return not await self.config.disable_wallet()
        return not await self.config.guild(ctx.guild).disable_wallet()

    def roll(self):
        roll = random.randint(1, 20)
        if roll == 1:
            return 0.005
        if roll > 1 and roll <= 6:
            return 0.03
        if roll > 6 and roll <= 8:
            return 0.10
        if roll > 8 and roll <= 10:
            return 0.20
        if roll > 10 and roll <= 13:
            return 0.25
        if roll > 13 and roll <= 16:
            return 0.4
        if roll > 16 and roll <= 17:
            return 0.655
        if roll > 17 and roll <= 19:
            return 0.8
        if roll == 20:
            return 0.85

    async def walletdeposit(self, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        await conf.wallet.set(wallet + amount)

    async def walletremove(self, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        if amount < wallet:
            await conf.wallet.set(wallet - amount)
        else:
            await conf.wallet.set(0)

    async def walletset(self, user, amount):
        conf = await self.configglobalcheckuser(user)
        await conf.wallet.set(amount)

    async def bankdeposit(self, ctx, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        deposit = abs(amount)
        if deposit > wallet:
            return await ctx.send("You have insufficent funds to complete this deposit.")
        await bank.deposit_credits(user, deposit)
        await self.walletset(user, wallet - deposit)
        return await ctx.send(
            f"You have succesfully deposited {deposit} {await bank.get_currency_name(ctx.guild)} into your bank account."
        )

    async def walletbalance(self, user):
        conf = await self.configglobalcheckuser(user)
        return await conf.wallet()

    async def bankwithdraw(self, ctx, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        try:
            await bank.withdraw_credits(user, amount)
            await self.walletset(user, wallet + amount)
            return await ctx.send(
                f"You have succesfully withdrawn {amount} {await bank.get_currency_name(ctx.guild)} from your bank account."
            )
        except ValueError:
            return await ctx.send("You have insufficent funds to complete this withdrawl.")

    async def configglobalcheckuser(self, user):
        if await bank.is_global():
            return self.config.user(user)
        return self.config.member(user)

    async def cdcheck(self, ctx, job):
        conf = await self.configglobalcheck(ctx)
        userconf = await self.configglobalcheckuser(ctx.author)
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
        userconf = await self.configglobalcheckuser(ctx.author)
        if not await self.walletdisabledcheck(ctx):
            if randint < await userconf.wallet():
                await self.walletremove(ctx.author, randint)
                embed = discord.Embed(
                    colour=discord.Color.red(),
                    description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}.",
                )
            else:
                interestfee = await self.config.guild(ctx.guild).interest()
                fee = int(
                    randint * float(f"1.{interestfee if interestfee >= 10 else f'0{interestfee}'}")
                )
                if await bank.can_spend(ctx.author, fee):
                    await bank.withdraw_credits(ctx.author, fee)
                    embed = discord.Embed(
                        colour=discord.Color.red(),
                        description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}. You did not have enough cash in your wallet and thus it was taken from your bank with a {interestfee}% interest fee ({fee} {await bank.get_currency_name(ctx.guild)}).",
                    )
                else:
                    await bank.set_balance(ctx.author, 0)
                    embed = discord.Embed(
                        colour=discord.Color.red(),
                        description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}. You did not have enough cash to pay the fine and are now bankrupt.",
                    )
        else:
            if await bank.can_spend(ctx.author, randint):
                await bank.withdraw_credits(ctx.author, randint)
                embed = discord.Embed(
                    colour=discord.Color.red(),
                    description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {randint}.",
                )
            else:
                await bank.set_balance(ctx.author, 0)
                embed = discord.Embed(
                    colour=discord.Color.red(),
                    description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}. You did not have enough cash to pay the fine and are now bankrupt.",
                )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @checks.admin()
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.command(name="set-cooldown")
    async def cooldown_set(
        self,
        ctx,
        job,
        *,
        time: commands.TimedeltaConverter(
            minimum=datetime.timedelta(seconds=0),
            maximum=datetime.timedelta(days=2),
            default_unit="minutes",
        ),
    ):
        """Set the cooldown for the work, crime or rob commands. Minimum cooldown is 30 seconds.
        
        The time can be formatted as so `1h30m` etc.
        Valid times are hours, minutes and seconds."""
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
    @commands.guild_only()
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
    @commands.guild_only()
    @commands.command(name="set-wallet", usage="<on_or_off>")
    async def wallet_set(self, ctx, on_or_off: bool):
        """Toggle the wallet on or off."""
        conf = await self.configglobalcheck(ctx)
        if on_or_off:
            await ctx.send("The wallet and rob system has been enabled.")
        else:
            await ctx.send("The wallet and rob system has been disabled.")
        await conf.disable_wallet.set(on_or_off)
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
    @commands.guild_only()
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
    @commands.guild_only()
    @commands.command(name="set-interest-rate", usage="<amount>")
    async def interest_set(self, ctx, amount: int):
        """Set the interest rate if unable to pay a fine from wallet."""
        if amount < 1 or amount > 99:
            return await ctx.send("Amount must be higher than 1 or less than 99")
        await self.config.guild(ctx.guild).interest.set(amount)
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.command(aliases=["addcashrole"])
    async def addmoneyrole(
        self, ctx, amount: int, role: discord.Role, destination: Optional[str] = "wallet"
    ):
        """Add money to the balance of all users within a role.

        Valid arguements are 'banks' or 'wallet'."""
        if destination.lower() not in ["bank", "wallet"]:
            return await ctx.send(
                "You've supplied an invalid destination, you can choose to add it to a bank or their wallet.\nIf no destination is supplied it will default to their wallet."
            )
        if destination.lower() == "bank":
            for user in role.members:
                try:
                    await bank.deposit_credits(user, amount)
                except (ValueError, TypeError):
                    pass
        else:
            for user in role.members:
                await self.walletdeposit(user, amount)
        await ctx.tick()

    @checks.admin()
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.command(aliases=["removecashrole"])
    async def removemoneyrole(
        self, ctx, amount: int, role: discord.Role, destination: Optional[str] = "wallet"
    ):
        """Remove money from the bank balance of all users within a role.

        Valid arguements are 'banks' or 'wallet'."""
        if destination.lower() not in ["bank", "wallet"]:
            return await ctx.send(
                "You've supplied an invalid destination, you can choose to add it to a bank or their wallet.\nIf no destination is supplied it will default to their wallet."
            )
        if destination.lower() == "bank":
            for user in role.members:
                try:
                    await bank.deposit_credits(user, amount)
                except ValueError:
                    await bank.set_balance(user, 0)
        else:
            for user in role.members:
                await self.walletremove(user, amount)
        await ctx.tick()

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
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
            colour=discord.Color.green(), description=line, timestamp=ctx.message.created_at
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Reply #{}".format(linenum))
        if not await self.walletdisabledcheck(ctx):
            await self.walletdeposit(ctx.author, wage)
        else:
            await bank.deposit_credits(ctx.author, wage)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
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
            colour=discord.Color.green(), description=line, timestamp=ctx.message.created_at
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Reply #{}".format(linenum))
        if not await self.walletdisabledcheck(ctx):
            await self.walletdeposit(ctx.author, wage)
        else:
            await bank.deposit_credits(ctx.author, wage)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @wallet_disabled_check()
    @commands.bot_has_permissions(embed_links=True)
    async def rob(self, ctx, user: discord.Member):
        """Rob another user."""
        if user == ctx.author:
            return await ctx.send("Robbing yourself doesn't make much sense.")
        cdcheck = await self.cdcheck(ctx, "robcd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "rob")
            return await ctx.send(embed=embed)
        conf = await self.configglobalcheck(ctx)
        failrates = await conf.failrates()
        fail = random.randint(1, 100)
        if fail < failrates["rob"]:
            return await self.fine(ctx, "rob")
        userbalance = await self.walletbalance(user)
        if userbalance <= 50:
            finechance = random.randint(1, 10)
            if finechance > 5:
                embed = discord.Embed(
                    colour=discord.Color.red(),
                    description="You steal {}'s wallet but there was nothing of value inside.".format(
                        user.name
                    ),
                    timestamp=ctx.message.created_at,
                )
                embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
                return await ctx.send(embed=embed)
            else:
                return await self.fine(ctx, "rob")
        modifier = self.roll()
        stolen = random.randint(1, int(userbalance * modifier))
        await self.walletremove(user, stolen)
        await self.walletdeposit(ctx.author, stolen)
        embed = discord.Embed(
            colour=discord.Color.green(),
            description="You steal {}'s wallet and find {} inside.".format(user.name, stolen),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @checks.admin()
    @commands.guild_only()
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
    @commands.guild_only()
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
    @commands.guild_only()
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
    @commands.guild_only()
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
    @commands.guild_only()
    async def cooldowns(self, ctx):
        """List your remaining cooldowns.."""
        conf = await self.configglobalcheck(ctx)
        userconf = await self.configglobalcheckuser(ctx.author)
        cd = await userconf.cooldowns()
        jobcd = await conf.cooldowns()
        if cd["workcd"] is None:
            workcd = "None"
        else:
            time = int(datetime.datetime.utcnow().timestamp()) - cd["workcd"]
            if time < jobcd["workcd"]:
                workcd = humanize_timedelta(seconds=jobcd["workcd"] - time)
            else:
                workcd = "Ready to use."
        if cd["crimecd"] is None:
            crimecd = "Ready to use."
        else:
            time = int(datetime.datetime.utcnow().timestamp()) - cd["crimecd"]
            if time < jobcd["crimecd"]:
                crimecd = humanize_timedelta(seconds=jobcd["crimecd"] - time)
            else:
                crimecd = "Ready to use."
        if not await self.walletdisabledcheck(ctx):
            if cd["robcd"] is None:
                robcd = "Ready to use."
            else:
                time = int(datetime.datetime.utcnow().timestamp()) - cd["robcd"]
                if time < jobcd["robcd"]:
                    robcd = humanize_timedelta(seconds=jobcd["robcd"] - time)
                else:
                    robcd = "Ready to use."
        else:
            robcd = "Disabled."
        msg = "Work Cooldown: `{}`\nCrime Cooldown: `{}`\nRob Cooldown: `{}`".format(
            workcd, crimecd, robcd
        )
        await ctx.maybe_send_embed(msg)

    @commands.command()
    @check_global_setting_admin()
    @checks.admin()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def settings(self, ctx):
        """Current unbelievaboat settings."""
        conf = await self.configglobalcheck(ctx)
        cooldowns = await conf.cooldowns()
        workcd = humanize_timedelta(seconds=cooldowns["workcd"])
        robcd = humanize_timedelta(seconds=cooldowns["robcd"])
        crimecd = humanize_timedelta(seconds=cooldowns["crimecd"])
        cooldowns = "Work Cooldown: `{}`\nCrime Cooldown: `{}`\nRob Cooldown: `{}`".format(
            workcd, crimecd, robcd
        )
        embed = discord.Embed(colour=ctx.author.colour, title="Unbelievaboat Settings")
        embed.add_field(
            name="Using Default Replies?",
            value="Yes" if await conf.defaultreplies() else "No",
            inline=True,
        )
        payouts = await conf.payouts()
        crimepayout = f"**Max**: {payouts['crime']['max']}\n**Min**: {payouts['crime']['min']}"
        workpayout = f"**Max**: {payouts['work']['max']}\n**Min**: {payouts['work']['min']}"
        embed.add_field(name="Work Payouts", value=workpayout, inline=True)
        embed.add_field(name="Crime Payouts", value=crimepayout, inline=True)
        failrates = await conf.failrates()
        embed.add_field(
            name="Fail Rates",
            value=f"**Crime**: {failrates['crime']}%\n**Rob**: {failrates['rob']}%\n**Interest Fee**: {await self.config.guild(ctx.guild).interest()}%",
            inline=True,
        )
        fines = await conf.fines()
        embed.add_field(
            name="Fines", value=f"**Max**: {fines['max']}\n**Min**: {fines['min']}", inline=True
        )
        embed.add_field(name="Cooldown Settings", value=cooldowns, inline=True)
        walletsettings = await conf.disable_wallet()
        embed.add_field(
            name="Wallet Settings",
            value="Disabled." if not walletsettings else "Enabled",
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.group()
    @wallet_disabled_check()
    @commands.guild_only()
    async def wallet(self, ctx):
        """Wallet commands."""
        pass

    @wallet.command()
    @commands.guild_only()
    async def balance(self, ctx, user=None):
        """Show the user's wallet balance.

        Defaults to yours."""
        if user is None:
            user = ctx.author
        balance = await self.walletbalance(user)
        currency = await bank.get_currency_name(ctx.guild)
        await ctx.send(f"{user.display_name}'s wallet balance is {balance} {currency}")

    @wallet.command()
    @commands.guild_only()
    async def leaderboard(self, ctx, top: int = 10):
        """Print the wallet leaderboard."""
        if top < 1:
            top = 10
        guild = ctx.guild
        if await bank.is_global():
            raw_accounts = await self.config.all_users()
            if guild is not None:
                tmp = raw_accounts.copy()
                for acc in tmp:
                    if not guild.get_member(acc):
                        del raw_accounts[acc]
        else:
            raw_accounts = await self.config.all_members(guild)
        walletlist = sorted(raw_accounts.items(), key=lambda x: x[1]["wallet"], reverse=True)[:top]
        try:
            bal_len = len(str(walletlist[0][1]["wallet"]))

        except IndexError:
            return await ctx.send("There are no users with a wallet balance.")
        pound_len = len(str(len(walletlist)))
        header = "{pound:{pound_len}}{score:{bal_len}}{name:2}\n".format(
            pound="#", name="Name", score="Score", bal_len=bal_len + 6, pound_len=pound_len + 3
        )
        highscores = []
        pos = 1
        temp_msg = header
        for acc in walletlist:
            try:
                name = guild.get_member(acc[0]).display_name
            except AttributeError:
                user_id = ""
                if await ctx.bot.is_owner(ctx.author):
                    user_id = f"({str(acc[0])})"
                name = f"{user_id}"
            balance = acc[1]["wallet"]

            if acc[0] != ctx.author.id:
                temp_msg += f"{f'{pos}.': <{pound_len+2}} {balance: <{bal_len + 5}} {name}\n"

            else:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} "
                    f"{balance: <{bal_len + 5}} "
                    f"<<{ctx.author.display_name}>>\n"
                )
            if pos % 10 == 0:
                highscores.append(box(temp_msg, lang="md"))
                temp_msg = header
            pos += 1

        if temp_msg != header:
            highscores.append(box(temp_msg, lang="md"))

        if highscores:
            await menu(ctx, highscores, DEFAULT_CONTROLS)

    @checks.admin()
    @wallet_disabled_check()
    @check_global_setting_admin()
    @commands.guild_only()
    @wallet.command(name="set")
    async def _walletset(self, ctx, user: discord.Member, amount: int):
        """Set a users wallet balance."""
        await self.walletset(user, amount)
        await ctx.send(
            f"{ctx.author.display_name} has set {user.display_name}'s wallet balance to {amount} {await bank.get_currency_name(ctx.guild)}"
        )

    @commands.command()
    @wallet_disabled_check()
    @commands.guild_only()
    async def deposit(self, ctx, amount: int):
        """Deposit cash from your wallet to your bank."""
        await self.bankdeposit(ctx, ctx.author, amount)

    @commands.command()
    @wallet_disabled_check()
    @commands.guild_only()
    async def withdraw(self, ctx, amount: int):
        """Withdraw cash from your bank to your wallet."""
        await self.bankwithdraw(ctx, ctx.author, amount)
