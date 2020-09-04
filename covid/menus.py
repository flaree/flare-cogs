import contextlib
import datetime
from typing import Any, Dict, Iterable, Optional

import discord
import validators
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
from redbot.vendored.discord.ext import menus


class GenericMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        source: menus.PageSource,
        cog: Optional[commands.Cog] = None,
        ctx=None,
        type: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None,
        clear_reactions_after: bool = True,
        delete_message_after: bool = False,
        add_reactions: bool = True,
        using_custom_emoji: bool = False,
        using_embeds: bool = False,
        keyword_to_reaction_mapping: Dict[str, str] = None,
        timeout: int = 180,
        message: discord.Message = None,
        **kwargs: Any,
    ) -> None:
        self.cog = cog
        self.ctx = ctx
        self.type = type
        super().__init__(
            source,
            clear_reactions_after=clear_reactions_after,
            delete_message_after=delete_message_after,
            check_embeds=using_embeds,
            timeout=timeout,
            message=message,
            **kwargs,
        )

    def reaction_check(self, payload):
        """The function that is used to check whether the payload should be processed.
        This is passed to :meth:`discord.ext.commands.Bot.wait_for <Bot.wait_for>`.
        There should be no reason to override this function for most users.
        Parameters
        ------------
        payload: :class:`discord.RawReactionActionEvent`
            The payload to check.
        Returns
        ---------
        :class:`bool`
            Whether the payload should be processed.
        """
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False

        return payload.emoji in self.buttons

    def _skip_single_arrows(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages == 1

    def _skip_double_triangle_buttons(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages <= 2

    # left
    @menus.button(
        "\N{BLACK LEFT-POINTING TRIANGLE}", position=menus.First(1), skip_if=_skip_single_arrows
    )
    async def prev(self, payload: discord.RawReactionActionEvent):
        if self.current_page == 0:
            await self.show_page(self._source.get_max_pages() - 1)
        else:
            await self.show_checked_page(self.current_page - 1)

    @menus.button("\N{CROSS MARK}", position=menus.First(2))
    async def stop_pages_default(self, payload: discord.RawReactionActionEvent) -> None:
        self.stop()
        with contextlib.suppress(discord.NotFound):
            await self.message.delete()

    @menus.button(
        "\N{BLACK RIGHT-POINTING TRIANGLE}", position=menus.First(2), skip_if=_skip_single_arrows
    )
    async def next(self, payload: discord.RawReactionActionEvent):
        if self.current_page == self._source.get_max_pages() - 1:
            await self.show_page(0)
        else:
            await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload: discord.RawReactionActionEvent):
        """go to the first page"""
        await self.show_page(0)

    @menus.button(
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.Last(1),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload: discord.RawReactionActionEvent):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(self._source.get_max_pages() - 1)


class ArticleFormat(menus.ListPageSource):
    def __init__(self, entries: Iterable[str]):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: GenericMenu, data) -> str:
        embed = discord.Embed(
            title=data["title"],
            color=await menu.ctx.embed_colour(),
            description=f"[Click Here for Full data]({data['url']})\n\n{data['description']}",
            timestamp=datetime.datetime.fromisoformat(data["publishedAt"].replace("Z", "")),
        )
        if data["urlToImage"] is not None:
            if validators.url(data["urlToImage"]):
                embed.set_image(url=data["urlToImage"])
        embed.set_author(name=f"{data['author']} - {data['source']['name']}")
        embed.set_footer(text=f"Article {menu.current_page + 1 }/{menu._source.get_max_pages()}")
        return embed


class CovidMenu(menus.ListPageSource):
    def __init__(self, entries: Iterable[str]):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: GenericMenu, country) -> str:
        embed = discord.Embed(
            color=await menu.ctx.embed_colour(),
            title="Covid-19 | {} Statistics".format(country["country"]),
            timestamp=datetime.datetime.utcfromtimestamp(country["updated"] / 1000),
        )
        embed.set_thumbnail(url=country["countryInfo"]["flag"])
        embed.add_field(name="Cases", value=humanize_number(country["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(country["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(country["recovered"]))
        embed.add_field(name=f"Cases {menu.type}", value=humanize_number(country["todayCases"]))
        embed.add_field(name=f"Deaths {menu.type}", value=humanize_number(country["todayDeaths"]))
        embed.add_field(
            name=f"Recovered {menu.type}", value=humanize_number(country["todayRecovered"])
        )
        embed.add_field(name="Critical", value=humanize_number(country["critical"]))
        embed.add_field(name="Active", value=humanize_number(country["active"]))
        embed.add_field(name="Total Tests", value=humanize_number(country["tests"]))
        embed.set_footer(text=f"Page {menu.current_page + 1 }/{menu._source.get_max_pages()}")
        return embed


class CovidStateMenu(menus.ListPageSource):
    def __init__(self, entries: Iterable[str]):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: GenericMenu, state) -> str:
        embed = discord.Embed(
            color=await menu.ctx.embed_colour(),
            title="Covid-19 | USA | {} Statistics".format(state["state"]),
        )
        embed.add_field(name="Cases", value=humanize_number(state["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(state["deaths"]))
        embed.add_field(name=f"Cases {menu.type}", value=humanize_number(state["todayCases"]))
        embed.add_field(name=f"Deaths {menu.type}", value=humanize_number(state["todayDeaths"]))
        embed.add_field(name=f"Active {menu.type}", value=humanize_number(state["active"]))
        embed.add_field(name="Total Tests", value=humanize_number(state["tests"]))
        embed.set_footer(text=f"Page {menu.current_page + 1 }/{menu._source.get_max_pages()}")
        return embed
