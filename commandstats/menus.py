import contextlib
import datetime
from typing import Any, Dict, Iterable, Optional

import discord
import tabulate
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, escape, humanize_number
from redbot.vendored.discord.ext import menus


class GenericMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(
        self,
        source: menus.PageSource,
        cog: Optional[commands.Cog] = None,
        title: Optional[str] = None,
        _type: Optional[str] = None,
        ctx=None,
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
        self.title = title
        self._type = _type
        self.timestamp = timestamp
        self.ctx = ctx
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


class EmbedFormat(menus.ListPageSource):
    def __init__(self, entries: Iterable[str]):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: GenericMenu, data) -> str:
        stats = []
        for item in data:
            stats.append(item)
        embed = discord.Embed(
            title=menu.title,
            colour=await menu.ctx.embed_color(),
            description=box(
                tabulate.tabulate(stats, headers=[menu._type, "Times Used"]), lang="prolog"
            ),
        )
        if menu.timestamp is not None:
            embed.set_footer(text="Recording commands since")
            embed.timestamp = menu.timestamp
        else:
            embed.set_footer(
                text="Page {page}/{amount}".format(
                    page=menu.current_page + 1, amount=menu._source.get_max_pages()
                )
            )
        return embed


class LeaderboardSource(menus.ListPageSource):
    def __init__(self, entries):
        super().__init__(entries, per_page=10)

    async def format_page(self, menu: GenericMenu, entries):
        bot = menu.ctx.bot
        position = (menu.current_page * self.per_page) + 1
        bal_len = len(humanize_number(entries[0][1]))
        pound_len = len(str(position + 9))
        header = "{pound:{pound_len}}{score:{bal_len}}{name:2}\n".format(
            pound="#",
            name=("Name"),
            score=("Score"),
            bal_len=bal_len + 6,
            pound_len=pound_len + 3,
        )
        msg = ""
        for i, data in enumerate(entries, start=position):
            try:
                server = bot.get_guild(int(data[0])).name
            except AttributeError:
                server = "<unknown server>"
            name = escape(server, formatting=True)

            balance = data[1]
            balance = humanize_number(balance)
            msg += (
                f"{f'{humanize_number(i)}.': <{pound_len + 2}} "
                f"{balance: <{bal_len + 5}} "
                f"{name}\n"
            )

        bank_name = "Guild Command Leaderboard."
        page = discord.Embed(
            title=("{}").format(bank_name),
            color=await menu.ctx.embed_color(),
            description="{}\n{} ".format(box(header, lang="prolog"), box(msg, lang="md")),
        )
        page.set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()}")

        return page
