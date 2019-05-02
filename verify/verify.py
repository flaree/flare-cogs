import discord
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify
from random import randint, choice
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import uuid
import socket

defaults = {"Codes": {}, "verified": {}, "settings": {}}


class Verify(commands.Cog):
    """Verify's Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7258295620, force_registration=True)
        self.config.register_global(**defaults)
        self._session = aiohttp.ClientSession()

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json()

    async def getraw(self, url):
        async with self._session.get(url) as response:
            return await response.text()

    @commands.command()
    async def verify(self, ctx, url=None):
        """Verification Link"""
        async with self.config.verified() as ver:
            if str(ctx.author.id) in ver:
                await ctx.send("Your account is already verified")
                return
            if url is None:
                async with self.config.Codes() as code:
                    if str(ctx.author.id) in code:
                        await ctx.send(
                            "Your code is `{}`. Please update your WC-RP Profiles In-Game characters section to the code. To verify that you have, reissue the command .verify <url of your forum account>".format(
                                code[str(ctx.author.id)]
                            )
                        )
                        return
                    code[str(ctx.author.id)] = uuid.uuid4().hex.upper()[0:6]
                    await ctx.send(
                        "Your code is `{}`. Please paste the code into your characters field on your profile.\nOnce that is completed please post verifiy your account using .verify <url to forum account>".format(
                            code[str(ctx.author.id)]
                        )
                    )
            if url is not None:
                if url.split(".")[0] != "https://wc-rp":
                    return
                async with self.config.settings() as settings:
                    if "tag" not in settings:
                        await ctx.send("You have not set the verification settings.")
                        return
                    tag = settings["tag"]
                    tagclass = settings["tagclass"]
                req = await self.getraw(url)
                soup = BeautifulSoup(req, "html.parser")
                genitems = []
                async with self.config.Codes() as code:
                    for link in soup.find_all("div", attrs={"class": "ipsDataItem_generic"}):
                        genitems.append(link.get_text())
                    if code[str(ctx.author.id)] in genitems:
                        await ctx.send("Your account has been sucessfully verified and linked.")
                        ver[str(ctx.author.id)] = str(url)
                    else:
                        await ctx.send(
                            "The code does not appear to be present in your characters field."
                        )

    @commands.command()
    async def unlink(self, ctx):
        """Unlink your forum account"""
        async with self.config.verified() as ver:
            del ver[str(ctx.author.id)]
        async with self.config.Codes() as code:
            del code[str(ctx.author.id)]
        await ctx.send("Your account has been unlinked successfully.")

    @checks.is_owner()
    @commands.command()
    async def verifyset(self, ctx, tag: str, *, tagclass: str):
        """Verification Settings"""
        async with self.config.settings() as settings:
            settings["tag"] = tag
            settings["tagclass"] = tagclass
            await ctx.send("Verification settings have been set.")
