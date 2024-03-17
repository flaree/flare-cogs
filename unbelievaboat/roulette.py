import asyncio
import datetime
import random

import discord
import tabulate
from redbot.core import bank, checks, commands
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.chat_formatting import box, humanize_number, humanize_timedelta

from .abc import MixinMeta
from .checks import check_global_setting_admin, roulette_disabled_check, wallet_disabled_check

NUMBERS = {
    0: "green",
    1: "red",
    3: "red",
    5: "red",
    7: "red",
    9: "red",
    12: "red",
    14: "red",
    16: "red",
    18: "red",
    19: "red",
    21: "red",
    23: "red",
    25: "red",
    27: "red",
    30: "red",
    32: "red",
    34: "red",
    36: "red",
    2: "black",
    4: "black",
    6: "black",
    8: "black",
    10: "black",
    11: "black",
    13: "black",
    15: "black",
    17: "black",
    20: "black",
    22: "black",
    24: "black",
    26: "black",
    28: "black",
    29: "black",
    31: "black",
    33: "black",
    35: "black",
}

EMOJIS = {"black": "\u2B1B", "red": "\U0001F7E5", "green": "\U0001F7E9"}

COLUMNS = [
    [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
    [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
    [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
]

BET_TYPES = {
    "red": "color",
    "black": "color",
    "1st dozen": "dozen",
    "2nd dozen": "dozen",
    "3rd dozen": "dozen",
    "odd": "odd_or_even",
    "even": "odd_or_even",
    "1st half": "halfs",
    "2nd half": "halfs",
    "1st column": "column",
    "2nd column": "column",
    "3rd column": "column",
}


class Roulette(MixinMeta):
    """Roulette Game."""

    async def roulettewithdraw(self, ctx, bet):
        if not await self.walletdisabledcheck(ctx):
            await self.walletwithdraw(ctx.author, bet)
        else:
            await bank.withdraw_credits(ctx.author, bet)

    async def betting(self, ctx, bet, _type):
        try:
            _type = int(_type)
        except ValueError:
            pass
        if isinstance(_type, int):
            if _type < 0 or _type > 36:
                return {"failed": "Bet must be between 0 and 36."}
            if _type == 0:
                for better in self.roulettegames[ctx.guild.id]["zero"]:
                    if better.get(_type, False) and better[_type]["user"] == ctx.author.id:
                        return {"failed": "You cannot make duplicate bets."}
                try:
                    await self.roulettewithdraw(ctx, bet)
                except ValueError:
                    return {"failed": "You do not have enough funds to complete this bet."}
                self.roulettegames[ctx.guild.id]["zero"].append(
                    {_type: {"user": ctx.author.id, "amount": bet}}
                )
                return {"sucess": 200}
            for better in self.roulettegames[ctx.guild.id]["number"]:
                if better.get(_type, False) and better[_type]["user"] == ctx.author.id:
                    return {"failed": "You cannot make duplicate bets."}
            self.roulettegames[ctx.guild.id]["number"].append(
                {_type: {"user": ctx.author.id, "amount": bet}}
            )
            try:
                await self.roulettewithdraw(ctx, bet)
            except ValueError:
                return {"failed": "You do not have enough funds to complete this bet."}
            return {"sucess": 200}
        if _type.lower() in BET_TYPES:
            for better in self.roulettegames[ctx.guild.id][BET_TYPES[_type.lower()]]:
                if (
                    better.get(_type.lower(), False)
                    and better[_type.lower()]["user"] == ctx.author.id
                ):
                    return {"failed": "You cannot make duplicate bets."}
            try:
                await self.roulettewithdraw(ctx, bet)
            except ValueError:
                return {"failed": "You do not have enough funds to complete this bet."}
            self.roulettegames[ctx.guild.id][BET_TYPES[_type.lower()]].append(
                {_type.lower(): {"user": ctx.author.id, "amount": bet}}
            )
            return {"sucess": 200}
        return {"failed": "Not a valid option"}

    async def payout(self, ctx, winningnum, bets):
        msg = []
        conf = await self.configglobalcheck(ctx)
        payouts = await conf.roulette_payouts()
        color = NUMBERS[winningnum]
        odd_even = "odd" if winningnum % 2 != 0 else "even"
        half = "1st half" if winningnum <= 18 else "2nd half"
        dozen = "N/A"
        if bets["dozen"]:
            if winningnum == 0:
                dozen = "No dozen winning bet."
            elif winningnum <= 12:
                dozen = "1st dozen"
            elif winningnum <= 24:
                dozen = "2nd dozen"
            else:
                dozen = "3rd dozen"
        column = "N/A"
        if bets["column"]:
            if winningnum == 0:
                pass
            elif winningnum in COLUMNS[0]:
                column = "1st column"
            elif winningnum in COLUMNS[1]:
                column = "2nd column"
            else:
                column = "3rd column"
        payout_types = {
            "zero": winningnum,
            "color": color,
            "single": winningnum,
            "odd_or_even": odd_even,
            "halfs": half,
            "dozen": dozen,
            "column": column,
        }
        for bettype, value in payout_types.items():
            for bet in bets[bettype]:
                bet_type = list(bet.keys())[0]
                if bet_type == value:
                    betinfo = list(bet.values())[0]
                    user = ctx.guild.get_member(betinfo["user"])
                    payout = betinfo["amount"] + (betinfo["amount"] * payouts[bettype])
                    if not await self.walletdisabledcheck(ctx):
                        user_conf = await self.configglobalcheckuser(user)
                        wallet = await user_conf.wallet()
                        try:
                            await self.walletdeposit(ctx, user, payout)
                        except ValueError:
                            max_bal = await conf.wallet_max()
                            payout = max_bal - wallet
                    else:
                        try:
                            await bank.deposit_credits(user, payout)
                        except BalanceTooHigh as e:
                            payout = e.max_bal - await bank.get_balance(user)
                            await bank.set_balance(user, e.max_bal)
                    msg.append([bet_type, humanize_number(payout), user.display_name])
        return msg

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @roulette_disabled_check()
    async def roulette(self, ctx, amount: int, *, bet):
        """Bet on the roulette wheel.

        **Current supported bets**:
        Single   - Any single number.
        Colors   - Red/Black
        Halfs    - 1st/2nd half
        Even Odd - Even or Odd
        Dozens   - 1st/2nd/3rd Dozen (Groups of 12)
        Colums   - 1st/2nd/3rd Column.
        - This is based on the English version of the roulette wheel.
        """
        if ctx.guild.id not in self.roulettegames:
            return await ctx.send(
                "Start a roulette game using {}roulette start".format(ctx.prefix)
            )
        if self.roulettegames[ctx.guild.id]["started"]:
            return await ctx.send("The wheel is already spinning.")
        conf = await self.configglobalcheck(ctx)
        betting = await conf.betting()
        minbet, maxbet = betting["min"], betting["max"]
        if minbet != -1:
            if amount < minbet:
                return await ctx.send(f"Your bet must be greater than {humanize_number(minbet)}.")
        if maxbet != -1:
            if amount > maxbet:
                return await ctx.send(f"Your bet must be less than {humanize_number(maxbet)}.")
        betret = await self.betting(ctx, amount, bet)
        if betret.get("failed") is not None:
            return await ctx.send(betret["failed"])
        await ctx.send(
            f"You've placed a {humanize_number(amount)} {await bank.get_currency_name(ctx.guild)} bet on {bet}."
        )

    @roulette_disabled_check()
    @roulette.command(name="start")
    async def roulette_start(self, ctx):
        """Start a game of roulette."""
        if ctx.guild.id not in self.roulettegames:
            self.roulettegames[ctx.guild.id] = {
                "zero": [],
                "color": [],
                "single": [],
                "dozen": [],
                "odd_or_even": [],
                "halfs": [],
                "column": [],
                "started": False,
            }
        else:
            return await ctx.send("There is already a roulette game on.")
        conf = await self.configglobalcheck(ctx)
        time = await conf.roulette_time()
        await ctx.send(
            "The roulette wheel will be spun in {} seconds.".format(time), delete_after=time
        )
        async with ctx.typing():
            await asyncio.sleep(time)
        self.roulettegames[ctx.guild.id]["started"] = True
        emb = discord.Embed(
            color=discord.Color.red(),
            title="Roulette Wheel",
            description="The wheel begins to spin.",
        )
        msg = await ctx.send(embed=emb)
        await asyncio.sleep(random.randint(3, 8))
        number = random.randint(0, 36)
        payouts = await self.payout(ctx, number, self.roulettegames[ctx.guild.id])
        emoji = EMOJIS[NUMBERS[number]]
        emb = discord.Embed(
            color=discord.Color.red(),
            title="Roulette Wheel",
            description="The wheel lands on {} {} {}\n\n**Winnings**\n{}".format(
                NUMBERS[number],
                number,
                emoji,
                box(
                    tabulate.tabulate(payouts, headers=["Bet", "Amount Won", "User"]),
                    lang="prolog",
                )
                if payouts
                else "None.",
            ),
        )
        await msg.edit(embed=emb)
        del self.roulettegames[ctx.guild.id]

    @checks.admin_or_permissions(manage_guild=True)
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.group()
    async def rouletteset(self, ctx):
        """Manage settings for roulette."""

    @roulette_disabled_check()
    @check_global_setting_admin()
    @commands.guild_only()
    @rouletteset.command()
    async def time(
        self,
        ctx,
        time: commands.TimedeltaConverter(
            minimum=datetime.timedelta(seconds=30),
            maximum=datetime.timedelta(minutes=5),
            default_unit="seconds",
        ),
    ):
        """Set the time for roulette wheel to start spinning."""
        seconds = time.total_seconds()
        conf = await self.configglobalcheck(ctx)
        await conf.roulette_time.set(seconds)
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @rouletteset.command()
    async def toggle(self, ctx):
        """Toggle roulette on and off."""
        conf = await self.configglobalcheck(ctx)
        toggle = await conf.roulette_toggle()
        if toggle:
            await conf.roulette_toggle.set(False)
            await ctx.send("Roulette has been disabled.")
        else:
            await conf.roulette_toggle.set(True)
            await ctx.send("Roulette has been enabled.")

    @roulette_disabled_check()
    @check_global_setting_admin()
    @commands.guild_only()
    @rouletteset.command()
    async def payouts(self, ctx, type, payout: int):
        """Set payouts for roulette winnings.

        Note: payout is what your prize is multiplied by.
        Valid types:
        zero
        single
        color
        dozen
        odd_or_even
        halfs
        column
        """
        types = ["zero", "single", "color", "dozen", "odd_or_even", "halfs", "column"]
        if type not in types:
            return await ctx.send(
                f"That's not a valid payout type. The available types are `{', '.join(types)}`"
            )
        conf = await self.configglobalcheck(ctx)
        async with conf.roulette_payouts() as payouts:
            payouts[type] = payout
        await ctx.tick()

    @rouletteset.command(name="settings")
    async def _settings(self, ctx):
        """Roulette Settings."""
        conf = await self.configglobalcheck(ctx)
        enabled = await conf.roulette_toggle()
        payouts = await conf.roulette_payouts()
        time = await conf.roulette_time()
        embed = discord.Embed(color=ctx.author.color, title="Roulette Settings")
        embed.add_field(name="Status", value="Enabled" if enabled else "Disabled")
        embed.add_field(name="Time to Spin", value=humanize_timedelta(seconds=time))
        payoutsmsg = "".join(
            f"**{payout.replace('_', ' ').title()}**: {payouts[payout]}\n"
            for payout in sorted(payouts, key=lambda x: payouts[x], reverse=True)
        )

        embed.add_field(name="Payout Settings", value=payoutsmsg)
        await ctx.send(embed=embed)
