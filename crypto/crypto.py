from typing import Dict, Optional

import aiohttp
from redbot.core import Config, bank, commands
from redbot.core.utils.chat_formatting import box, humanize_number
from tabulate import tabulate

# https://github.com/Flame442/FlameCogs/blob/master/stocks/stocks.py
# A lot of the logic in this is based on Flames stocks, obtained with permission.


async def tokencheck(ctx):
    token = await ctx.bot.get_shared_api_tokens("coinmarketcap")
    return bool(token.get("api_key", False))


class Crypto(commands.Cog):
    """Buy and Sell Crypto"""

    __version__ = "0.0.1"
    __author__ = "flare, Flame and TrustyJAID."

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 95932766180343808, force_registration=True)
        self.config.register_user(crypto={})

    async def get_header(
        self,
    ) -> Optional[
        Dict[str, str]
    ]:  # Original function taken from TrustyJAID with permission, https://github.com/TrustyJAID/Trusty-cogs/blob/ffdb8f77ed888d5bbbfcc3805d860e8dab80741b/conversions/conversions.py#L177
        api_key = (await self.bot.get_shared_api_tokens("coinmarketcap")).get("api_key")
        if api_key:
            return {"X-CMC_PRO_API_KEY": api_key}
        else:
            return None

    async def checkcoins(
        self, base: str
    ) -> dict:  # Attribution to TrustyJAID, https://github.com/TrustyJAID/Trusty-cogs/blob/ffdb8f77ed888d5bbbfcc3805d860e8dab80741b/conversions/conversions.py#L211
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=await self.get_header()) as resp:
                data = await resp.json()
                if resp.status in [400, 401, 403, 429, 500]:
                    return data
        for coin in data["data"]:
            if base.upper() == coin["symbol"].upper() or base.lower() == coin["name"].lower():
                return coin
        return {}

    async def all_coins(self):
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=await self.get_header()) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}

    @commands.group()
    @commands.check(tokencheck)
    async def crypto(self, ctx):
        """Group command for buying/selling crypto

        Exchange rate 1$ = 10 credits."""

    @crypto.command()
    async def buy(self, ctx, coin, *, amount: float):
        """Buy crypto

        Exchange rate 1$ = 10 credits."""
        if amount <= 0:
            await ctx.send("You cannot buy less than 0 coin.")
            return
        coin_data = await self.checkcoins(coin)
        if "status" in coin_data:
            status = coin_data["status"]
            if status["error_code"] in [1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011]:
                await ctx.send(
                    "Something went wrong, the error code is "
                    "{code}\n`{error_message}`".format(
                        code=coin["error_code"], error_message=coin["error_message"]
                    )
                )
                return None
            if status["error_code"] in [1001, 1002]:
                await ctx.send(
                    "The bot owner has not set an API key. "
                    "Please use `{prefix}cryptoapi` to see "
                    "how to create and setup an API key.".format(prefix=ctx.clean_prefix)
                )
                return None
        if coin_data == {}:
            await ctx.send("{} is not in my list of currencies!".format(coin))
            return None
        price = (
            int(float(coin_data["quote"]["USD"]["price"]) * amount)
            if float(coin_data["quote"]["USD"]["price"]) < 1
            else float(coin_data["quote"]["USD"]["price"]) * amount
        )
        inflate_price = price * 10
        inflate_price = max(inflate_price, 1)
        currency = await bank.get_currency_name(ctx.guild)
        try:
            bal = await bank.withdraw_credits(ctx.author, int(inflate_price))
        except ValueError:
            bal = await bank.get_balance(ctx.author)
            await ctx.send(
                f'You cannot afford {humanize_number(amount)} of {coin_data["name"]}.\nIt would have cost {humanize_number(inflate_price)} {currency} ({price} {currency}) however you only have {bal} {currency}!.'
            )
            return
        async with self.config.user(ctx.author).crypto() as coins:
            if coin_data["name"] in coins:
                coins[coin_data["name"]]["amount"] += amount
                coins[coin_data["name"]]["totalcost"] += inflate_price
            else:
                coins[coin_data["name"]] = {"amount": amount, "totalcost": inflate_price}
        await ctx.send(
            f'You\'ve purchased {humanize_number(amount)} of {coin_data["name"]} for {humanize_number(inflate_price)} {currency}. ({humanize_number((float(coin_data["quote"]["USD"]["price"])) * 10)} {currency} each)!'
        )

    @crypto.command()
    async def sell(self, ctx, coin, *, amount: float):
        """Sell crypto

        Exchange rate 1$ = 10 credits."""
        if amount <= 0:
            await ctx.send("You cannot buy less than 0 coin.")
            return
        coin_data = await self.checkcoins(coin)
        if "status" in coin_data:
            status = coin_data["status"]
            if status["error_code"] in [1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011]:
                await ctx.send(
                    "Something went wrong, the error code is "
                    "{code}\n`{error_message}`".format(
                        code=coin["error_code"], error_message=coin["error_message"]
                    )
                )
                return None
            if status["error_code"] in [1001, 1002]:
                await ctx.send(
                    "The bot owner has not set an API key. "
                    "Please use `{prefix}cryptoapi` to see "
                    "how to create and setup an API key.".format(prefix=ctx.clean_prefix)
                )
                return None
        if coin_data == {}:
            await ctx.send("{} is not in my list of currencies!".format(coin))
            return None
        async with self.config.user(ctx.author).crypto() as coins:
            if coin_data["name"] not in coins:
                return await ctx.send(f'You do not have any of {coin_data["name"]}.')
            if amount > coins[coin_data["name"]]["amount"]:
                return await ctx.send(
                    f'You do not have enough of {coin_data["name"]}. '
                    f'You only have {coins[coin_data["name"]]["amount"]}.'
                )
            coins[coin_data["name"]]["amount"] -= amount
            coins[coin_data["name"]]["totalcost"] -= int(
                amount * (coin_data["quote"]["USD"]["price"] * 10)
            )
            if coins[coin_data["name"]]["amount"] == 0:
                del coins[coin_data["name"]]
        bal = await bank.deposit_credits(
            ctx.author, int(amount * (float(coin_data["quote"]["USD"]["price"]) * 10))
        )
        currency = await bank.get_currency_name(ctx.guild)
        await ctx.send(
            f'You sold {humanize_number(amount)} of {coin_data["name"]} for {humanize_number(int(amount * (float(coin_data["quote"]["USD"]["price"]) * 10)))} {currency} '
            f'({humanize_number((float(coin_data["quote"]["USD"]["price"]) * 10))} {currency} each).\nYou now have {humanize_number(bal)} {currency}.'
        )

    @crypto.command(name="list")
    async def _list(self, ctx):
        """List your crypto"""
        coin_data = await self.all_coins()
        if coin_data == {}:
            return await ctx.send("Failed to fetch all coin data.")
        coin_list = {coin["name"]: coin for coin in coin_data["data"]}
        data = await self.config.user(ctx.author).crypto()
        if not data:
            return await ctx.send("You do not have any crypto bought.")
        enddata = []
        for coin in data:
            totalprice = (
                int(data[coin]["amount"] * (coin_list[coin]["quote"]["USD"]["price"] * 10))
                - data[coin]["totalcost"]
            )
            pricestr = (
                f"+{humanize_number(totalprice)}"
                if totalprice > 0
                else f"{humanize_number(totalprice)}"
            )
            enddata.append([coin, data[coin]["amount"], pricestr])
        await ctx.send(
            box(tabulate(enddata, headers=["Coin", "Amount", "Profit/Loss"]), lang="prolog")
        )

    @crypto.command()
    async def price(self, ctx, coin, *, amount: float = None):
        """Price of a crypto"""
        coin_data = await self.checkcoins(coin)
        if "status" in coin_data:
            status = coin_data["status"]
            if status["error_code"] in [1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011]:
                await ctx.send(
                    "Something went wrong, the error code is "
                    "{code}\n`{error_message}`".format(
                        code=coin["error_code"], error_message=coin["error_message"]
                    )
                )
                return None
            if status["error_code"] in [1001, 1002]:
                await ctx.send(
                    "The bot owner has not set an API key. "
                    "Please use `{prefix}cryptoapi` to see "
                    "how to create and setup an API key.".format(prefix=ctx.clean_prefix)
                )
                return None
        currency = await bank.get_currency_name(ctx.guild)
        if coin_data == {}:
            await ctx.send("{} is not in my list of currencies!".format(coin))
            return None
        if amount is None:
            await ctx.send(
                f'1 {coin_data["name"]} is {humanize_number((float(coin_data["quote"]["USD"]["price"]) * 10))} {currency} each. (${humanize_number((float(coin_data["quote"]["USD"]["price"])))})'
            )
            return
        if amount <= 0:
            return await ctx.send("Amount must be greater than 0.")
        await ctx.send(
            f'{humanize_number(amount)} of {coin_data["name"]} is {humanize_number(amount * (float(coin_data["quote"]["USD"]["price"]) * 10))} {currency} each. ({humanize_number(float(coin_data["quote"]["USD"]["price"]) * 10)} {currency} each)'
        )

    @commands.command()
    @commands.is_owner()
    async def cryptoapi(self, ctx):
        """
        Instructions for how to setup the crypto API
        """
        msg = (
            "1. Go to https://coinmarketcap.com/api/ sign up for an account.\n"
            "2. In Dashboard / Overview grab your API Key and enter it with:\n"
            f"`{ctx.prefix}set api coinmarketcap api_key YOUR_KEY_HERE`"
        )
        await ctx.maybe_send_embed(msg)
