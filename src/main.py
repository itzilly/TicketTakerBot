import os
import json
import discord
import logging
import sqlite3
import datetime
import subprocess

from discord.ext import commands
from typing import Optional, Any

CONFIG_FILE_PATH = '../config.json'
BOT_VERSION = '0.0.1'


class GuildConfiguration:
	def __init__(self, sql_response):
		self._sql_response = sql_response
		"""
		Represents a table with a guild's configuration data in it
		:param sql_response:
		"""

	def print_content(self):
		print(self._sql_response)


class MultiServerConfig:
	def __init__(self, auto_load: bool = True):
		"""
		Config handler for the bot.
		:param auto_load: Allows you to load later (required for bot)
		"""
		self._path = '../data.sql'

		self.connection: Optional[sqlite3.Connection] = None
		self.cursor: Optional[sqlite3.Cursor] = None
		if auto_load:
			self.load()

	def load(self) -> None:
		"""
		Loads the config database
		:return:
		"""
		self.connection = sqlite3.Connection(self._path)
		self.cursor = self.connection.cursor()

	def get_guild_config(self, guild_id: int) -> GuildConfiguration:
		"""
		Retrieve a guild's configuration file
		:param guild_id:
		:return
		"""
		query = "SELECT * FROM CONFIG_MASTER WHERE GUILD_ID IS (?)"
		response = self.cursor.execute(query, (guild_id,))
		item = GuildConfiguration(response)
		return item


class SimpleClientBotHelpCommand(commands.HelpCommand):
	async def send_bot_help(self, mapping):
		logo_file = discord.File('../images/TicketTakerLogoScreenshot.png', filename="TicketTaker.png")
		help_embed = discord.Embed(
			title="Ticket Taker Help",
			timestamp=datetime.datetime.now(),
			colour=discord.Color(0x0ac940),
			description=f"Help info for Ticket Taker"
		)
		help_embed.add_field(
			name="Info",
			value="Commands Prefix: `!`\nUse this prefix to run commands ex: `!help` shows this message",
			inline=False
		)
		help_embed.add_field(
			name="Commands",
			value="`!help` | Shows this help message\n"
			      "`!source` | Shows github link for bot's source code\n"
			      "`!version` | Shows the bot's version",
			inline=False

		)
		help_embed.set_footer(text=f"TicketTaker {BOT_VERSION}", icon_url="attachment://TicketTaker.png")
		await self.context.send(embed=help_embed, file=logo_file)


class SimpleClientBot(commands.Bot):
	"""
	Simple discord bot aimed to just help start my project
	"""

	def __init__(self, config: MultiServerConfig, *args, **kwargs):
		intents = discord.Intents.default()
		intents.message_content = True
		super().__init__(intents=intents, command_prefix="!", *args, **kwargs)

		self.server_config = config
		self.bot_version = BOT_VERSION
		self.bot_logo_path = '../images/TicketTakerLogoScreenshot.png'
		self.help_command = SimpleClientBotHelpCommand()

	async def on_ready(self) -> None:
		"""
		Runs when the bot has logged in successfully and is
		ready to preform any task/command etc.
		:return:
		"""
		print(f"Logged in as {self.user.name} ({self.user.id})")
		for guild in self.guilds:
			print(f"Logged into guild: {guild.name} ({guild.id})")

	async def setup_hook(self) -> None:
		await self.add_cog(SimpleClientBotCommandCog(bot=self))

	def start_client(self, token: str) -> None:
		"""
		Starts the discord bot
		:param token:
		:return:
		"""
		try:
			self.run(token=token)
		except discord.LoginFailure:
			logging.critical("Invalid bot token has been passed, stopping bot")
			exit(1)


class SimpleClientBotCommandCog(commands.Cog):
	def __init__(self, bot: SimpleClientBot):
		self.bot = bot

	@commands.command(name="source")
	async def source_command(self, context: commands.Context) -> None:
		"""
		Links the bot's source code (github)
		:param context:
		:return:
		"""
		logo_file = discord.File(self.bot.bot_logo_path, filename="TicketTaker.png")
		await context.channel.send("View the bot's source here: https://github.com/itzilly/TicketTakerBot")

	@commands.command(name="version")
	async def version_command(self, context: commands.Context) -> None:
		"""
		Shows information about the bot's latest version
		:param context:
		:return:
		"""
		logo_file = discord.File(self.bot.bot_logo_path, filename="TicketTaker.png")

		try:
			git_hash = subprocess.check_output(["git", "rev-list", "--count", "--left-only", "@{u}...HEAD"])
			commits_behind = int(git_hash.strip())
			current_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()
			sub_hash = current_hash.decode('UTF-8')[-7:]
		except subprocess.CalledProcessError:
			logging.error("Git installation not found on host!")
			commits_behind = None
			current_hash = None
			sub_hash = None

		version_embed = discord.Embed(
			title="Version Info",
			timestamp=datetime.datetime.now(),
			colour=discord.Color(0x001F3F),
		)

		description = f"Ticket Taker is running version `{self.bot.bot_version}`"
		if commits_behind is not None:
			version_embed.description = f"{description} which is {commits_behind} commits behind\n" \
			                            f"Current commit: `{sub_hash}`"

		version_embed.set_footer(text=f"Ticket Taker v{self.bot.bot_version}", icon_url='attachment://TicketTaker.png')

		await context.reply(embed=version_embed, file=logo_file, mention_author=False)


def main() -> None:
	if not os.path.exists(CONFIG_FILE_PATH) and not os.path.isfile(CONFIG_FILE_PATH):
		with open(CONFIG_FILE_PATH, 'w') as config_file:
			json.dump({'token': ''}, config_file, indent=2)

	with open(CONFIG_FILE_PATH, 'r') as config_file:
		token = json.load(config_file)['token']

	intents = discord.Intents.default()
	intents.message_content = True
	config = MultiServerConfig()
	client = SimpleClientBot(config=config)
	client.start_client(token=token)


if __name__ == '__main__':
	main()
