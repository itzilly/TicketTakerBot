import os
import json
import logging
import sqlite3

import discord
from discord.ext import commands


CONFIG_FILE_PATH = '../config.json'


class GuildConfiguration:
	def __init__(self, sql_response):
		self._sql_response = sql_response
		"""
		Represents a table with a guild's configuration data in it
		:param sql_response:
		"""

	def _print_content(self):
		print(self._sql_response)


class MultiServerConfig:
	def __init__(self, auto_load: bool = True):
		"""
		Config handler for the bot.
		:param auto_load: Allows you to load later (required for bot)
		"""
		self._path = '../data.sql'

		self.connection: sqlite3.Connection = None
		self.cursor: sqlite3.Cursor = None
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
		response = self.cursor.execute(query, (guild_id, ))
		item = GuildConfiguration(response)
		return item


class SimpleClientBot(commands.Bot):
	"""
	Simple discord bot aimed to just help start my project
	"""
	def __init__(self, config: MultiServerConfig, *args, **kwargs):
		self.server_config = config
		super().__init__(*args, **kwargs)

	async def on_ready(self):
		print(f"Logged in as {self.user.name} ({self.user.id})")
		for guild in self.guilds:
			print(f"Logged into guild: {guild.name} ({guild.id})")

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


def main() -> None:
	if not os.path.exists(CONFIG_FILE_PATH) and not os.path.isfile(CONFIG_FILE_PATH):
		with open(CONFIG_FILE_PATH, 'w') as config_file:
			json.dump({'token': ''}, config_file, indent=2)

	with open(CONFIG_FILE_PATH, 'r') as config_file:
		token = json.load(config_file)['token']

	intents = discord.Intents.default()
	intents.message_content = True
	config = MultiServerConfig()
	client = SimpleClientBot(config=config, intents=intents, command_prefix="!")
	client.start_client(token=token)


if __name__ == '__main__':
	main()
