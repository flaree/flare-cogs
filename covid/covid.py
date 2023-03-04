import datetime
import typing

import aiohttp
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

from .menus import ArticleFormat, CovidMenu, CovidStateMenu, GenericMenu


class Covid(commands.Cog):
    """Covid-19 (Novel Coronavirus Stats)."""

    __version__ = "0.3.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.api = "https://disease.sh/v3/covid-19"
        self.newsapi = "https://newsapi.org/v2/top-headlines?q=COVID&sortBy=publishedAt&pageSize=100&country={}&apiKey={}&page=1"
        self.session = aiohttp.ClientSession()
        self.newsapikey = None

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    async def initalize(self):
        token = await self.bot.get_shared_api_tokens("newsapi")
        self.newsapikey = token.get("key", None)

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "newsapi":
            self.newsapikey = api_tokens.get("key", None)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get(self, url):
        async with self.session.get(url) as response:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                return {
                    "failed": "Their appears to be an issue with the API. Please try again later."
                }
            if response.status != 200:
                return {"failed": data["message"]}
            try:
                if isinstance(data, dict) and data.get("message") is not None:
                    return {"failed": data["message"]}
                return data
            except aiohttp.ServerTimeoutError:
                return {
                    "failed": "Their appears to be an issue with the API. Please try again later."
                }

    @commands.command(hidden=True)
    async def covidcountries(self, ctx):
        """Countries supported by covidnews."""
        await ctx.send(
            "Valid country codes are:\nae ar at au be bg br ca ch cn co cu cz de eg fr gb gr hk hu id ie il in it jp kr lt lv ma mx my ng nl no nz ph pl pt ro rs ru sa se sg si sk th tr tw ua us ve za"
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def covidnews(self, ctx, countrycode: str):
        """Covid News from a Country - County must be 2-letter ISO 3166-1 code.

        Check [p]covidcountries for a list of all possible country codes supported."""
        async with ctx.typing():
            data = await self.get(self.newsapi.format(countrycode, self.newsapikey))
        if data.get("failed") is not None:
            return await ctx.send(data.get("failed"))
        if data["totalResults"] == 0:
            return await ctx.send(
                "No results found, ensure you're looking up the correct country code. Check {}covidcountries for a list.".format(
                    ctx.prefix
                )
            )
        await GenericMenu(source=ArticleFormat(data["articles"]), ctx=ctx,).start(
            ctx=ctx,
            wait=False,
        )

    @commands.command()
    @commands.is_owner()
    async def covidsetup(self, ctx):
        """Instructions on how to setup covid related APIs."""
        msg = "**Covid News API Setup**\n**1**. Visit https://newsapi.org and register for an API.\n**2**. Use the following command: {}set api newsapi key <api_key_here>\n**3**. Reload the cog if it doesnt work immediately.".format(
            ctx.prefix
        )
        await ctx.maybe_send_embed(msg)

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def covid(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19 or countries if provided.

        Supports multiple countries seperated by a comma.
        Example: [p]covid Ireland, England
        """
        if not country:
            async with ctx.typing():
                data = await self.get(self.api + "/all")
            if isinstance(data, dict) and data.get("failed") is not None:
                return await ctx.send(data.get("failed"))
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 Global Statistics",
                timestamp=datetime.datetime.utcfromtimestamp(data["updated"] / 1000),
            )
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            embed.add_field(name="Critical", value=humanize_number(data["critical"]))
            embed.add_field(name="Active", value=humanize_number(data["active"]))
            embed.add_field(
                name="Affected Countries", value=humanize_number(data["affectedCountries"])
            )
            embed.add_field(name="Cases Today", value=humanize_number(data["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data["todayDeaths"]))
            embed.add_field(name="Recovered Today", value=humanize_number(data["todayRecovered"]))
            embed.add_field(name="Total Tests", value=humanize_number(data["tests"]))
            await ctx.send(embed=embed)
        else:
            async with ctx.typing():
                data = await self.get(self.api + "/countries/{}".format(country))
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
                data = [data]
            if not data:
                return await ctx.send("No data available.")
            await GenericMenu(source=CovidMenu(data), ctx=ctx, type="Today").start(
                ctx=ctx,
                wait=False,
            )

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def yesterday(self, ctx, *, country: str):
        """Show the statistics from yesterday for countries.

        Supports multiple countries seperated by a comma.
        Example: [p]covid yesterday Ireland, England
        """
        async with ctx.typing():
            data = await self.get(self.api + "/countries/{}?yesterday=1".format(country))
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
                data = [data]
            if not data:
                return await ctx.send("No data available.")
            await GenericMenu(source=CovidMenu(data), ctx=ctx, type="Yesterday").start(
                ctx=ctx,
                wait=False,
            )

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def todaycases(self, ctx):
        """Show the highest cases from countrys today."""
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=todayCases")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Highest Cases Today | {}".format(data[0]["country"]),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def todaydeaths(self, ctx):
        """Show the highest deaths from countrys today."""
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=todayDeaths")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Highest Deaths Today | {}".format(data[0]["country"]),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def highestcases(self, ctx):
        """Show the highest cases from countrys overall."""
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=cases")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Highest Cases Overall | {}".format(data[0]["country"]),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def highestdeaths(self, ctx):
        """Show the highest deaths from countrys overall."""
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=deaths")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Highest Deaths Overall | {}".format(data[0]["country"]),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def topcases(self, ctx, amount: int = 6):
        """Show X countries with top amount of cases.

        Defaults to 6.
        """
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=cases")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Top {} Cases ".format(amount),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def topcasestoday(self, ctx, amount: int = 6):
        """Show X countries with top amount of cases today.

        Defaults to 6.
        """
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=todayCases")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Top {} Cases Today ".format(amount),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def topdeaths(self, ctx, amount: int = 6):
        """Show X countries with top amount of deaths.

        Defaults to 6.
        """
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=deaths")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Top {} Deaths ".format(amount),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def topdeathstoday(self, ctx, amount: int = 6):
        """Show X countries with top amount of deaths today.

        Defaults to 6.
        """
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=todayDeaths")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 | Top {} Deaths Today ".format(amount),
                timestamp=datetime.datetime.utcfromtimestamp(data[0]["updated"] / 1000),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def state(self, ctx, *, states: str):
        """Show stats for specific states.

        Supports multiple countries seperated by a comma.
        Example: [p]covid state New York, California
        """
        if not states:
            return await ctx.send_help()
        async with ctx.typing():
            states = ",".join(states.split(", "))
            data = await self.get(self.api + "/states/{}".format(states))
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
                data = [data]
            if not data:
                return await ctx.send("No data available.")
            await GenericMenu(source=CovidStateMenu(data), ctx=ctx, type="Today").start(
                ctx=ctx,
                wait=False,
            )

    @state.command(name="yesterday")
    @commands.bot_has_permissions(embed_links=True)
    async def _yesterday(self, ctx, *, states: str):
        """Show stats for yesterday for specific states.

        Supports multiple countries seperated by a comma.
        Example: [p]covid state yesterday New York, California.
        """
        async with ctx.typing():
            states = ",".join(states.split(", "))
            data = await self.get(self.api + "/states/{}?yesterday=1".format(states))
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
                data = [data]
            if not data:
                return await ctx.send("No data available.")
            await GenericMenu(source=CovidStateMenu(data), ctx=ctx, type="Yesterday").start(
                ctx=ctx,
                wait=False,
            )

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def continent(self, ctx, *, continent: str):
        """Stats about Covid-19 for a particular continent.

        Example: [p]covid continent europe
        """
        async with ctx.typing():
            data = await self.get(self.api + f"/continents/{continent}")
        if isinstance(data, dict) and data.get("failed") is not None:
            return await ctx.send(data.get("failed"))
        if not data:
            return await ctx.send("No data available.")

        embed = discord.Embed(
            color=await self.bot.get_embed_color(ctx.channel),
            title=f"Covid-19 {continent.title()} Statistics",
            timestamp=datetime.datetime.utcfromtimestamp(data["updated"] / 1000),
        )
        embed.add_field(name="Cases", value=humanize_number(data["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
        embed.add_field(name="Critical", value=humanize_number(data["critical"]))
        embed.add_field(name="Active", value=humanize_number(data["active"]))
        embed.add_field(name="Cases Today", value=humanize_number(data["todayCases"]))
        embed.add_field(name="Deaths Today", value=humanize_number(data["todayDeaths"]))
        embed.add_field(name="Recovered Today", value=humanize_number(data["todayRecovered"]))
        embed.add_field(name="Total Tests", value=humanize_number(data["tests"]))
        await ctx.send(embed=embed)

    @covid.command()
    @commands.bot_has_permissions(embed_links=True)
    async def vaccine(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19 vaccinate data globally or per country.

        Example: [p]covid vaccine
        [p]covid vaccine ireland
        """
        if not country:
            async with ctx.typing():
                data = await self.get(self.api + "/vaccine/coverage")
            if isinstance(data, dict) and data.get("failed") is not None:
                return await ctx.send(data.get("failed"))
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title="Covid-19 Global Vaccine Statistics",
            )
            msg = "".join(
                f"{datetime.datetime.strptime(day, '%m/%d/%y').strftime('%d-%m-%Y')}: {humanize_number(data[day])}\n"
                for day in data
            )

        else:
            async with ctx.typing():
                data = await self.get(self.api + "/vaccine/coverage/countries/{}".format(country))
            if isinstance(data, dict) and data.get("failed") is not None:
                return await ctx.send(data.get("failed"))
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=await self.bot.get_embed_color(ctx.channel),
                title=f"Covid-19 {data['country']} Vaccine Statistics",
            )
            msg = "".join(
                f"{datetime.datetime.strptime(day, '%m/%d/%y').strftime('%d-%m-%Y')}: {humanize_number(data['timeline'][day])}\n"
                for day in data["timeline"]
            )

        embed.description = f"```{msg}```"
        await ctx.send(embed=embed)
