import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Context
import asyncio
import os
import aiosqlite
import io

relay_channels = {}
channel_webhooks = {}

class ConfirmView(discord.ui.View):
    def __init__(self, user, cog):
        super().__init__(timeout=60)
        self.user = user
        self.cog = cog

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.bot.is_owner(interaction.user):
            embed = discord.Embed(
                title="Permission Denied",
                description="You are not the owner of this bot!",
                color=0xE02B2B,
            )
            embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if self.user.id in relay_channels:
            channel_id = relay_channels[self.user.id]
            del relay_channels[self.user.id]
            if channel_id in channel_webhooks:
                del channel_webhooks[channel_id]
        
        await self.cog.remove_relay_from_db(self.user.id)
        self.cog.bot.logger.info(f"Closed DM relay for user {self.user.id} by {interaction.user} ({interaction.user.id}) in {interaction.guild and interaction.guild.name}")
        
        embed = discord.Embed(
            title="DM Relay Closed",
            description=f"Successfully closed DM relay with {self.user.display_name}",
            color=0x00FF00,
        )
        embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
        await interaction.response.edit_message(embed=embed, view=None)
        
        if interaction.channel.name == self.user.name.lower():
            embed = discord.Embed(
                title="Channel Deletion",
                description="Deleting this channel in 5 seconds...",
                color=0xE02B2B,
            )
            embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
            await interaction.followup.send(embed=embed, ephemeral=True)
            await asyncio.sleep(5)
            await interaction.channel.delete()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.bot.is_owner(interaction.user):
            embed = discord.Embed(
                title="Permission Denied",
                description="You are not the owner of this bot!",
                color=0xE02B2B,
            )
            embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Cancelled",
            description="DM relay closure cancelled",
            color=0x7289DA,
        )
        embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
        await interaction.response.edit_message(embed=embed, view=None)
        self.cog.bot.logger.info(f"Cancelled DM relay closure for user {self.user.id} by {interaction.user} ({interaction.user.id})")

class DMModal(discord.ui.Modal, title='Send DM'):
    def __init__(self, target_user, bot):
        super().__init__()
        self.target_user = target_user
        self.bot = bot

    message = discord.ui.TextInput(
        label='Message',
        placeholder='Type your message here...',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.target_user.send(self.message.value)
            self.bot.logger.info(f"Sent initial DM to user {self.target_user} ({self.target_user.id}) by {interaction.user} ({interaction.user.id})")
            
            embed = discord.Embed(
                title="Message Sent",
                description=f"Message sent to {self.target_user.display_name}!",
                color=0x00FF00,
            )
            embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            support_guild_id_env = os.getenv('DM_GUILD_ID') or os.getenv('SUPPORT_GUILD_ID')
            if support_guild_id_env:
                guild = self.bot.get_guild(int(support_guild_id_env))
            else:
                guild = interaction.guild
            if guild:
                self.bot.logger.info(f"Using guild {guild.name} ({guild.id}) for DM relay channel for user {self.target_user.id}")
            channel_name = self.target_user.name.lower()
            
            existing_channel = discord.utils.get(guild.channels, name=channel_name)
            
            if not existing_channel:
                category_id_env = os.getenv('DM_CATEGORY_ID')
                if not category_id_env:
                    self.bot.logger.warning("DM_CATEGORY_ID not configured; cannot create DM relay channel")
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="Category Not Configured",
                            description="DM_CATEGORY_ID is not set in the environment.",
                            color=0xE02B2B,
                        ).set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp"),
                        ephemeral=True,
                    )
                    return
                category_id = int(category_id_env)
                category = guild.get_channel(category_id)
                
                if not category or not isinstance(category, discord.CategoryChannel) or category.guild.id != guild.id:
                    embed = discord.Embed(
                        title="Category Not Found",
                        description=f"Category ID {category_id} not found in the target guild or is not a category. Check DM_GUILD_ID/DM_CATEGORY_ID.",
                        color=0xE02B2B,
                    )
                    embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    self.bot.logger.warning(f"Category validation failed for DM relay: category_id={category_id} guild_id={guild.id}")
                    return
                
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"DM relay with {self.target_user.display_name} ({self.target_user.id})"
                )
                self.bot.logger.info(f"Created DM relay channel #{channel.name} ({channel.id}) in guild {guild.id} for user {self.target_user.id}")
                
                webhook = await channel.create_webhook(name="DM Relay Webhook")
                channel_webhooks[channel.id] = webhook
                self.bot.logger.info(f"Created DM relay webhook {webhook.id} for channel {channel.id}")
                
                await self.bot.get_cog("dmrelay").save_relay_to_db(
                    self.target_user.id, channel.id, webhook.id, webhook.token
                )
                self.bot.logger.info(f"Saved DM relay mapping user {self.target_user.id} -> channel {channel.id}")
                
                embed = discord.Embed(
                    title="DM Relay Started",
                    description=f"DM relay has been established with {self.target_user.display_name}\n Use `/dm user:{self.target_user.mention}` to send messages!",
                    color=0x7289DA,
                )
                embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
                await channel.send(embed=embed)
            else:
                channel = existing_channel
                if channel.id not in channel_webhooks:
                    webhooks = await channel.webhooks()
                    webhook = None
                    for wh in webhooks:
                        if wh.name == "DM Relay Webhook":
                            webhook = wh
                            break
                    if not webhook:
                        webhook = await channel.create_webhook(name="DM Relay Webhook")
                    channel_webhooks[channel.id] = webhook
                    self.bot.logger.info(f"Attached DM relay webhook {webhook.id} to existing channel {channel.id}")
                    
                    await self.bot.get_cog("dmrelay").save_relay_to_db(
                        self.target_user.id, channel.id, webhook.id, webhook.token
                    )
                    self.bot.logger.info(f"Saved DM relay mapping user {self.target_user.id} -> channel {channel.id}")
            
            relay_channels[self.target_user.id] = channel.id
            
            webhook = channel_webhooks[channel.id]
            await webhook.send(
                content=self.message.value,
                username=interaction.user.display_name,
                avatar_url=interaction.user.display_avatar.url
            )
            self.bot.logger.info(f"Relayed owner message to channel {channel.id} for user {self.target_user.id}")
            
        except discord.Forbidden:
            self.bot.logger.warning(f"Forbidden sending DM to user {self.target_user.id}; likely DMs disabled")
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Couldn't send DM to {self.target_user.display_name}. They might have DMs disabled.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Couldn't send DM to {self.target_user.display_name}. They might have DMs disabled.",
                    ephemeral=True
                )
        except Exception as e:
            self.bot.logger.error(f"Error in DMModal.on_submit for user {self.target_user.id}: {e}")
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Error sending message: {str(e)}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Error sending message: {str(e)}",
                    ephemeral=True
                )

class DMRelay(commands.Cog, name="dmrelay"):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def save_relay_to_db(self, user_id: int, channel_id: int, webhook_id: int, webhook_token: str):
        async with aiosqlite.connect("database/database.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO dm_relays (user_id, channel_id, webhook_id, webhook_token) VALUES (?, ?, ?, ?)",
                (str(user_id), str(channel_id), str(webhook_id), webhook_token)
            )
            await db.commit()
        self.bot.logger.info(f"DB save dm_relays: user_id={user_id} channel_id={channel_id} webhook_id={webhook_id}")

    async def remove_relay_from_db(self, user_id: int):
        async with aiosqlite.connect("database/database.db") as db:
            await db.execute("DELETE FROM dm_relays WHERE user_id = ?", (str(user_id),))
            await db.commit()
        self.bot.logger.info(f"DB remove dm_relays: user_id={user_id}")

    async def load_relays_from_db(self):
        self.bot.logger.info("Loading DM relays from database...")
        async with aiosqlite.connect("database/database.db") as db:
            async with db.execute("SELECT user_id, channel_id, webhook_id, webhook_token FROM dm_relays") as cursor:
                rows = await cursor.fetchall()
                self.bot.logger.info(f"Found {len(rows)} DM relays in database")
                for row in rows:
                    user_id, channel_id, webhook_id, webhook_token = row
                    user_id = int(user_id)
                    channel_id = int(channel_id)
                    webhook_id = int(webhook_id)
                    
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            webhook = discord.Webhook.from_url(f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}", client=self.bot)
                            relay_channels[user_id] = channel_id
                            channel_webhooks[channel_id] = webhook
                            self.bot.logger.info(f"Restored DM relay for user {user_id} in channel {channel_id}")
                        except Exception as e:
                            self.bot.logger.warning(f"Failed to restore webhook for user {user_id}: {e}")
                            await self.remove_relay_from_db(user_id)
                    else:
                        self.bot.logger.warning(f"Channel {channel_id} not found, removing relay for user {user_id}")
                        await self.remove_relay_from_db(user_id)
        self.bot.logger.info(f"DM relay loading complete. Active relays: {len(relay_channels)}")

    async def _load_relays_after_ready(self):
        await self.bot.wait_until_ready()
        await self.load_relays_from_db()

    async def send_embed(self, context: Context, embed: discord.Embed, *, ephemeral: bool = False) -> None:
        interaction = getattr(context, "interaction", None)
        if interaction is not None:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        else:
            await context.send(embed=embed)

    @app_commands.command(name="dm", description="Send a DM to a user")
    @app_commands.describe(user="The user to send a DM to")
    async def dm_command(self, interaction: discord.Interaction, user: discord.Member):
        self.bot.logger.info(f"Executed dm command in {interaction.guild and interaction.guild.name} (ID: {interaction.guild and interaction.guild.id}) by {interaction.user} (ID: {interaction.user.id}) target {user} (ID: {user.id})")
        if not await self.bot.is_owner(interaction.user):
            embed = discord.Embed(
                title="Permission Denied",
                description="You are not the owner of this bot!",
                color=0xE02B2B,
            )
            embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        if user == interaction.user:
            await interaction.response.send_message("You can't DM yourself!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.response.send_message("You can't DM bots!", ephemeral=True)
            return
        
        modal = DMModal(user, self.bot)
        await interaction.response.send_modal(modal)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if isinstance(message.channel, discord.DMChannel):
            user_id = message.author.id
            
            if user_id in relay_channels:
                channel = self.bot.get_channel(relay_channels[user_id])
                if channel:
                    self.bot.logger.info(f"Forwarding DM from user {user_id} to channel {channel.id}")
                    webhook = channel_webhooks.get(channel.id)
                    if not webhook:
                        webhooks = await channel.webhooks()
                        for wh in webhooks:
                            if wh.name == "DM Relay Webhook":
                                webhook = wh
                                break
                        if not webhook:
                            webhook = await channel.create_webhook(name="DM Relay Webhook")
                        channel_webhooks[channel.id] = webhook
                        self.bot.logger.info(f"Recreated/attached webhook {webhook.id} for channel {channel.id} during DM forward")
                    
                    content = message.content if message.content else ""
                    
                    files = []
                    if message.attachments:
                        for attachment in message.attachments:
                            try:
                                if attachment.size <= 8388608:  # 8MB limit
                                    file_data = await attachment.read()
                                    files.append(discord.File(
                                        fp=io.BytesIO(file_data),
                                        filename=attachment.filename
                                    ))
                                else:
                                    content += f"\nAttachment: {attachment.filename} (File too large: {attachment.size} bytes)"
                            except Exception as e:
                                content += f"\nAttachment: {attachment.filename} (Error: {str(e)})"
                    
                    await webhook.send(
                        content=content,
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar.url,
                        files=files
                    )
                else:
                    self.bot.logger.warning(f"Relay channel missing for user {user_id}; cleaning up state and DB")
                    del relay_channels[user_id]
                    if user_id in relay_channels and relay_channels[user_id] in channel_webhooks:
                        del channel_webhooks[relay_channels[user_id]]
                    await self.remove_relay_from_db(user_id)

    async def cog_command_error(self, context: Context, error) -> None:
        if isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                title="Permission Denied",
                description="You are not the owner of this bot!",
                color=0xE02B2B,
            )
            embed.set_author(name="Owner", icon_url="https://yes.nighty.works/raw/zReOib.webp")
            await self.send_embed(context, embed, ephemeral=True)
        else:
            raise error

async def setup(bot) -> None:
    cog = DMRelay(bot)
    await bot.add_cog(cog)
    bot.loop.create_task(cog._load_relays_after_ready())