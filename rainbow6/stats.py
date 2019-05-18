import aiohttp
import asyncio

class Stats:

    def __init__(self, bot):
        self.bot = bot
        self.url = "https://www.antisnakedetail.xyz/r6/"
        self.session = self._session = aiohttp.ClientSession(loop=self.bot.loop)
    
    async def profileid(self, name, platform):
        async with self._session.get(self.url + "/getSmallUser.php?name={}&platform={}&appcode=flare".format(name, platform)) as response:
            profile = await response.json(content_type="text/html")
            return list(profile.keys())[0]

    async def profile(self, account, platform):
        async with self._session.get(self.url + "/getUser.php?name={}&platform={}&appcode=flare".format(account, platform)) as response:
            return await response.json(content_type="text/html")

    async def season(self, account, platform, season):
        async with self._session.get(self.url + "/getUser.php?name={}&platform={}&season={}&appcode=flare".format(account, platform, season)) as response:
            return await response.json(content_type="text/html")

    async def stats(self, account, platform):
        async with self._session.get(self.url + "/getStats.php?name={}&platform={}&appcode=flare".format(account, platform)) as response:
            return await response.json(content_type="text/html")

    async def operators(self, account, platform):
        async with self._session.get(self.url + "/getOperators.php?name={}&platform={}&appcode=flare".format(account, platform)) as response:
            return await response.json(content_type="text/html")

    async def getimg(self, url):
        async with self._session.get(url) as response:
            rank = await response.read()
            return rank
    def cog_unload(self):
        self.bot.loop.create_task(self._session.close())