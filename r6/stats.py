import random
from io import BytesIO

import aiohttp
import discord
import r6statsapi
from PIL import Image, ImageDraw, ImageFont
from redbot.core.data_manager import bundled_data_path


class Stats:
    def __init__(self, bot):
        self.bot = bot
        self.url = "https://api2.r6stats.com/public-api/"
        self.rankurl = "https://cdn.r6stats.com/seasons/rank-imgs/"
        self.ranksember = {
            "Unranked": "unranked.png",
            "Copper V": "copper-5.png",
            "Copper IV": "copper-4.png",
            "Copper III": "copper-3.png",
            "Copper II": "copper-2.png",
            "Copper I": "copper-1.png",
            "Bronze V": "bronze-5.png",
            "Bronve IV": "bronze-4.png",
            "Bronze III": "bronze-3.png",
            "Bronze II": "bronze-2.png",
            "Bronze I": "bronze-1.png",
            "Silver V": "silver-5.png",
            "Silver IV": "silver-4.png",
            "Silver III": "silver-3.png",
            "Silver II": "silver-2.png",
            "Silver I": "silver-1.png",
            "Gold III": "gold-3.png",
            "Gold II": "gold-2.png",
            "Gold I": "gold-1.png",
            "Platinum III": "platinum-3.png",
            "Platinum II": "platinum-2.png",
            "Platinum I": "platinum-1.png",
            "Diamond": "diamond.png",
            "Champions": "champions.png",
        }
        self.ranks = {
            "Unranked": "unranked.png",
            "Copper IV": "copper-4.png",
            "Copper III": "copper-3.png",
            "Copper II": "copper-2.png",
            "Copper I": "copper-1.png",
            "Bronve IV": "bronze-4.png",
            "Bronze III": "bronze-3.png",
            "Bronze II": "bronze-2.png",
            "Bronze I": "bronze-1.png",
            "Silver IV": "silver-4.png",
            "Silver III": "silver-3.png",
            "Silver II": "silver-2.png",
            "Silver I": "silver-1.png",
            "Gold IIII": "gold-4.png",
            "Gold III": "gold-3.png",
            "Gold II": "gold-2.png",
            "Gold I": "gold-1.png",
            "Platinum III": "platinum-3-old.png",
            "Platinum II": "platinum-2-old.png",
            "Platinum I": "platinum-1-old.png",
            "Diamond": "diamond-old.png",
            "Diamond I": "diamond-old.png",
        }
        self.regions = {"ncsa": "NA", "emea": "EU", "apac": "Asia"}
        self.session = aiohttp.ClientSession()
        self.bgs = ["twitch", "thermite", "ash", "sledge", "thatcher"]

    async def getimg(self, url):
        async with self.session.get(url) as response:
            rank = await response.read()
            return rank

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def profilecreate(self, data):
        font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
        bold_file = f"{bundled_data_path(self)}/fonts/RobotoBold.ttf"
        name_fnt = ImageFont.truetype(font_file, 42, encoding="utf-8")
        header_fnt = ImageFont.truetype(bold_file, 42, encoding="utf-8")
        operator = random.choice(self.bgs)

        bg_image = Image.open(f"{bundled_data_path(self)}/bg/{operator}.jpg").convert("RGBA")

        profile_image = Image

        profile_avatar = BytesIO()
        profile_url = data.avatar_url_256
        async with self.session.get(profile_url) as r:
            profile_img = await r.content.read()
            profile_avatar = BytesIO(profile_img)

        profile_image = Image.open(profile_avatar).convert("RGBA")

        # set canvas
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (1280, 1080), bg_color)
        process = Image.new("RGBA", (1280, 1080), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((1920, 1090), Image.ANTIALIAS)
        bg_image = bg_image.crop((0, 0, 1920, 1080))
        result.paste(bg_image, (0, 0))

        aviholder = self.add_corners(Image.new("RGBA", (266, 266), (255, 255, 255, 255)), 10)
        process.paste(aviholder, (995, 15), aviholder)
        process.paste(profile_image, (1000, 20))

        # data
        draw.text(
            (
                self._center(
                    440,
                    1000,
                    "Name: {}".format(self._truncate_text(data.username, 18)),
                    header_fnt,
                ),
                40,
            ),
            "Name: {}".format(self._truncate_text(data.username, 18)),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (
                self._center(
                    440, 1000, "Platform: {}".format(str(data.platform).title()), header_fnt
                ),
                90,
            ),
            "Platform: {}".format(str(data.platform).title()),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (self._center(440, 1000, "General Statistics", header_fnt), 140),
            "General Statistics",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (self._center(1000, 1256, f"Level: {data.level}", header_fnt), 300),
            f"Level: {data.level}",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (520, 400),
            "Wins: {}".format(data.general_stats["wins"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 400),
            "Losses: {}".format(data.general_stats["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 470),
            "Draws: {}".format(data.general_stats["draws"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 470),
            "Total W/LR: {}%".format(
                round(data.general_stats["wins"] / data.general_stats["games_played"], 2) * 100
            ),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 540),
            "Lootbox %: {}%".format(data.lootbox_probability),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 610),
            "Kills: {}".format(data.general_stats["kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 610),
            "Deaths: {}".format(data.general_stats["deaths"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 680),
            "Assists: {}".format(data.general_stats["assists"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 680),
            "KDR: {}".format(data.general_stats["kd"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 750),
            "Revives: {}".format(data.general_stats["revives"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 750),
            "Suicides: {}".format(data.general_stats["suicides"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 820),
            "Blind Kills: {}".format(data.general_stats["blind_kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 820),
            "Melee Kills: {}".format(data.general_stats["melee_kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 890),
            "Pentration Kills: {}".format(data.general_stats["penetration_kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 890),
            "DBNOs: {}".format(data.general_stats["dbnos"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        m, _ = divmod(data.general_stats["playtime"], 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        draw.text(
            (520, 1010),
            f"Playtime: {d:d}d {h:d}h {m:02d}m",
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "png")
        file.name = f"general-{data.username}.png"
        file.seek(0)
        image = discord.File(file)
        return image

    async def rankedstatscreate(self, data):
        font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
        bold_file = f"{bundled_data_path(self)}/fonts/RobotoBold.ttf"
        name_fnt = ImageFont.truetype(font_file, 42, encoding="utf-8")
        header_fnt = ImageFont.truetype(bold_file, 42, encoding="utf-8")
        operator = random.choice(self.bgs)

        bg_image = Image.open(f"{bundled_data_path(self)}/bg/{operator}.jpg").convert("RGBA")

        profile_image = Image

        profile_avatar = BytesIO()
        profile_url = data.avatar_url_256
        async with self.session.get(profile_url) as r:
            profile_img = await r.content.read()
            profile_avatar = BytesIO(profile_img)

        profile_image = Image.open(profile_avatar).convert("RGBA")

        # set canvas
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (1280, 1080), bg_color)
        process = Image.new("RGBA", (1280, 1080), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((1920, 1090), Image.ANTIALIAS)
        bg_image = bg_image.crop((0, 0, 1920, 1080))
        result.paste(bg_image, (0, 0))

        aviholder = self.add_corners(Image.new("RGBA", (266, 266), (255, 255, 255, 255)), 10)
        process.paste(aviholder, (995, 15), aviholder)
        process.paste(profile_image, (1000, 20))

        # data
        # draw.text((440, 40), "Name: {}".format(self._truncate_text(data.username, 18)), fill=(255, 255, 255, 255), font=header_fnt)
        draw.text(
            (
                self._center(
                    440,
                    1000,
                    "Name: {}".format(self._truncate_text(data.username, 18)),
                    header_fnt,
                ),
                40,
            ),
            "Name: {}".format(self._truncate_text(data.username, 18)),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (
                self._center(
                    440, 1000, "Platform: {}".format(str(data.platform).title()), header_fnt
                ),
                90,
            ),
            "Platform: {}".format(str(data.platform).title()),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (self._center(440, 1000, "Alltime Ranked Statistics", header_fnt), 140),
            "Alltime Ranked Statistics",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (self._center(1000, 1256, f"Level: {data.level}", header_fnt), 300),
            f"Level: {data.level}",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (520, 400),
            "Games Played: {}".format(data.queue_stats["ranked"]["games_played"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 480),
            "Wins: {}".format(data.queue_stats["ranked"]["wins"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 480),
            "Losses: {}".format(data.queue_stats["ranked"]["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 560),
            "Draws: {}".format(data.queue_stats["ranked"]["draws"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        try:
            wlr = (
                round(
                    data.queue_stats["ranked"]["wins"]
                    / data.queue_stats["ranked"]["games_played"],
                    2,
                )
                * 100
            )
        except ZeroDivisionError:
            wlr = 0
        draw.text(
            (520, 640), "Total W/LR: {}%".format(wlr), fill=(255, 255, 255, 255), font=name_fnt
        )

        draw.text(
            (520, 800),
            "Kills: {}".format(data.queue_stats["ranked"]["kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 800),
            "Deaths: {}".format(data.queue_stats["ranked"]["deaths"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 880),
            "KDR: {}".format(data.queue_stats["ranked"]["kd"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        m, _ = divmod(data.queue_stats["ranked"]["playtime"], 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        draw.text(
            (520, 960),
            f"Playtime: {d:d}d {h:d}h {m:02d}m",
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "png")
        file.name = f"ranked-{data.username}.png"
        file.seek(0)
        image = discord.File(file)
        return image

    async def casualstatscreate(self, data):
        font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
        bold_file = f"{bundled_data_path(self)}/fonts/RobotoBold.ttf"
        name_fnt = ImageFont.truetype(font_file, 42, encoding="utf-8")
        header_fnt = ImageFont.truetype(bold_file, 42, encoding="utf-8")
        operator = random.choice(self.bgs)

        bg_image = Image.open(f"{bundled_data_path(self)}/bg/{operator}.jpg").convert("RGBA")

        profile_image = Image

        profile_avatar = BytesIO()
        profile_url = data.avatar_url_256
        async with self.session.get(profile_url) as r:
            profile_img = await r.content.read()
            profile_avatar = BytesIO(profile_img)

        profile_image = Image.open(profile_avatar).convert("RGBA")

        # set canvas
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (1280, 1080), bg_color)
        process = Image.new("RGBA", (1280, 1080), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((1920, 1090), Image.ANTIALIAS)
        bg_image = bg_image.crop((0, 0, 1920, 1080))
        result.paste(bg_image, (0, 0))

        aviholder = self.add_corners(Image.new("RGBA", (266, 266), (255, 255, 255, 255)), 10)
        process.paste(aviholder, (995, 15), aviholder)
        process.paste(profile_image, (1000, 20))

        # data
        # draw.text((440, 40), "Name: {}".format(self._truncate_text(data.username, 18)), fill=(255, 255, 255, 255), font=header_fnt)
        draw.text(
            (
                self._center(
                    440,
                    1000,
                    "Name: {}".format(self._truncate_text(data.username, 18)),
                    header_fnt,
                ),
                40,
            ),
            "Name: {}".format(self._truncate_text(data.username, 18)),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (
                self._center(
                    440, 1000, "Platform: {}".format(str(data.platform).title()), header_fnt
                ),
                90,
            ),
            "Platform: {}".format(str(data.platform).title()),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (self._center(440, 1000, "Alltime Ranked Statistics", header_fnt), 140),
            "Alltime Casual Statistics",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (self._center(1000, 1256, f"Level: {data.level}", header_fnt), 300),
            f"Level: {data.level}",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (520, 400),
            "Games Played: {}".format(data.queue_stats["casual"]["games_played"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 480),
            "Wins: {}".format(data.queue_stats["casual"]["wins"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 480),
            "Losses: {}".format(data.queue_stats["casual"]["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 560),
            "Draws: {}".format(data.queue_stats["casual"]["draws"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        try:
            wlr = (
                round(
                    data.queue_stats["casual"]["wins"]
                    / data.queue_stats["casual"]["games_played"],
                    2,
                )
                * 100
            )
        except ZeroDivisionError:
            wlr = 0
        draw.text(
            (520, 640), "Total W/LR: {}%".format(wlr), fill=(255, 255, 255, 255), font=name_fnt
        )

        draw.text(
            (520, 800),
            "Kills: {}".format(data.queue_stats["casual"]["kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 800),
            "Deaths: {}".format(data.queue_stats["casual"]["deaths"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 880),
            "KDR: {}".format(data.queue_stats["casual"]["kd"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        m, _ = divmod(data.queue_stats["casual"]["playtime"], 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        draw.text(
            (520, 960),
            f"Playtime: {d:d}d {h:d}h {m:02d}m",
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "png")
        file.name = f"casual-{data.username}.png"
        file.seek(0)
        image = discord.File(file)
        return image

    async def seasoncreate(self, data, seasondata, season, profile, seasonname):
        font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
        bold_file = f"{bundled_data_path(self)}/fonts/RobotoBold.ttf"
        name_fnt = ImageFont.truetype(font_file, 42, encoding="utf-8")
        header_fnt = ImageFont.truetype(bold_file, 42, encoding="utf-8")
        operator = random.choice(self.bgs)

        bg_image = Image.open(f"{bundled_data_path(self)}/bg/{operator}.jpg").convert("RGBA")

        profile_image = Image

        profile_avatar = BytesIO()
        profile_url = data.avatar_url_256
        async with self.session.get(profile_url) as r:
            profile_img = await r.content.read()
            profile_avatar = BytesIO(profile_img)

        profile_image = Image.open(profile_avatar).convert("RGBA")

        # set canvas
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (1600, 1080), bg_color)
        process = Image.new("RGBA", (1600, 1080), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((1920, 1090), Image.ANTIALIAS)
        bg_image = bg_image.crop((0, 0, 1920, 1080))
        result.paste(bg_image, (0, 0))

        aviholder = self.add_corners(Image.new("RGBA", (266, 266), (255, 255, 255, 255)), 10)
        process.paste(aviholder, (1295, 15), aviholder)
        process.paste(profile_image, (1300, 20))

        # op badge

        if season >= 14:
            ranks = self.ranksember
        else:
            ranks = self.ranks
        url = self.rankurl + ranks[seasondata["rank_text"]]

        process.paste(aviholder, (995, 15), aviholder)
        im = Image.open(BytesIO(await self.getimg(url)))
        im = im.resize((256, 256), Image.ANTIALIAS)
        process.paste(im, (1000, 20))

        # data
        # draw.text((440, 40), "Name: {}".format(self._truncate_text(data.username, 18)), fill=(255, 255, 255, 255), font=header_fnt)
        draw.text(
            (
                self._center(
                    440,
                    1000,
                    "Name: {}".format(self._truncate_text(data.username, 18)),
                    header_fnt,
                ),
                40,
            ),
            "Name: {}".format(self._truncate_text(data.username, 18)),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (
                self._center(
                    440, 1000, "Platform: {}".format(str(data.platform).title()), header_fnt
                ),
                90,
            ),
            "Platform: {}".format(str(data.platform).title()),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (
                self._center(
                    440, 1000, "Region: {}".format(self.regions[seasondata["region"]]), header_fnt
                ),
                140,
            ),
            "Region: {}".format(self.regions[seasondata["region"]]),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (self._center(440, 1000, f"{seasonname} Statistics", header_fnt), 190),
            f"{seasonname} Statistics",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (520, 320),
            "Games Played: {}".format(seasondata["wins"] + seasondata["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 380),
            "Wins: {}".format(seasondata["wins"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (960, 380),
            "Losses: {}".format(seasondata["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 440),
            "Abandons: {}".format(seasondata["abandons"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        try:
            wlr = round(seasondata["wins"] / (seasondata["wins"] + seasondata["losses"]), 2)
        except ZeroDivisionError:
            wlr = 0
        draw.text(
            (960, 440),
            "Total W/LR: {}%".format(wlr * 100),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        draw.text(
            (520, 520),
            "Kills: {}".format(seasondata["kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (960, 520),
            "Deaths: {}".format(seasondata["deaths"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 580),
            "MMR: {}".format(seasondata["mmr"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 640),
            "Max MMR: {}".format(seasondata["max_mmr"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 700),
            "Previous Rank MMR: {}".format(seasondata["prev_rank_mmr"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 760),
            "Next Rank MMR: {}".format(seasondata["next_rank_mmr"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 820),
            "Rank: {}".format(seasondata["rank_text"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        if seasondata["rank_text"] == "Champions":
            draw.text(
                (960, 820),
                "Champion Rank Position: {}".format(seasondata["champions_rank_position"]),
                fill=(255, 255, 255, 255),
                font=name_fnt,
            )
        draw.text(
            (520, 880),
            "Max Rank: {}".format(seasondata["max_rank_text"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "png")
        file.name = f"season-{data.username}.png"
        file.seek(0)
        image = discord.File(file)
        return image

    async def operatorstatscreate(self, data, index, profile):
        font_file = f"{bundled_data_path(self)}/fonts/RobotoRegular.ttf"
        bold_file = f"{bundled_data_path(self)}/fonts/RobotoBold.ttf"
        name_fnt = ImageFont.truetype(font_file, 42, encoding="utf-8")
        header_fnt = ImageFont.truetype(bold_file, 42, encoding="utf-8")
        operator = random.choice(self.bgs)
        opdata = data.operators[index]

        bg_image = Image.open(f"{bundled_data_path(self)}/bg/{operator}.jpg").convert("RGBA")

        profile_image = Image

        profile_avatar = BytesIO()
        profile_url = data.avatar_url_256
        async with self.session.get(profile_url) as r:
            profile_img = await r.content.read()
            profile_avatar = BytesIO(profile_img)

        profile_image = Image.open(profile_avatar).convert("RGBA")

        # set canvas
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (1600, 1080), bg_color)
        process = Image.new("RGBA", (1600, 1080), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((1920, 1090), Image.ANTIALIAS)
        bg_image = bg_image.crop((0, 0, 1920, 1080))
        result.paste(bg_image, (0, 0))

        aviholder = self.add_corners(Image.new("RGBA", (266, 266), (255, 255, 255, 255)), 10)
        process.paste(aviholder, (1295, 15), aviholder)
        process.paste(profile_image, (1300, 20))

        # op badge
        url = opdata["badge_image"]
        process.paste(aviholder, (995, 15), aviholder)
        im = Image.open(BytesIO(await self.getimg(url)))
        im = im.resize((256, 256), Image.ANTIALIAS)
        process.paste(im, (1000, 20))

        # data
        # draw.text((440, 40), "Name: {}".format(self._truncate_text(data.username, 18)), fill=(255, 255, 255, 255), font=header_fnt)
        draw.text(
            (
                self._center(
                    440,
                    1000,
                    "Name: {}".format(self._truncate_text(data.username, 18)),
                    header_fnt,
                ),
                40,
            ),
            "Name: {}".format(self._truncate_text(data.username, 18)),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (
                self._center(
                    440, 1000, "Platform: {}".format(str(data.platform).title()), header_fnt
                ),
                90,
            ),
            "Platform: {}".format(str(data.platform).title()),
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )
        draw.text(
            (self._center(440, 1000, f"{opdata['name']} Statistics", header_fnt), 140),
            f"{opdata['name']} Statistics",
            fill=(255, 255, 255, 255),
            font=header_fnt,
        )

        draw.text(
            (520, 320),
            "Games Played: {}".format(opdata["wins"] + opdata["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 380), "Wins: {}".format(opdata["wins"]), fill=(255, 255, 255, 255), font=name_fnt
        )
        draw.text(
            (920, 380),
            "Losses: {}".format(opdata["losses"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        try:
            wlr = round(opdata["wins"] / (opdata["wins"] + opdata["losses"]), 2)
        except ZeroDivisionError:
            wlr = 0
        draw.text(
            (520, 440),
            "Total W/LR: {}%".format(wlr * 100),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        draw.text(
            (520, 520),
            "Kills: {}".format(opdata["kills"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (920, 520),
            "Deaths: {}".format(opdata["deaths"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        draw.text(
            (520, 580), "KDR: {}".format(opdata["kd"]), fill=(255, 255, 255, 255), font=name_fnt
        )
        draw.text(
            (520, 640),
            "Headshots: {}".format(opdata["headshots"]),
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )
        y = 760
        for ability in opdata["abilities"]:

            draw.text(
                (520, y),
                "{}: {}".format(ability["ability"], ability["value"]),
                fill=(255, 255, 255, 255),
                font=name_fnt,
            )
            y += 80

        m, _ = divmod(opdata["playtime"], 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        draw.text(
            (520, 700),
            f"Playtime: {d:d}d {h:d}h {m:02d}m",
            fill=(255, 255, 255, 255),
            font=name_fnt,
        )

        result = Image.alpha_composite(result, process)
        result = result.crop((500, 0, 1600, 1080))
        file = BytesIO()
        result.save(file, "png")
        file.name = f"operator-{data.username}.png"
        file.seek(0)
        image = discord.File(file)
        return image

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

    def _truncate_text(self, text, max_length):
        if len(text) > max_length:
            if text.strip("$").isdigit():
                text = int(text.strip("$"))
                return "${:.2E}".format(text)
            return text[: max_length - 3] + "..."
        return text

    def _center(self, start, end, text, font):
        dist = end - start
        width = font.getsize(text)[0]
        start_pos = start + ((dist - width) / 2)
        return int(start_pos)
