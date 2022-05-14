import asyncio
from io import BytesIO
from typing import Optional

import aiohttp
import colorgram
import discord
from PIL import Image, ImageDraw, ImageFile, ImageFont
from redbot.core import commands
from redbot.core.data_manager import bundled_data_path

from .converters import ImageFinder


class Palette(commands.Cog):
    """
    This is a collection of commands that are used to show colour palettes.
    """

    __version__ = "0.0.2"
    __author__ = "flare(flare#0001)"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    def rgb_to_hex(self, rgb):
        return "%02x%02x%02x" % rgb

    async def get_img(self, ctx, url):
        async with ctx.typing():
            async with self.session.get(url) as resp:
                if resp.status in [200, 201]:
                    file = await resp.read()
                    file = BytesIO(file)
                    file.seek(0)
                    return file
                if resp.status == 404:
                    return {
                        "error": "Server not found, ensure the correct URL is setup and is reachable. "
                    }
                return {"error": resp.status}

    @commands.command()
    async def palette(
        self,
        ctx,
        img: Optional[ImageFinder] = None,
        amount: Optional[int] = 10,
        sorted: bool = False,
    ):
        """Colour palette of an image

        By default it is sorted by prominence, but you can sort it by rgb by passing true."""
        if amount > 50:
            return await ctx.send("Too many colours, please limit to 50.")
        if img is None:
            img = str(ctx.author.avatar_url_as(format="png"))
        async with ctx.typing():
            img = await self.get_img(ctx, str(img))
        if isinstance(img, dict):
            return await ctx.send(img["error"])
        image = await self.create_palette(img, amount, False, sorted)
        await ctx.send(file=image)

    @commands.command()
    async def hexpalette(
        self,
        ctx,
        img: Optional[ImageFinder] = None,
        amount: Optional[int] = 10,
        sorted: bool = False,
    ):
        """Colour palette of an image with hex values

        By default it is sorted by prominence, but you can sort it by rgb by passing true."""
        if amount < 1:
            return await ctx.send("Colours should be at least 1.")
        if amount > 50:
            return await ctx.send("Too many colours, please limit to 50.")
        if img is None:
            img = str(ctx.author.avatar_url_as(format="png"))
        async with ctx.typing():
            img = await self.get_img(ctx, str(img))
        if isinstance(img, dict):
            return await ctx.send(img["error"])
        image = await self.create_palette(img, amount, False, sorted)
        await ctx.send(file=image)

    async def create_palette(self, img: BytesIO, amount: int, show_hex: bool, sorted: bool):
        colors = colorgram.extract(img, amount)
        if sorted:
            colors.sort(key=lambda c: c.rgb)

        dimensions = (500 * len(colors), 500) if show_hex else (100 * len(colors), 100)
        final = Image.new("RGBA", dimensions)
        a = ImageDraw.Draw(final)
        start = 0
        if show_hex:
            font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
            name_fnt = ImageFont.truetype(font_file, 52, encoding="utf-8")
        for color in colors:
            a.rectangle(
                [(start, 0), (start + dimensions[1], 450 if show_hex else 100)], fill=color.rgb
            )
            if show_hex:
                msg = f"#{self.rgb_to_hex(color.rgb)}"
                a.text(
                    (start + dimensions[1] // 2, 500),
                    msg,
                    font=name_fnt,
                    fill=(255, 255, 255, 255),
                    anchor="mb",
                )
            start = start + dimensions[1]
        final = final.resize((500 * len(colors), 500), resample=Image.ANTIALIAS)
        fileObj = BytesIO()
        final.save(fileObj, "png")
        fileObj.name = "palette.png"
        fileObj.seek(0)
        return discord.File(fileObj)
