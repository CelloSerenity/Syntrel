import discord
from discord import app_commands
from .dm import DMModal


@app_commands.command(name="dm_id", description="Send a DM to a user by their ID")
@app_commands.describe(user_id="The user ID to send a DM to")
async def dm_id_command(interaction: discord.Interaction, user_id: str):
    bot = interaction.client
    bot.logger.info(f"Executed dm_id command in {interaction.guild and interaction.guild.name} (ID: {interaction.guild and interaction.guild.id}) by {interaction.user} (ID: {interaction.user.id}) target_id {user_id}")
    if not await bot.is_owner(interaction.user):
        embed = discord.Embed(
            title="Permission Denied",
            description="You are not the owner of this bot!",
            color=0xE02B2B,
        )
        embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user_id_int = int(user_id)
    except ValueError:
        await interaction.response.send_message("Invalid user ID format!", ephemeral=True)
        return

    if user_id_int == interaction.user.id:
        await interaction.response.send_message("You can't DM yourself!", ephemeral=True)
        return

    try:
        user = await bot.fetch_user(user_id_int)
        bot.logger.info(f"Fetched user by ID {user_id_int} for dm_id command")
    except discord.NotFound:
        bot.logger.info(f"dm_id user not found: {user_id_int}")
        await interaction.response.send_message("User not found!", ephemeral=True)
        return
    except discord.HTTPException as e:
        bot.logger.warning(f"dm_id HTTP error fetching user {user_id_int}: {e}")
        await interaction.response.send_message(f"Error fetching user: {str(e)}", ephemeral=True)
        return

    if user.bot:
        await interaction.response.send_message("You can't DM bots!", ephemeral=True)
        return

    modal = DMModal(user, bot)
    await interaction.response.send_modal(modal)


async def setup(bot):
    bot.tree.add_command(dm_id_command)

