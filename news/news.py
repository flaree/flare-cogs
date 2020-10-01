import aiohttp
from redbot.core import commands

from .menus import ArticleFormat, GenericMenu


class News(commands.Cog):
    """News Cog."""

    __version__ = "0.0.3"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.api = (
            "https://newsapi.org/v2/{}?{}&sortBy=publishedAt{}&apiKey={}&page=1&pageSize=15{}"
        )
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
        """Group Command for News."""

    @commands.command()
    async def newssetup(self, ctx):
        """Instructions on how to setup news related APIs."""
        msg = "**News API Setup**\n**1**. Visit https://newsapi.org and register for an API.\n**2**. Use the following command: {}set api newsapi key <api_key_here>\n**3**. Reload the cog if it doesnt work immediately.".format(
            ctx.prefix
        )
        await ctx.maybe_send_embed(msg)

    @news.command(hidden=True)
    async def countrycodes(self, ctx):
        """Countries supported by the News Cog."""
        await ctx.send(
            "Valid country codes are:\nae ar at au be bg br ca ch cn co cu cz de eg fr gb gr hk hu id ie il in it jp kr lt lv ma mx my ng nl no nz ph pl pt ro rs ru sa se sg si sk th tr tw ua us ve za"
        )

    @news.command()
    async def top(self, ctx, countrycode: str, *, query: str = None):
        """
        Top News from a Country - County must be 2-letter ISO 3166-1 code. Supports querys to search news.

        Check [p]news countrycodes for a list of all possible country codes supported.
        """
        async with ctx.typing():
            data = await self.get(
                self.api.format(
                    "top-headlines",
                    "q={}".format(query) if query is not None else "",
                    "&country={}".format(countrycode),
                    self.newsapikey,
                    "",
                )
            )
        if data.get("failed") is not None:
            return await ctx.send(data.get("failed"))
        if data["totalResults"] == 0:
            return await ctx.send(
                "No results found, ensure you're looking up the correct country code. Check {}countrycodes for a list. Alternatively, your query may be returning no results.".format(
                    ctx.prefix
                )
            )
        await GenericMenu(source=ArticleFormat(data["articles"][:15]), ctx=ctx,).start(
            ctx=ctx,
            wait=False,
        )

    @news.command(name="global")
    async def global_all(self, ctx, *, query: str = None):
        """News from around the World.

        Not considered top-headlines. May be unreliable, unknown etc.
        """
        async with ctx.typing():
            data = await self.get(
                self.api.format("everything", "q={}".format(query), "", self.newsapikey, "")
            )
        if data.get("failed") is not None:
            return await ctx.send(data.get("failed"))
        if data["totalResults"] == 0:
            return await ctx.send("No results found.")
        await GenericMenu(source=ArticleFormat(data["articles"]), ctx=ctx,).start(
            ctx=ctx,
            wait=False,
        )

    @news.command()
    async def topglobal(self, ctx, *, query: str):
        """Top Headlines from around the world."""
        async with ctx.typing():
            data = await self.get(
                self.api.format("top-headlines", "q={}".format(query), "", self.newsapikey, "")
            )
        if data.get("failed") is not None:
            return await ctx.send(data.get("failed"))
        if data["totalResults"] == 0:
            return await ctx.send("No results found.")
        await GenericMenu(source=ArticleFormat(data["articles"]), ctx=ctx,).start(
            ctx=ctx,
            wait=False,
        )
