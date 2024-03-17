import logging

import discord
from discord.ui import Button, Modal, TextInput, View

from .objects import AlreadyEnteredError, GiveawayEnterError, GiveawayExecError

log = logging.getLogger("red.flare.giveaways")


class GiveawayView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog


BUTTON_STYLE = {
    "blurple": discord.ButtonStyle.primary,
    "grey": discord.ButtonStyle.secondary,
    "green": discord.ButtonStyle.success,
    "red": discord.ButtonStyle.danger,
    "gray": discord.ButtonStyle.secondary,
}


class GiveawayButton(Button):
    def __init__(
        self,
        label: str,
        style: str,
        emoji,
        cog,
        id,
        update=False,
    ):
        super().__init__(
            label=label, style=BUTTON_STYLE[style], emoji=emoji, custom_id=f"giveaway_button:{id}"
        )
        self.default_label = label
        self.update = update
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.message.id in self.cog.giveaways:
            giveaway = self.cog.giveaways[interaction.message.id]
            await interaction.response.defer()
            try:
                await giveaway.add_entrant(
                    interaction.user, bot=self.cog.bot, session=self.cog.session
                )
            except GiveawayEnterError as e:
                await interaction.followup.send(e.message, ephemeral=True)
                return
            except GiveawayExecError as e:
                log.exception("Error while adding user to giveaway", exc_info=e)
                return
            except AlreadyEnteredError:
                await interaction.followup.send(
                    "You have been removed from the giveaway.", ephemeral=True
                )
                await self.update_entrant(giveaway, interaction)
                await self.update_label(giveaway, interaction)
                return
            await self.update_entrant(giveaway, interaction)
            await interaction.followup.send(
                f"You have been entered into the giveaway for {giveaway.prize}.",
                ephemeral=True,
            )
            await self.update_label(giveaway, interaction)

    async def update_entrant(self, giveaway, interaction):
        await self.cog.config.custom(
            "giveaways", interaction.guild_id, interaction.message.id
        ).entrants.set(self.cog.giveaways[interaction.message.id].entrants)

    async def update_label(self, giveaway, interaction):
        if self.update:
            if len(giveaway.entrants) >= 1:
                self.label = f"{self.default_label} ({len(giveaway.entrants)})"
            if len(giveaway.entrants) == 0:
                self.label = self.default_label
            await interaction.message.edit(view=self.view)
