from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import discord
import aiohttp
import typing
import datetime


class Covid(commands.Cog):
    """Covid-19 (Novel Coronavirus Stats)."""

    __version__ = "0.0.6"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.api = "https://corona.lmao.ninja"
        self.newsapi = "https://newsapi.org/v2/top-headlines?q=COVID&sortBy=publishedAt&pageSize=100&country={}&apiKey={}&page=1"
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.newsapikey = None

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
            if response.status == 200:
                try:
                    if isinstance(data, dict):
                        if data.get("message") is not None:
                            return {"failed": data["message"]}
                    return data
                except aiohttp.ServerTimeoutError:
                    return {
                        "failed": "Their appears to be an issue with the API. Please try again later."
                    }
            else:
                return {"failed": data["message"]}

    @commands.command(hidden=True)
    async def covidcountries(self, ctx):
        """Countries supported by covidnews"""
        await ctx.send(
            "Valid country codes are:\nae ar at au be bg br ca ch cn co cu cz de eg fr gb gr hk hu id ie il in it jp kr lt lv ma mx my ng nl no nz ph pl pt ro rs ru sa se sg si sk th tr tw ua us ve za"
        )

    @commands.command()
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
        embeds = []
        for i, article in enumerate(data["articles"], 1):
            embed = discord.Embed(
                title=article["title"],
                color=ctx.author.color,
                description=f"[Click Here for Full Article]({article['url']})\n\n{article['description']}",
                timestamp=datetime.datetime.fromisoformat(article["publishedAt"].replace("Z", "")),
            )
            embed.set_image(url=article["urlToImage"])
            embed.set_author(name=f"{article['author']} - {article['source']['name']}")
            embed.set_footer(text=f"Article {i}/{data['totalResults']}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=90)

    @commands.command()
    async def covidsetup(self, ctx):
        """Instructions on how to setup covid related APIs."""
        msg = "**Covid News API Setup**\n**1**. Visit https://newsapi.org and register for an API.\n**2**. Use the following command: {}set api newsapi key <api_key_here>\n**3**. Reload the cog if it doesnt work immediately.".format(
            ctx.prefix
        )
        await ctx.maybe_send_embed(msg)

    @commands.group(invoke_without_command=True)
    async def covid(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19."""
        if not country:
            async with ctx.typing():
                data = await self.get(self.api + "/all")
            if isinstance(data, dict):
                if data.get("failed") is not None:
                    return await ctx.send(data.get("failed"))
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(color=ctx.author.color, title="Covid-19 Global Statistics")
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            await ctx.send(embed=embed)
        else:
            async with ctx.typing():
                data = await self.get(self.api + "/countries/{}".format(country))
            error = data.get("failed")
            if error is not None:
                return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | {} Statistics".format(data["country"])
            )
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def todaycases(self, ctx):
        """Show the highest cases from countrys today"""
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayCases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Cases Today | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def today(self, ctx):
        """Statistics for today."""
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            todayDeaths = 0
            todayCases = 0
            for i in range(len(data)):
                todayDeaths += int(data[i]["todayDeaths"])
                todayCases += int(data[i]["todayCases"])
            embed = discord.Embed(title="Covid-19 Statistics for Today", color=ctx.author.color)
            embed.add_field(name="Cases Today", value=humanize_number(todayCases))
            embed.add_field(name="Deaths Today", value=humanize_number(todayDeaths))
            await ctx.send(embed=embed)

    @covid.command()
    async def todaydeaths(self, ctx):
        """Show the highest deaths from countrys today"""
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayDeaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Deaths Today | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def highestcases(self, ctx):
        """Show the highest cases from countrys overall"""
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["cases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Cases Overall | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def highestdeaths(self, ctx):
        """Show the highest deaths from countrys overall"""
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=deaths")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["deaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Deaths Overall | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def topcases(self, ctx, amount: int = 6):
        """Show X countries with top amount of cases. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["cases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Cases ".format(amount)
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def topcasestoday(self, ctx, amount: int = 6):
        """Show X countries with top amount of cases today. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayCases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Cases Today ".format(amount)
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def topdeaths(self, ctx, amount: int = 6):
        """Show X countries with top amount of deaths. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["deaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Deaths ".format(amount)
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def topdeathstoday(self, ctx, amount: int = 6):
        """Show X countries with top amount of deaths today. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayDeaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Deaths Today ".format(amount)
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def state(self, ctx, *, state: str):
        """Show stats for a specific state."""
        async with ctx.typing():
            data = await self.get(self.api + "/states")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            statedata = None
            for i in range(len(data)):
                if data[i]["state"].lower() == state.lower():
                    statedata = i
            if statedata is None:
                return await ctx.send("No statistics/State not found.")
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | USA | {} Statistics".format(data[statedata]["state"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[statedata]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[statedata]["deaths"]))
            embed.add_field(
                name="Cases Today", value=humanize_number(data[statedata]["todayCases"])
            )
            embed.add_field(
                name="Deaths Today", value=humanize_number(data[statedata]["todayDeaths"])
            )
            embed.add_field(name="Active Cases", value=humanize_number(data[statedata]["active"]))
            await ctx.send(embed=embed)
