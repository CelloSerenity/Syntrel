import discord
from discord import app_commands
from .dm import ConfirmView, relay_channels


@app_commands.command(name="close_dm", description="Close a DM relay channel")
@app_commands.describe(user="The user whose DM relay to close")
async def close_dm(interaction: discord.Interaction, user: discord.Member = None):
    bot = interaction.client
    bot.logger.info(f"Executed close_dm command in {interaction.guild and interaction.guild.name} (ID: {interaction.guild and interaction.guild.id}) by {interaction.user} (ID: {interaction.user.id}) user_param={user and user.id}")
    if not await bot.is_owner(interaction.user):
        embed = discord.Embed(
            title="Permission Denied",
            description="You are not the owner of this bot!",
            color=0xE02B2B,
        )
        embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not user:
        channel_name = interaction.channel.name
        user = discord.utils.get(interaction.guild.members, name=channel_name)

    if not user:
        await interaction.response.send_message("Couldn't find user. Please specify the user.", ephemeral=True)
        bot.logger.info("close_dm could not infer user from channel name")
        return

    if user.id in relay_channels:
        embed = discord.Embed(
            title="Confirm DM Relay Closure",
            description=f"Do you really want to delete the DM relay with {user.display_name}?",
            color=0xE02B2B,
        )
        embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")

        view = ConfirmView(user, bot.get_cog("dmrelay"))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        embed = discord.Embed(
            title="No Active Relay",
            description=f"No active DM relay with {user.display_name}",
            color=0xE02B2B,
        )
        embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    bot.tree.add_command(close_dm)

