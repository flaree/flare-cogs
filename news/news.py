from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import discord
import aiohttp
import typing
import datetime
import validators


class News(commands.Cog):
    """News Cog."""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.api = "https://newsapi.org/v2/{}?{}&sortBy=publishedAt&pageSize=100{}&apiKey={}&page=1{}"
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
            data = await response.json()
            if response.status == 200:
                try:
                    return data
                except aiohttp.ServerTimeoutError:
                    return {
                        "failed": "Their appears to be an issue with the API. Please try again later."
                    }
            else:
                return {"failed": data["message"]}

    @commands.group()
    async def news(self, ctx):
        """Group Command for News"""
        pass

    @news.command(hidden=True)
    async def countrycodes(self, ctx):
        """Countries supported by the News Cog"""
        await ctx.send(
            "Valid country codes are:\nae ar at au be bg br ca ch cn co cu cz de eg fr gb gr hk hu id ie il in it jp kr lt lv ma mx my ng nl no nz ph pl pt ro rs ru sa se sg si sk th tr tw ua us ve za"
        )

    @news.command()
    async def top(self, ctx, countrycode: str, *, query: str = None):
        """Top News from a Country - County must be 2-letter ISO 3166-1 code.
        
        Check [p]countrycodes for a list of all possible country codes supported."""
        async with ctx.typing():
            data = await self.get(self.api.format("top-headlines", "q={}".format(query) if query is not None else "", "&country={}".format(countrycode), self.newsapikey, ""))
        if data.get("failed") is not None:
            return await ctx.send(data.get("failed"))
        if data["totalResults"] == 0:
            return await ctx.send(
                "No results found, ensure you're looking up the correct country code. Check {}countrycodes for a list. Alternatively, your query may be returning no results.".format(
                    ctx.prefix
                )
            )
        embeds = []
        total = 15 if len(data["articles"]) > 15 else len(data["articles"])
        for i, article in enumerate(data["articles"][:15], 1):
            embed = discord.Embed(
                title=article["title"],
                color=ctx.author.color,
                description=f"[Click Here for Full Article]({article['url']})\n\n{article['description']}",
                timestamp=datetime.datetime.fromisoformat(article["publishedAt"].replace("Z", "")),
            )
            if validators.url(article["urlToImage"]):
                embed.set_image(url=article["urlToImage"])
            embed.set_author(name=f"{article['author']} - {article['source']['name']}")
            embed.set_footer(text=f"Article {i}/{total}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=90)

    # @news.command(name="global")
    # async def global_all(self, ctx, *, query: str = None):
    #     """News from the World."""
    #     async with ctx.typing():
    #         print(self.api.format("everything", "q={}".format(query) if query is not None else "", "", self.newsapikey, ""))
    #         data = await self.get(self.api.format("everything", "q={}".format(query) if query is not None else "", "", self.newsapikey, ""))
    #     if data.get("failed") is not None:
    #         return await ctx.send(data.get("failed"))
    #     if data["totalResults"] == 0:
    #         return await ctx.send(
    #             "No results found."
    #         )
    #     embeds = []
    #     for i, article in enumerate(data["articles"][:15], 1):
    #         embed = discord.Embed(
    #             title=article["title"],
    #             color=ctx.author.color,
    #             description=f"[Click Here for Full Article]({article['url']})\n\n{article['description']}",
    #             timestamp=datetime.datetime.fromisoformat(article["publishedAt"].replace("Z", "")),
    #         )
    #         embed.set_image(url=article["urlToImage"])
    #         embed.set_author(name=f"{article['author']} - {article['source']['name']}")
    #         embed.set_footer(text=f"Article {i}/{data['totalResults']}")
    #         embeds.append(embed)
    #     if len(embeds) == 1:
    #         await ctx.send(embed=embeds[0])
    #     else:
    #         await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=90)
    
    # @news.command()
    # async def topglobal(self, ctx, *, query: str = None):
    #     """News from the World."""
    #     async with ctx.typing():
    #         print(self.api.format("top-headlines", "q={}".format(query) if query is not None else "", "", self.newsapikey, ""))
    #         data = await self.get(self.api.format("everything", "q={}".format(query) if query is not None else "", "", self.newsapikey, ""))
    #     if data.get("failed") is not None:
    #         return await ctx.send(data.get("failed"))
    #     if data["totalResults"] == 0:
    #         return await ctx.send(
    #             "No results found."
    #         )
    #     embeds = []
    #     for i, article in enumerate(data["articles"][:15], 1):
    #         embed = discord.Embed(
    #             title=article["title"],
    #             color=ctx.author.color,
    #             description=f"[Click Here for Full Article]({article['url']})\n\n{article['description']}",
    #             timestamp=datetime.datetime.fromisoformat(article["publishedAt"].replace("Z", "")),
    #         )
    #         embed.set_image(url=article["urlToImage"])
    #         embed.set_author(name=f"{article['author']} - {article['source']['name']}")
    #         embed.set_footer(text=f"Article {i}/{data['totalResults']}")
    #         embeds.append(embed)
    #     if len(embeds) == 1:
    #         await ctx.send(embed=embeds[0])
    #     else:
    #         await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=90)

