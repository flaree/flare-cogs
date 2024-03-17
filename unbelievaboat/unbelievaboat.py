import datetime
import logging
import random
from abc import ABC
from io import BytesIO
from typing import Literal, Optional

import discord
import tabulate
from redbot.core import Config, bank, checks, commands
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.chat_formatting import humanize_number, humanize_timedelta, pagify

from .checks import check_global_setting_admin, wallet_disabled_check
from .defaultreplies import crimes, work
from .functions import roll
from .roulette import Roulette
from .settings import SettingsMixin
from .wallet import Wallet

log = logging.getLogger("red.flare.unbelievaboat")


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """This allows the metaclass used for proper type detection to coexist with discord.py's
    metaclass."""


class Unbelievaboat(Wallet, Roulette, SettingsMixin, commands.Cog, metaclass=CompositeMetaClass):
    """Unbelievaboat Commands."""

    __version__ = "0.5.10"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        defaults = {
            "cooldowns": {
                "workcd": 14400,
                "crimecd": 14400,
                "robcd": 86400,
                "withdrawcd": 1,
                "depositcd": 1,
            },
            "defaultreplies": True,
            "replies": {"crimereplies": [], "workreplies": []},
            "rob": [],
            "payouts": {"crime": {"max": 300, "min": 10}, "work": {"max": 250, "min": 10}},
            "failrates": {"crime": 50, "rob": 70},
            "fines": {"max": 250, "min": 10},
            "interest": 5,
            "disable_wallet": False,
            "roulette_toggle": True,
            "roulette_time": 60,
            "roulette_payouts": {
                "zero": 36,
                "single": 17,
                "color": 1,
                "dozen": 2,
                "odd_or_even": 1,
                "halfs": 1,
                "column": 2,
            },
            "betting": {"max": 10000, "min": 100},
            "wallet_max": 50000,
        }
        defaults_member = {
            "cooldowns": {
                "workcd": None,
                "crimecd": None,
                "robcd": None,
                "depositcd": None,
                "withdrawcd": None,
            },
            "wallet": 0,
            "winnings": 0,
            "losses": 0,
        }
        self.roulettegames = {}
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(**defaults)
        self.config.register_guild(**defaults)
        self.config.register_member(**defaults_member)
        self.config.register_user(**defaults_member)

    async def red_get_data_for_user(self, *, user_id: int):
        data = await self.config.user_from_id(user_id).all()
        all_members = await self.config.all_members()
        wallets = []
        for guild_id, member_dict in all_members.items():
            if user_id in member_dict:
                usr = await self.config.member_from_ids(guild_id, user_id).all()
                wallets.append(guild_id, usr["wallet"])
        contents = f"Unbelievaboat Account for Discord user with ID {user_id}:\n**Global**\n- Wallet: {data['wallet']}\n"
        if wallets:
            contents += "**Guilds**"
            for bal in wallets:
                contents += f"Guild: {bal[0]} | Wallet: {bal[1]}"
        return {"user_data.txt": BytesIO(contents.encode())}

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        await self.config.user_from_id(user_id).clear()
        all_members = await self.config.all_members()
        for guild_id, member_dict in all_members.items():
            if user_id in member_dict:
                await self.config.member_from_ids(guild_id, user_id).clear()

    async def configglobalcheck(self, ctx):
        return self.config if await bank.is_global() else self.config.guild(ctx.guild)

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
                cd[job] = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            return True
        time = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) - cd[job]
        if time < jobcd[job]:
            return (False, humanize_timedelta(seconds=jobcd[job] - time))
        async with userconf.cooldowns() as cd:
            cd[job] = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        return True

    async def fine(self, ctx, job):
        conf = await self.configglobalcheck(ctx)
        fines = await conf.fines()
        randint = random.randint(fines["min"], fines["max"])
        amount = str(humanize_number(randint)) + " " + await bank.get_currency_name(ctx.guild)
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
        elif await bank.can_spend(ctx.author, randint):
            await bank.withdraw_credits(ctx.author, randint)
            embed = discord.Embed(
                colour=discord.Color.red(),
                description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}.",
            )
        else:
            if await bank.can_spend(ctx.author, randint):
                await bank.withdraw_credits(ctx.author, randint)
                embed = discord.Embed(
                    colour=discord.Color.red(),
                    description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}.",
                )
            else:
                await bank.set_balance(ctx.author, 0)
                embed = discord.Embed(
                    colour=discord.Color.red(),
                    description=f"\N{NEGATIVE SQUARED CROSS MARK} You were caught by the police and fined {amount}. You did not have enough cash to pay the fine and are now bankrupt.",
                )
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    async def cdnotice(self, user, cooldown, job):
        response = {
            "work": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot work for another {cooldown}.",
            "crime": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot commit a crime for another {cooldown}.",
            "rob": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot rob a person for another {cooldown}.",
            "withdraw": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot withdraw any more cash for another {cooldown}.",
            "deposit": f"\N{NEGATIVE SQUARED CROSS MARK} You cannot deposit any more cash for another {cooldown}.",
        }
        embed = discord.Embed(colour=discord.Color.red(), description=response[job])
        embed.set_author(name=user, icon_url=user.display_avatar)
        return embed

    @checks.admin_or_permissions(manage_guild=True)
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.command(aliases=["addcashrole"])
    async def addmoneyrole(
        self, ctx, amount: int, role: discord.Role, destination: Optional[str] = "wallet"
    ):
        """Add money to the balance of all users within a role.

        Valid arguements are 'banks' or 'wallet'.
        """
        if destination.lower() not in ["bank", "wallet"]:
            return await ctx.send(
                "You've supplied an invalid destination, you can choose to add it to a bank or their wallet.\nIf no destination is supplied it will default to their wallet."
            )

        failedmsg = ""
        if destination.lower() == "bank":
            for user in role.members:
                try:
                    await bank.deposit_credits(user, amount)
                except (ValueError, TypeError) as e:
                    if isinstance(e, ValueError):
                        log.debug(f"Failed to add money to {user} - invalid amount.")
                    else:
                        log.debug(f"Failed to add money to {user} - deposit amount is not an int.")
                except BalanceTooHigh as e:
                    await bank.set_balance(ctx.author, e.max_balance)
                    failedmsg += f"Failed to add {amount} to {user} due to the max wallet balance limit. Their cash has been set to the max balance.\n"
        else:
            for user in role.members:
                try:
                    await self.walletdeposit(ctx, user, amount)
                except ValueError:
                    failedmsg += f"Failed to add {amount} to {user} due to the max wallet balance limit. Their cash has been set to the max balance.\n"
        if failedmsg:
            for page in pagify(failedmsg):
                await ctx.send(page)
        await ctx.tick()

    @checks.admin_or_permissions(manage_guild=True)
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.command(aliases=["removecashrole"])
    async def removemoneyrole(
        self, ctx, amount: int, role: discord.Role, destination: Optional[str] = "wallet"
    ):
        """Remove money from the bank balance of all users within a role.

        Valid arguements are 'banks' or 'wallet'.
        """
        if destination.lower() not in ["bank", "wallet"]:
            return await ctx.send(
                "You've supplied an invalid destination, you can choose to add it to a bank or their wallet.\nIf no destination is supplied it will default to their wallet."
            )
        if destination.lower() == "bank":
            for user in role.members:
                try:
                    await bank.withdraw_credits(user, amount)
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
        if ctx.assume_yes:
            return await ctx.send("This command can't be scheduled.")
        cdcheck = await self.cdcheck(ctx, "workcd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "work")
            return await ctx.send(embed=embed)
        conf = await self.configglobalcheck(ctx)
        payouts = await conf.payouts()
        wage = random.randint(payouts["work"]["min"], payouts["work"]["max"])
        wagesentence = str(humanize_number(wage)) + " " + await bank.get_currency_name(ctx.guild)
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
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Reply #{}".format(linenum))
        if not await self.walletdisabledcheck(ctx):
            try:
                await self.walletdeposit(ctx, ctx.author, wage)
            except ValueError:
                embed.description += f"\nYou've reached the maximum amount of {await bank.get_currency_name(ctx.guild)}s in your wallet!"
        else:
            try:
                await bank.deposit_credits(ctx.author, wage)
            except BalanceTooHigh as e:
                await bank.set_balance(ctx.author, e.max_balance)
                embed.description += f"\nYou've reached the maximum amount of {await bank.get_currency_name(ctx.guild)}s in your bank!"

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def crime(self, ctx):
        """Commit a crime, more risk but higher payout."""
        if ctx.assume_yes:
            return await ctx.send("This command can't be scheduled.")
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
        wagesentence = str(humanize_number(wage)) + " " + await bank.get_currency_name(ctx.guild)
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
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Reply #{}".format(linenum))
        if not await self.walletdisabledcheck(ctx):
            try:
                await self.walletdeposit(ctx, ctx.author, wage)
            except ValueError:
                embed.description += f"\nYou've reached the maximum amount of {await bank.get_currency_name(ctx.guild)}s in your wallet!"
        else:
            try:
                await bank.deposit_credits(ctx.author, wage)
            except BalanceTooHigh as e:
                await bank.set_balance(ctx.author, e.max_balance)
                embed.description += f"\nYou've reached the maximum amount of {await bank.get_currency_name(ctx.guild)}s in your bank!"
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @wallet_disabled_check()
    @commands.bot_has_permissions(embed_links=True)
    async def rob(self, ctx, user: discord.Member):
        """Rob another user."""
        if ctx.assume_yes:
            return await ctx.send("This command can't be scheduled.")
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
            if finechance <= 5:
                return await self.fine(ctx, "rob")
            embed = discord.Embed(
                colour=discord.Color.red(),
                description=f"You steal {user.name}'s wallet but there was nothing of value inside.",
                timestamp=ctx.message.created_at,
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            return await ctx.send(embed=embed)
        modifier = roll()
        stolen = random.randint(1, int(userbalance * modifier) + 1)
        embed = discord.Embed(
            colour=discord.Color.green(),
            description=f"You steal {user.name}'s wallet and find {humanize_number(stolen)} inside.",
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        try:
            await self.walletdeposit(ctx, ctx.author, stolen)
            await self.walletremove(user, stolen)
        except ValueError:
            embed.description += "\nAfter stealing the cash, you notice your wallet is now full!"

        await ctx.send(embed=embed)
