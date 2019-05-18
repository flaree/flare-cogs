import random
import discord
import aiohttp
import asyncio
from redbot.core import commands, Config, checks
from . import __path__
import os
from .operators import ops
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

defaults = {"Profiles": {}, "Platform": {}}


class Rainbow6(commands.Cog):
    """Rainbow6 Related Commands"""

    def __init__(self, bot):
        self.database = Config.get_conf(self, identifier=7258295620, force_registration=True)
        self.database.register_global(**defaults)
        self.bot = bot
        self._session = aiohttp.ClientSession()
        self.platforms = ["psn", "xbl"]

    def cog_unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json(content_type="text/html")

    async def getimg(self, url):
        async with self._session.get(url) as response:
            rank = await response.read()
            return rank

    # Thanks trusty & malarne for helping me get over pillow.
    def round_corner(self, radius):
        """Draw a round corner"""
        corner = Image.new("L", (radius, radius), 0)
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=255)
        return corner

    def add_corners(self, im, rad):
        # https://stackoverflow.com/questions/7787375/python-imaging-library-pil-drawing-rounded-rectangle-with-gradient
        width, height = im.size
        alpha = Image.new("L", im.size, 255)
        origCorner = self.round_corner(rad)
        corner = origCorner
        alpha.paste(corner, (0, 0))
        corner = origCorner.rotate(90)
        alpha.paste(corner, (0, height - rad))
        corner = origCorner.rotate(180)
        alpha.paste(corner, (width - rad, height - rad))
        corner = origCorner.rotate(270)
        alpha.paste(corner, (width - rad, 0))
        im.putalpha(alpha)
        return im

    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """R6 Commands"""
        pass

    @r6.command()
    async def setprofile(self, ctx, account: str, platforms=None):
        """Set profile for automatic lookup via r6 profile"""
        if platforms != "psn" or platforms != "xbl":
            platforms = "uplay"
        async with self.database.Profiles() as profiles:
            key1 = ctx.author
            profiles[key1] = account
        async with self.database.Platform() as platform:
            key1 = ctx.author
            platform[key1] = platforms
        await ctx.send(f"Profile and platform updated successfully.")

    @r6.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def profile(self, ctx, account: str = None):
        """R6 Profile Stats for your or the provided account. """
        data = await self.database.all()
        pic = await self.database.user(ctx.author).all()
        if account is None:
            try:
                member = ctx.author
                account = data["Profiles"]["{}".format(member)]
                platform = data["Platform"]["{}".format(member)]
            except KeyError:
                await ctx.send(
                    "Please set your account using the r6 setprofile command or search for an account using r6 profile <name> [platform]"
                )
                return

        else:
            platform = "uplay"
        async with ctx.typing():
            req1 = "https://www.antisnakedetail.xyz/r6/getUser.php?name={}&platform={}&appcode=flare".format(
                account, platform
            )
            req2 = "https://www.antisnakedetail.xyz/r6/getSmallUser.php?name={}&platform={}&appcode=flare".format(
                account, platform
            )
            req3 = "https://www.antisnakedetail.xyz/r6/getStats.php?name={}&platform=uplay&appcode=flare".format(
                account
            )
            r = await self.get(req1)
            t = await self.get(req2)
            s = await self.get(req3)
            p = r["players"]["{}".format(list(t.keys())[0])]
            q = s["players"]["{}".format(list(t.keys())[0])]
            if (int(p["wins"]) + int(p["losses"]) + int(p["abandons"])) != 0:
                wlr = (int(p["wins"]) / (int(p["wins"]) + int(p["losses"]) + int(p["abandons"]))) * 100
            else:
                wlr = 0
            if (int(q["rankedpvp_matchlost"]) + int(q["rankedpvp_matchwon"])) != 0:
                twlr = (
                    q["rankedpvp_matchwon"] / (q["rankedpvp_matchlost"] + q["rankedpvp_matchwon"])
                ) * 100
            else:
                twlr = 0
            kdr = int(q["rankedpvp_kills"]) / int(q["rankedpvp_death"])
            season = p["season"]
            img = Image.new("RGBA", (400, 580), (17, 17, 17, 0))
            aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
            nameplate = self.add_corners(Image.new("RGBA", (180, 90), (0, 0, 0, 255)), 10)
            img.paste(nameplate, (155, 10), nameplate)
            img.paste(aviholder, (10, 10), aviholder)
            url = p["rankInfo"]["image"]
            im = Image.open(BytesIO(await self.getimg(url)))
            im_size = 130, 130
            im.thumbnail(im_size)
            img.paste(im, (14, 15))
            draw = ImageDraw.Draw(img)
            font2 = ImageFont.truetype(os.path.join(__path__[0], "ARIALUNI.ttf"), 22)
            font = ImageFont.truetype(os.path.join(__path__[0], "ARIALUNI.ttf"), 24)
            draw.text((162, 14), f"{account}", fill=(255, 255, 255, 255), font=font)
            draw.text(
                (10, 180),
                "Rank: {}".format(p["rankInfo"]["name"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text((162, 40), "Level: {}".format(p["level"]), fill=(255, 255, 255, 255), font=font)
            draw.text((162, 70), "Ranked Stats", fill=(255, 255, 255, 255), font=font2)
            draw.text(
                (10, 220),
                "S{} Wins: {}".format(season, p["wins"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 260),
                "S{} Losses: {}".format(season, p["losses"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (180, 220),
                "Total Wins: {}".format(q["rankedpvp_matchwon"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (180, 260),
                "Total Losses: {}".format(q["rankedpvp_matchlost"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 300), "MMR: {}".format(round(p["mmr"])), fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 340), "Abandons: {}".format(p["abandons"]), fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 380),
                "Ranked Kills: {}".format(q["rankedpvp_kills"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 420),
                "Ranked Deaths: {}".format(q["rankedpvp_death"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 460), "Ranked KDR: {}".format(round(kdr, 2)), fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 500),
                "S{} Ranked W/LR: {}%".format(season, round(wlr, 2)),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 540),
                "Total Ranked W/LR: {}%".format(round(twlr, 2)),
                fill=(255, 255, 255, 255),
                font=font,
            )
            file = BytesIO()
            img.save(file, "png")
            file.name = "profile.png"
            file.seek(0)
            image = discord.File(file)
            await ctx.send(file=image)

    @commands.command()
    async def accinfo(self, ctx, member: discord.Member = None):
        """Account Info"""
        data = await self.database.all()
        if member is None:
            member = ctx.author
        try:
            profile = data["Profiles"]["{}".format(member)]
            platform = data["Platform"]["{}".format(member)]
            await ctx.send(f"Profile Name: {profile}")
            await ctx.send(f"Platform: {platform}")
        except KeyError:
            await ctx.send("You do not have an account set, please set one via .r6 setprofile")

    @r6.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def season(self, ctx, account: str, season: int, platform=None):
        """R6 Profile Stats for a custom season - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        if 0 > season or season > 12:
            season = 12
        if platform not in self.platforms:
            platform = "uplay"
        async with ctx.typing():
            r = await self.get(
                f"https://www.antisnakedetail.xyz/r6/getUser.php?name={account}&platform={platform}&appcode=flare&season={season}"
            )
            t = await self.get(
                f"https://www.antisnakedetail.xyz/r6/getSmallUser.php?name={account}&platform={platform}&appcode=flare"
            )

            s = await self.get(
                "https://www.antisnakedetail.xyz/r6/getStats.php?name={}&platform={}&appcode=flare".format(
                    account, platform
                )
            )
            p = r["players"]["{}".format(list(t.keys())[0])]
            q = s["players"]["{}".format(list(t.keys())[0])]
            kdr = int(q["rankedpvp_kills"]) / int(q["rankedpvp_death"])
            img = Image.new("RGBA", (340, 520), (17, 17, 17, 0))
            aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
            nameplate = self.add_corners(Image.new("RGBA", (180, 90), (0, 0, 0, 255)), 10)
            img.paste(nameplate, (155, 10), nameplate)
            img.paste(aviholder, (10, 10), aviholder)
            url = p["rankInfo"]["image"]
            im = Image.open(BytesIO(await self.getimg(url)))
            im_size = 130, 130
            im.thumbnail(im_size)
            img.paste(im, (14, 15))
            draw = ImageDraw.Draw(img)
            font2 = ImageFont.truetype(os.path.join(__path__[0], "ARIALUNI.ttf"), 22)
            font = ImageFont.truetype(os.path.join(__path__[0], "ARIALUNI.ttf"), 24)
            draw.text((162, 14), f"{account}", fill=(255, 255, 255, 255), font=font)
            draw.text(
                (10, 180),
                "Rank: {}".format(p["rankInfo"]["name"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text((162, 40), "Level: {}".format(p["level"]), fill=(255, 255, 255, 255), font=font)
            draw.text((162, 70), f"Season {season} Stats", fill=(255, 255, 255, 255), font=font2)
            draw.text((10, 220), "Wins: {}".format(p["wins"]), fill=(255, 255, 255, 255), font=font)
            draw.text(
                (10, 260), "Losses: {}".format(p["losses"]), fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 300), "MMR: {}".format(round(p["mmr"])), fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 340), "Abandons: {}".format(p["abandons"]), fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 380),
                "Ranked Kills: {}".format(q["rankedpvp_kills"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 420),
                "Ranked Deaths: {}".format(q["rankedpvp_death"]),
                fill=(255, 255, 255, 255),
                font=font,
            )
            draw.text(
                (10, 460), "Ranked KDR: {}".format(round(kdr, 2)), fill=(255, 255, 255, 255), font=font
            )

            file = BytesIO()
            img.save(file, "png")
            file.name = "season.png"
            file.seek(0)
            image = discord.File(file)
            await ctx.send(file=image)

    @r6.command()
    async def operator(self, ctx, account: str, operator: str, platform: str = None):
        """R6 Profile Stats for a certain Operator - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        operator = operator.lower()
        if operator not in ops:
            await ctx.send(f"{operator} is not a valid operator.")
            return
        if platform not in self.platforms:
            platform = "uplay"
        async with ctx.typing():
            r = await self.get(
                f"https://www.antisnakedetail.xyz/r6/getOperators.php?name={account}&platform={platform}&appcode=flare"
            )
            t = await self.get(
                f"https://www.antisnakedetail.xyz/r6/getSmallUser.php?name={account}&platform={platform}&appcode=flare"
            )
            p = r["players"]["{}".format(list(t.keys())[0])]["{}".format(operator)]
            if p["operatorpvp_kills"] == 0 and p["operatorpvp_death"] == 0:
                kdr = 0
            else:
                kdr = round(p["operatorpvp_kills"] / p["operatorpvp_death"], 2)
            if p["operatorpvp_roundwon"] == 0 and p["operatorpvp_roundlost"] == 0:
                opwlr = 0
            else:
                opwlr = round(
                    (
                        p["operatorpvp_roundwon"]
                        / (p["operatorpvp_roundwon"] + p["operatorpvp_roundlost"])
                    )
                    * 100,
                    2,
                )
            url = (r["operators"][f"{operator}"]["images"]["badge"]).replace("\\", "")
            img = Image.new("RGBA", (540, 520), (17, 17, 17, 0))
            aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
            nameplate = self.add_corners(Image.new("RGBA", (240, 65), (0, 0, 0, 255)), 10)
            img.paste(nameplate, (155, 10), nameplate)
            img.paste(aviholder, (10, 10), aviholder)
            im = Image.open(BytesIO(await self.getimg(url)))
            im_size = 130, 130
            im.thumbnail(im_size)
            img.paste(im, (14, 15))
            draw = ImageDraw.Draw(img)
            font2 = ImageFont.truetype(os.path.join(__path__[0], "ARIALUNI.ttf"), 22)
            font = ImageFont.truetype(os.path.join(__path__[0], "ARIALUNI.ttf"), 24)
            draw.text((162, 14), f"{account}", fill=(255, 255, 255, 255), font=font)
            draw.text(
                (162, 40), f"Operator: {operator.capitalize()}", fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 180), f"{operator.capitalize()} KDR: {kdr}", fill=(255, 255, 255, 255), font=font
            )
            draw.text(
                (10, 220),
                f"{operator.capitalize()} WLR: {opwlr}%",
                fill=(255, 255, 255, 255),
                font=font,
            )
            i = 260
            for stats in p:
                if stats[0:11] == "operatorpvp":
                    stat = str(stats[12:]).replace("_", " ").title()
                    if stat == "Timeplayed":
                        p[stats] = round((p[stats] / 60), 2)
                    t = len(operator)
                    if stat[:t] == operator.capitalize():
                        stat = stat[t + 1 :]
                    draw.text(
                        (10, i),
                        "{} {}: {}".format(operator.capitalize(), stat, p[stats]),
                        fill=(255, 255, 255, 255),
                        font=font,
                    )

                i += 40
            file = BytesIO()
            img.save(file, "png")
            file.name = "operator.png"
            file.seek(0)
            image = discord.File(file)
            await ctx.send(file=image)

    @r6.command()
    async def operators(self, ctx, account: str, stats: str, platform=None):
        """R6 Profile Statsfor all operators.
         Stats can be kills, roundwon or timeplayed.
         Platform defaults to uplay.Other choices: "xbl" and "psn" """
        if platform not in self.platforms:
            platform = "uplay"
        async with ctx.typing():
            r = await self.get(
                "https://www.antisnakedetail.xyz/r6/getOperators.php?name={}&platform={}&appcode=flare".format(
                    account, platform
                )
            )
            t = await self.get(
                "https://www.antisnakedetail.xyz/r6/getSmallUser.php?name={}&platform={}&appcode=flare".format(
                    account, platform
                )
            )
            q = r["players"]["{}".format(list(t.keys())[0])]
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(
                title="Operator Information for {} - Page 1".format(account), colour=colour
            )
            emb = discord.Embed(
                title="Operator Information for {} - Page 2".format(account), colour=colour
            )
            i = 0
            while i < len(ops):
                if i < 21:
                    if stats == "timeplayed":
                        embed.add_field(
                            name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                            value=str(
                                round(
                                    int(q["{}".format(ops[i])]["operatorpvp_{}".format(stats)]) / 3600
                                )
                            ),
                            inline=True,
                        )
                    else:
                        embed.add_field(
                            name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                            value=q["{}".format(ops[i])]["operatorpvp_{}".format(stats)],
                            inline=True,
                        )
                else:
                    if stats == "timeplayed":
                        emb.add_field(
                            name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                            value=str(
                                round(
                                    int(q["{}".format(ops[i])]["operatorpvp_{}".format(stats)]) / 3600
                                )
                            ),
                            inline=True,
                        )
                    else:
                        emb.add_field(
                            name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                            value=q["{}".format(ops[i])]["operatorpvp_{}".format(stats)],
                            inline=True,
                        )
                i += 1
            msgs = []
            msgs.append(embed)
            msgs.append(emb)
        await menu(ctx, msgs, DEFAULT_CONTROLS)
