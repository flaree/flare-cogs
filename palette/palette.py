from io import BytesIO
from typing import Optional

import aiohttp
import colorgram
import discord
from PIL import Image, ImageDraw, ImageFont
from redbot.core import commands
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import box
from tabulate import tabulate

from .converters import ImageFinder

VALID_CONTENT_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/gif")


class Palette(commands.Cog):
    """
    This is a collection of commands that are used to show colour palettes.
    """

    __version__ = "0.1.0"
    __author__ = "flare(flare#0001) and Kuro"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    def rgb_to_hex(self, rgb):
        return "#%02x%02x%02x" % rgb

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
        image: Optional[ImageFinder] = None,
        amount: Optional[commands.Range[int, 1, 50]] = 10,
        detailed: bool = False,
        sort: bool = False,
    ):
        """Get the colour palette of an image.

        **Arguments**
        - `[image]` The image to get the palette from. If not provided, the author's avatar will be used. You can also provide an attachment.
        - `[amount]` The amount of colours to get. Must be between 1 and 50. Defaults to 10.
        - `[detailed]` Whether to show the colours in a detailed format (with rgb and hex). Defaults to False.
        - `[sort]` Whether to sort the colours by rgb. Defaults to False.
        """
        if not image and (attachments := ctx.message.attachments):
            valid_attachments = [a for a in attachments if a.content_type in VALID_CONTENT_TYPES]
            if valid_attachments:
                image = valid_attachments[0].url
            else:
                image = str(ctx.author.display_avatar)
        async with ctx.typing():
            img = await self.get_img(ctx, str(image))
        if isinstance(img, dict):
            return await ctx.send(img["error"])

        colors, file = await self.bot.loop.run_in_executor(
            None, self.create_palette, img, amount, detailed, sort
        )
        if not detailed:
            return await ctx.send(file=file)

        table = []
        for i, color in enumerate(colors, start=1):
            row = [f"{color.rgb.r}, {color.rgb.g}, {color.rgb.b}", self.rgb_to_hex(color.rgb)]
            if len(colors) > 1:
                row.insert(0, str(i))
            table.append(row)
        headers = ["#", "RGB", "Hex"] if len(colors) > 1 else ["RGB", "Hex"]

        embed = discord.Embed(
            color=await ctx.embed_color(),
            title="Colour Palette",
            description=box(tabulate(table, headers), lang="css"),
        )
        embed.set_thumbnail(url=image)
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(
            embed=embed,
            file=file,
            reference=ctx.message.to_reference(fail_if_not_exists=False),
            mention_author=False,
        )

    def create_palette(self, fp: BytesIO, amount: int, detailed: bool, sort: bool):
        colors = colorgram.extract(fp, amount)
        if sort:
            colors.sort(key=lambda c: c.rgb)

        dimensions = (500 * len(colors), 500) if detailed else (100 * len(colors), 100)
        final = Image.new("RGBA", dimensions)
        a = ImageDraw.Draw(final)
        start = 0
        if detailed:
            font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
            name_fnt = ImageFont.truetype(font_file, 69, encoding="utf-8")
        for i, color in enumerate(colors, start=1):
            a.rectangle(
                [(start, 0), (start + dimensions[1], 431 if detailed else 100)], fill=color.rgb
            )
            if detailed:
                # Bold text effect
                offsets = ((0, 0), (1, 0), (0, 1), (1, 1))
                for xo, yo in offsets:
                    a.text(
                        (start + dimensions[1] // 2 + xo, 499 + yo),
                        str(i),
                        fill=(255, 255, 255, 255),
                        font=name_fnt,
                        anchor="mb",
                    )
            start = start + dimensions[1]
        final = final.resize((500 * len(colors), 500), resample=Image.Resampling.LANCZOS)
        fileObj = BytesIO()
        final.save(fileObj, "png")
        fileObj.name = "palette.png"
        fileObj.seek(0)
        return colors, discord.File(fileObj)
