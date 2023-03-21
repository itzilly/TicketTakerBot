import os
import json
import pytz
import discord
import logging
import sqlite3
import datetime
import subprocess

from typing import Optional, Any
from discord.ext import commands
from discord import app_commands

CONFIG_FILE_PATH = '../config.json'
BOT_VERSION = '0.0.3'


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
		self.pytz_utc = pytz.UTC

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
		self._postload()

	def _postload(self) -> None:
		command = """
		CREATE TABLE IF NOT EXISTS GUILD_IDS (
			ID INTEGER PRIMARY KEY,
			GUILD_ID INTEGER UNIQUE
		)
		"""
		self.cursor.execute(command)

		command = f"""
		CREATE TABLE IF NOT EXISTS GUILD_CONFIGS (
			id INTEGER PRIMARY KEY,
			guild_id INTEGER UNIQUE,
			config JSON NOT NULL DEFAULT {self._get_default_config(version=1)}
		);
		"""
		self.cursor.execute(command)
		self.connection.commit()

	def get_guild_config(self, guild_id: int) -> Optional[str]:
		"""
		Retrieve a guild's configuration file
		:param guild_id:
		:return
		"""
		try:
			data = self._retrieve_guild_config(guild_id)
			return json.loads(data)
		except sqlite3.OperationalError as e:
			if "no such table: CONFIG_MASTER" in str(e):
				logging.debug(f"No config table found for guild {guild_id}")
				self._generate_guild_config(guild_id)
				raise SystemError(f"Unable to locate table for guild {guild_id}")
		except json.JSONDecodeError as e:
			raise ValueError(f"Invalid json when parsing database config for {guild_id}: {e}")

	def sync_guild_ids(self, guilds: list[int]):
		"""
		This ensures that the configs are up-to-date
		with all guild id's the bot is in. This also will
		ensure that a row exists for each guild in the
		GUILD_CONFIGS table.
		"""
		for guild_id in guilds:
			self.sync_guild_id(guild_id)

	def sync_guild_id(self, guild_id: int) -> None:
		"""
		This ensures that the guild id will have an
		empty/existing config row in the MASTER_CONFIG table.
		"""
		try:
			command = "SELECT COUNT(*) FROM GUILD_CONFIGS WHERE GUILD_ID = ?"
			result = self.cursor.execute(command, (guild_id,))
			count = result.fetchone()[0]
			if count == 0:
				self._generate_guild_config(guild_id)
		except sqlite3.OperationalError as e:
			logging.error(f"Error syncing guild id: {guild_id}: ")
			logging.error(e)
		except Exception as e:
			logging.error(f"Unknown error syncing guild id: {guild_id}")
			logging.error(e)
		self._ensure_guild_data(guild_id)
		self.connection.commit()

	def _ensure_guild_data(self, guild_id: int):
		"""
		Ensures that the guild id has a row in the master config table
		"""

	def _retrieve_guild_config(self, guild_id: int):
		query = "SELECT config FROM CONFIG_MASTER WHERE GUILD_ID IS (?)"
		response = self.cursor.execute(query, (guild_id,))
		return response.fetchone()

	def _generate_guild_config(self, guild_id: int) -> None:

		# Check if a row with the specified guild_id already exists
		command = "SELECT COUNT(*) FROM GUILD_CONFIGS WHERE GUILD_ID = ?"
		self.cursor.execute(command, (guild_id,))
		count = self.cursor.fetchone()[0]
		if count > 0:
			raise ValueError(f"A row with guild_id={guild_id} already exists in GUILD_CONFIGS")

		# Create entry for guild
		command = """
		INSERT INTO GUILD_CONFIGS (
			GUILD_ID,
			TICKET_SECTION_ID,
			CREATE_TICKET_MESSAGE_ID
		) VALUES (
			?,
			NULL,
			NULL
		)
		"""
		self.cursor.execute(command, (guild_id,))
		self.connection.commit()

	def _get_default_config(self, version: int):
		time_generated = datetime.datetime.now(tz=self.pytz_utc).timestamp()
		version_1_dict = {
			'config_version': 1,
			'config_generated_at': str(time_generated),
			'bot_admin_role_id': None,
			'create_new_tickets_in_category': False,
			'ticket_category': {
				'id': None,
			},
			'ticket_creation_message_id': None,
		}

		match version:
			case 1:
				return f"'{json.dumps(version_1_dict)}'"

		raise ValueError(f"Invalid default config version number in _get_default_config(self, version: int): {version}")


class SimpleClientBot(commands.Bot):
	"""
	Simple discord bot aimed to just help start my project
	"""

	def __init__(self, config: MultiServerConfig, *args, **kwargs):
		intents = discord.Intents.default()
		intents.message_content = True
		prefix = commands.when_mentioned
		description = "Support Ticket Tool Bot"
		super().__init__(
			intents=intents,
			command_prefix=prefix,
			description=description,
			*args, **kwargs
		)

		self.server_config = config
		self.bot_version = BOT_VERSION
		self.bot_logo_path = '../images/TicketTakerLogoScreenshot.png'

	async def on_ready(self) -> None:
		"""
		Runs when the bot has logged in successfully and is
		ready to preform any task/command etc.
		:return:
		"""
		print(f"Logged in as {self.user.name} ({self.user.id})")
		for guild in self.guilds:
			print(f"  Logged into guild: {guild.name} ({guild.id})")
			self.server_config.sync_guild_id(guild.id)
		await self.tree.sync()

	async def setup_hook(self) -> None:
		default_cogs = [
			SimpleClientBotCommandCog,
			SimpleClientBotEventCog
		]
		for cog in default_cogs:
			logging.debug(f"Loading cog {cog.__name__}")
			await self.add_cog(cog(bot=self))

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

	@app_commands.command(name="help", description="Show help for Ticket Taker Bot")
	async def help_command(self, interaction: discord.Interaction) -> None:
		"""
		Shows help message for the bot
		:param interaction:
		:return:
		"""
		response: Optional[discord.InteractionResponse | Any] = interaction.response
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
		await response.send_message(embed=help_embed, file=logo_file)

	@app_commands.command(name="source", description="View source code for bot")
	async def source_command(self, interaction: discord.Interaction) -> None:
		"""
		Links the bot's source code (GitHub)
		:param interaction:
		:return:
		"""
		response: Optional[discord.InteractionResponse | Any] = interaction.response
		await response.send_message(
			"View the bot's source here: https://github.com/itzilly/TicketTakerBot",
			suppress_embeds=True
		)

	@app_commands.command(name="version", description="Show the current version the bot is running")
	async def version_command(self, interaction: discord.Interaction) -> None:
		"""
		Shows information about the bot's latest version
		:param interaction:
		:return:
		"""
		response: Optional[discord.InteractionResponse | Any] = interaction.response
		await response.defer()

		logo_file = discord.File(self.bot.bot_logo_path, filename="TicketTaker.png")

		try:
			fetch = subprocess.check_output(["git", "fetch"])
			git_hash = subprocess.check_output(["git", "rev-list", "--count", "--left-only", "@{u}...HEAD"])
			commits_behind = int(git_hash.strip())
			current_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()
			sub_hash = current_hash.decode('UTF-8')[-7:]
		except subprocess.CalledProcessError:
			logging.error("Git installation not found on host!")
			commits_behind = None
			sub_hash = None

		version_embed = discord.Embed(
			title="Version Info",
			timestamp=datetime.datetime.now(),
			colour=discord.Color(0x001F3F),
		)

		description = f"Ticket Taker is running version `{self.bot.bot_version}`"
		if commits_behind is not None:
			version_embed.description = f"{description} which is {commits_behind} commit(s) behind\n" \
			                            f"Current commit: `{sub_hash}`"

		version_embed.set_footer(text=f"Ticket Taker v{self.bot.bot_version}", icon_url='attachment://TicketTaker.png')

		await interaction.edit_original_response(
			content=None,
			embed=version_embed,
			attachments=[logo_file]
		)


class SimpleClientBotEventCog(commands.Cog):
	def __init__(self, bot: SimpleClientBot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_guild_join(self, guild: discord.Guild) -> None:
		print(f"Joined a guild: {guild.name}")
		command = """
			SELECT EXISTS(SELECT 1 FROM GUILD_IDS WHERE guild_id = ?);
		"""
		query = self.bot.server_config.cursor.execute(command, (guild.id, ))
		result = query.fetchall()
		if len(result) > 1:
			logging.error("Found multiple guild entries with the same guild ID")
			return
		command = """
			INSERT INTO GUILD_IDS (guild_id) VALUES (?);
		"""
		self.bot.server_config.cursor.execute(command)

	@commands.Cog.listener()
	async def on_guild_remove(self, guild: discord.Guild) -> None:
		print("I just left a guild!")
		command = """
			DELETE FROM GUILD_IDS WHERE guild_id = ?;
		"""
		self.bot.server_config.cursor.execute(command, (guild.id, ))


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
