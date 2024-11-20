"""
Automate image posts, media generation, and recent avatars on Discord.
https://discord.gg/pfpvault for support
"""
from __future__ import annotations

from typing import (
    Optional,
    ClassVar, 
    Any, 
    List
)
from discord.ext import commands, tasks
from discord import app_commands

import discord
import pathlib
import sqlite3
import config
import random
import pfps


class Steal(commands.AutoShardedBot):
    """
    Automate image posts, media generation, and recent avatars on Discord.
    https://discord.gg/pfpvault for support
    """
    config: ClassVar[config.Config] = config.Config()

    connection: sqlite3.Connection = sqlite3.connect("fuckingdatabaseandshit.db")
    cursor: sqlite3.Cursor = connection.cursor()

    def __init__(self: Steal, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            *args,
            **kwargs,
            command_prefix=self.config.prefix,
            allowed_mentions=discord.AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            intents = discord.Intents.all(), 
            help_command = None
        )

    async def setup_hook(self: Steal) -> None:
        await self.tree.sync()

    def run(self: Steal) -> None:
        super().run(token=self.config.token, reconnect=True)


    @app_commands.command(
        name="avatar",
        description="Get the user's avatar"
    )
    async def avatar(
        self, 
        interaction: discord.Interaction,
        user: Optional[discord.User] = None
    ) -> discord.Message:
        """
        Fetch and display the avatar of a user
        """
        user = user or interaction.user
        return await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{user}", 
                color=0x2B2D31
            )
            .set_image(url=user.avatar_url)
        )


    @app_commands.command(
        name="dump",
        description="Enable or disable periodic dumps in a channel"
    )
    async def dump(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel
    ) -> discord.Message:
        """
        Enable or disable periodic dumps in a channel
        """
        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS dumps (
                guild_id INTEGER,
                channel_id INTEGER, 
                enabled BOOLEAN
            )
            '''
        )
        self.cursor.execute(
            '''
            SELECT enabled 
            FROM dumps 
            WHERE guild_id = ? 
            AND channel_id = ?
            ''', 
            (
                interaction.guild.id, 
                channel.id
            )
        )
        result = self.cursor.fetchone()

        if result:
            current_state = result[0]
            state = not current_state
            self.cursor.execute(
                '''
                UPDATE dumps 
                SET enabled = ? 
                WHERE guild_id = ? 
                AND channel_id = ?
                ''',
                (
                    state,
                    interaction.guild.id,
                    channel.id
                )
            )
            self.connection.commit()
            self.periodic_pfp_task.stop(channel)
            return await interaction.response.send_message(
                f"Periodic dumps have been {'enabled' if state else 'disabled'} in {channel.mention}",
                ephemeral=True
            )
        else:
            self.cursor.execute(
                '''
                INSERT INTO dumps (
                    guild_id, 
                    channel_id, 
                    enabled
                ) 
                VALUES (?, ?, ?)
                ''', 
                (
                    interaction.guild.id,
                    channel.id, 
                    True
                )
            )
            self.connection.commit()
            self.periodic_pfp_task.start(channel)
            return await interaction.response.send_message(
                f"Periodic dumps have been enabled in {channel.mention}",
                ephemeral=True
            )



    @app_commands.command(
        name="generate",
        description="Generate media based on the type"
    )
    async def generate(
        self, 
        interaction: discord.Interaction, 
        type: str
    ) -> discord.Message:
        """
        Generate media based on the type
        """
        media_map = {
            "gif": pfps.PFPS.gifs,
            "icon": pfps.PFPS.icons,
            "banner": pfps.PFPS.banners,
            "matching": pfps.PFPS.matching,
            "display": pfps.PFPS.displays,
        }

        if type not in media_map:
            return await interaction.response.send_message(
                "Invalid type! Available types are: gif, icon, banner, matching, display",
                ephemeral=True
            )

        randomized = random.sample(media_map[type], 9)
        message = "\n".join(
            [
                f"[Media {i+1}]({url})" 
                for i, url 
                in enumerate(
                    randomized
                )
            ]
        )
        return await interaction.response.send_message(message)


    @commands.Cog.listener()
    async def on_user_update(
        self,
        before: discord.User, 
        after: discord.User
    ) -> discord.Message:
        """
        Detect when a user changes their pfp
        """
        if before.avatar != after.avatar:
            embed = discord.Embed(
                title=f"{after} changed their avatar",
                color=0x2B2D31
            )
            embed.set_image(url=after.avatar.url)
            channel: discord.abc.GuildChannel = self.get_channel(self.config.channel)
            return await channel.send(embed=embed)


    @tasks.loop(seconds=5)
    async def periodic_pfp_task(self, channel: discord.TextChannel):
        """
        Continuously send random PFPs from any category every 5 seconds
        """
        a = pfps.PFPS.gifs + pfps.PFPS.icons
        b = random.choice(a)
        await channel.send(f"{b}")


    async def is_periodic_dump_enabled(self, channel: discord.abc.GuildChannel) -> bool:
        """
        Check if periodic dumps are still enabled for the given channel.
        """
        self.cursor.execute(
            '''
            SELECT enabled 
            FROM dumps 
            WHERE guild_id = ? 
            AND channel_id = ?
            ''',
            (
                channel.guild.id, 
                channel.id
            )
        )
        result = self.cursor.fetchone()
        return result and result[0] 


    def run(self: Steal) -> None:
        super().run(token=self.config.token, reconnect=True)