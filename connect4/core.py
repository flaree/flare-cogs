from itertools import chain, groupby
from typing import Union

import discord
from redbot.core import commands
from redbot.vendored.discord.ext import menus


class Board(list):
    __slots__ = frozenset({"width", "height"})

    def __init__(self, width, height, player1_name=None, player2_name=None):
        self.width = width
        self.height = height
        for x in range(width):
            self.append([0] * height)

    def __getitem__(self, pos: Union[int, tuple]):
        if isinstance(pos, int):
            return list(self)[pos]
        elif isinstance(pos, tuple):
            x, y = pos
            return list(self)[x][y]
        else:
            raise TypeError("pos must be an int or tuple")

    def __setitem__(self, pos: Union[int, tuple], new_value):
        x, y = self._xy(pos)

        if self[x, y] != 0:
            raise IndexError("there's already a move at that position")

        # basically self[x][y] = new_value
        # super().__getitem__(x).__setitem__(y, new_value)
        self[x][y] = new_value

    def _xy(self, pos):
        if isinstance(pos, tuple):
            return pos[0], pos[1]
        elif isinstance(pos, int):
            x = pos
            return x, self._y(x)
        else:
            raise TypeError("pos must be an int or tuple")

    def _y(self, x):
        """find the lowest empty row for column x"""
        # start from the bottom and work up
        for y in range(self.height - 1, -1, -1):
            if self[x, y] == 0:
                return y
        raise ValueError("that column is full")

    def _pos_diagonals(self):
        """Get positive diagonals, going from bottom-left to top-right."""
        for di in (
            [(j, i - j) for j in range(self.width)] for i in range(self.width + self.height - 1)
        ):
            yield [
                self[i, j]
                for i, j in di
                if i >= 0 and j >= 0 and i < self.width and j < self.height
            ]

    def _neg_diagonals(self):
        """Get negative diagonals, going from top-left to bottom-right."""
        for di in (
            [(j, i - self.width + j + 1) for j in range(self.height)]
            for i in range(self.width + self.height - 1)
        ):
            yield [
                self[i, j]
                for i, j in di
                if i >= 0 and j >= 0 and i < self.width and j < self.height
            ]

    def _full(self):
        """is there a move in every position?"""

        for x in range(self.width):
            if self[x, 0] == 0:
                return False
        return True


class Connect4Game:
    __slots__ = frozenset({"board", "turn_count", "_whomst_forfeited", "names", "player1", "player2", "players"})

    FORFEIT = -2
    TIE = -1
    NO_WINNER = 0

    PIECES = "\N{medium white circle}" "\N{large red circle}" "\N{large blue circle}"

    def __init__(self, player1: discord.Member, player2: discord.Member):
        self.player1 = player1
        self.player2 = player2
        self.players = (player1, player2)
        self.names = (player1.display_name, player2.display_name)

        self.board = Board(7, 6)
        self.turn_count = 0
        self._whomst_forfeited = 0

    def move(self, column):
        self.board[column] = self.whomst_turn()
        self.turn_count += 1

    def forfeit(self):
        """forfeit the game as the current player"""
        self._whomst_forfeited = self.whomst_turn_name()

    def _get_forfeit_status(self):
        if self._whomst_forfeited:
            status = "{} won ({} forfeited)\n"

            return status.format(self.other_player_name(), self.whomst_turn_name())

        raise ValueError("nobody has forfeited")

    def __str__(self):
        win_status = self.whomst_won()
        status = self._get_status()
        instructions = ""

        if win_status == self.NO_WINNER:
            instructions = self._get_instructions()
        elif win_status == self.FORFEIT:
            status = self._get_forfeit_status()

        return (
            status
            + instructions
            + "\n".join(self._format_row(y) for y in range(self.board.height))
        )

    def _get_status(self):
        win_status = self.whomst_won()

        if win_status == self.NO_WINNER:
            status = self.whomst_turn_name() + "'s turn " + self.PIECES[self.whomst_turn()]
        elif win_status == self.TIE:
            status = "It's a tie!"
        elif win_status == self.FORFEIT:
            status = self._get_forfeit_status()
        else:
            status = self._get_player_name(win_status) + " won!"
        return status + "\n"

    def _get_instructions(self):
        instructions = ""
        for i in range(1, self.board.width + 1):
            instructions += str(i) + "\N{combining enclosing keycap}"
        return instructions + "\n"

    def _format_row(self, y):
        return "".join(self[x, y] for x in range(self.board.width))

    def __getitem__(self, pos):
        x, y = pos
        return self.PIECES[self.board[x, y]]

    def whomst_won(self):
        """Get the winner on the current board.
		If there's no winner yet, return Connect4Game.NO_WINNER.
		If it's a tie, return Connect4Game.TIE"""

        lines = (
            self.board,  # columns
            zip(*self.board),  # rows (zip picks the nth item from each column)
            self.board._pos_diagonals(),  # positive diagonals
            self.board._neg_diagonals(),  # negative diagonals
        )

        if self._whomst_forfeited:
            return self.FORFEIT

        for line in chain(*lines):
            for player, group in groupby(line):
                if player != 0 and len(list(group)) >= 4:
                    return player

        if self.board._full():
            return self.TIE
        else:
            return self.NO_WINNER

    def other_player_name(self):
        self.turn_count += 1
        other_player_name = self.whomst_turn_name()
        self.turn_count -= 1
        return other_player_name

    def whomst_turn_name(self):
        return self._get_player_name(self.whomst_turn())

    def whomst_turn(self):
        return self.turn_count % 2 + 1

    def _get_player_name(self, player_number):
        player_number -= 1  # these lists are 0-indexed but the players aren't

        return self.names[player_number]

    @property
    def current_player(self) -> discord.Member:
        player_number = self.whomst_turn() - 1
        return self.players[player_number]


class Connect4Menu(menus.Menu):
    def __init__(self, cog, game: Connect4Game):
        self.cog = cog
        self.game = game
        super().__init__(timeout=cog.GAME_TIMEOUT_THRESHOLD, delete_message_after=False, clear_reactions_after=True)
        for index, digit in enumerate(cog.DIGITS):
            self.add_button(menus.Button(digit, self.handle_digit_press, position=menus.First(index)))

    def reaction_check(self, payload: discord.RawReactionActionEvent):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id != self.game.current_player.id:
            return False
        return payload.emoji in self.buttons

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel) -> discord.Message:
        return await channel.send(self.game)

    async def handle_digit_press(self, payload: discord.RawReactionActionEvent):
        try:
            # convert the reaction to a 0-indexed int and move in that column
            self.game.move(self.cog.DIGITS.index(str(payload.emoji)))
        except ValueError:
            pass  # the column may be full
        await self.edit(content=self.game)
    
    @menus.button("🚫", position=menus.Last(0))
    async def close_menu(self, payload: discord.RawReactionActionEvent):
        ...

    async def edit(self, **kwargs):
        try:
            await self.message.edit(**kwargs)
        except discord.NotFound:
            self.cancel("Connect4 game cancelled since the message was deleted.")
        except discord.Forbidden:
            self.cancel(None)

    async def cancel(self, message: str = "Connect4 game cancelled."):
        if message:
            await self.ctx.send(message)
        self.stop()
