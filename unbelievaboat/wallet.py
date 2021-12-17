from typing import Union

import discord
from redbot.core import bank, commands
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .checks import check_global_setting_admin, roulette_disabled_check, wallet_disabled_check


class Wallet(MixinMeta):
    """Wallet Commands."""

    async def walletdisabledcheck(self, ctx):
        if await bank.is_global():
            return not await self.config.disable_wallet()
        return not await self.config.guild(ctx.guild).disable_wallet()

    async def walletdeposit(self, ctx, user, amount):
        conf = await self.configglobalcheckuser(user)
        main_conf = await self.configglobalcheck(ctx)
        wallet = await conf.wallet()
        max_bal = await main_conf.wallet_max()
        amount = wallet + amount
        if amount <= max_bal:
            await conf.wallet.set(amount)
        else:
            await conf.wallet.set(max_bal)
            raise ValueError

    async def walletremove(self, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        if amount < wallet:
            await conf.wallet.set(wallet - amount)
        else:
            await conf.wallet.set(0)

    async def walletwithdraw(self, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        if amount < wallet:
            await conf.wallet.set(wallet - amount)
        else:
            raise ValueError

    async def walletset(self, user, amount):
        conf = await self.configglobalcheckuser(user)
        await conf.wallet.set(amount)

    async def bankdeposit(self, ctx, user, amount):
        conf = await self.configglobalcheckuser(user)
        wallet = await conf.wallet()
        deposit = abs(amount)
        if deposit > wallet:
            return await ctx.send("You have insufficent funds to complete this deposit.")
        try:
            await bank.deposit_credits(user, deposit)
            msg = f"You have succesfully deposited {deposit} {await bank.get_currency_name(ctx.guild)} into your bank account."
        except BalanceTooHigh as e:
            deposit = e.max_balance - await bank.get_balance(user)
            await bank.deposit_credits(user, deposit)
            msg = f"Your transaction was limited to {deposit} {e.currency_name} as your bank account has reached the max balance."
        await self.walletset(user, wallet - deposit)
        return await ctx.send(msg)

    async def walletbalance(self, user):
        conf = await self.configglobalcheckuser(user)
        return await conf.wallet()

    async def bankwithdraw(self, ctx, user, amount):
        conf = await self.configglobalcheckuser(user)
        mainconf = await self.configglobalcheck(ctx)
        max_bal = await mainconf.wallet_max()
        wallet = await conf.wallet()
        try:
            if wallet + amount > max_bal:
                return await ctx.send(
                    f"You have attempted to withdraw more cash than the maximum balance allows. The maximum balance is {humanize_number(max_bal)} {await bank.get_currency_name(ctx.guild)}."
                )
            await bank.withdraw_credits(user, amount)
            await self.walletset(user, wallet + amount)
            return await ctx.send(
                f"You have succesfully withdrawn {humanize_number(amount)} {await bank.get_currency_name(ctx.guild)} from your bank account."
            )
        except ValueError:
            return await ctx.send("You have insufficent funds to complete this withdrawal.")

    @commands.group()
    @wallet_disabled_check()
    @commands.guild_only()
    async def wallet(self, ctx):
        """Wallet commands."""

    @wallet.command()
    @commands.guild_only()
    async def balance(self, ctx, user: discord.Member = None):
        """Show the user's wallet balance.

        Defaults to yours.
        """
        if user is None:
            user = ctx.author
        balance = await self.walletbalance(user)
        currency = await bank.get_currency_name(ctx.guild)
        await ctx.send(
            f"{user.display_name}'s wallet balance is {humanize_number(balance)} {currency}"
        )

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
                user_id = f"({acc[0]})" if await ctx.bot.is_owner(ctx.author) else ""
                name = f"{user_id}"
            balance = acc[1]["wallet"]

            if acc[0] != ctx.author.id:
                temp_msg += f"{pos}. {balance: <{bal_len + 5}} {name}\n"

            else:
                temp_msg += f"{pos}. {balance: <{bal_len + 5}} <<{ctx.author.display_name}>>\n"
            if pos % 10 == 0:
                highscores.append(box(temp_msg, lang="md"))
                temp_msg = header
            pos += 1

        if temp_msg != header:
            highscores.append(box(temp_msg, lang="md"))

        if highscores:
            await menu(ctx, highscores, DEFAULT_CONTROLS)

    @wallet_disabled_check()
    @check_global_setting_admin()
    @commands.guild_only()
    @wallet.command(name="set")
    async def _walletset(self, ctx, user: discord.Member, amount: int):
        """Set a users wallet balance."""
        conf = await self.configglobalcheck(ctx)
        maxw = await conf.wallet_max()
        if amount > maxw:
            return await ctx.send(
                f"{user.display_name}'s wallet balance cannot rise above {humanize_number(maxw)} {await bank.get_currency_name(ctx.guild)}."
            )
        await self.walletset(user, amount)
        await ctx.send(
            f"{ctx.author.display_name} has set {user.display_name}'s wallet balance to {humanize_number(amount)} {await bank.get_currency_name(ctx.guild)}."
        )

    @commands.command()
    @wallet_disabled_check()
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def deposit(self, ctx, amount: Union[int, str]):
        """Deposit cash from your wallet to your bank."""
        cdcheck = await self.cdcheck(ctx, "depositcd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "deposit")
            return await ctx.send(embed=embed)
        if isinstance(amount, str):
            if amount != "all":
                return await ctx.send("You must provide a valid number or the string `all`.")
            amount = await self.walletbalance(ctx.author)
        await self.bankdeposit(ctx, ctx.author, amount)

    @commands.command()
    @wallet_disabled_check()
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def withdraw(self, ctx, amount: int):
        """Withdraw cash from your bank to your wallet."""
        cdcheck = await self.cdcheck(ctx, "withdrawcd")
        if isinstance(cdcheck, tuple):
            embed = await self.cdnotice(ctx.author, cdcheck[1], "withdraw")
            return await ctx.send(embed=embed)
        await self.bankwithdraw(ctx, ctx.author, amount)
