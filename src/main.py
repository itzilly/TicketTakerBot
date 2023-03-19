import os
import json
import logging
import discord
from discord.ext import commands


CONFIG_FILE_PATH = '../config.json'


class SimpleClientBot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	async def on_ready(self):
		print(f"Logged in as {self.user.name} ({self.user.id})")
		for guild in self.guilds:
			print(f"{guild.name} ({guild.id})")

	def start_client(self, token: str):
		try:
			self.run(token=token)
		except discord.LoginFailure:
			logging.critical("Invalid bot token has been passed, stopping bot")
			exit(1)


def main():
	if not os.path.exists(CONFIG_FILE_PATH) and not os.path.isfile(CONFIG_FILE_PATH):
		with open(CONFIG_FILE_PATH, 'w') as config_file:
			json.dump({'token': ''}, config_file, indent=2)

	with open(CONFIG_FILE_PATH, 'r') as config_file:
		token = json.load(config_file)['token']

	intents = discord.Intents.default()
	intents.message_content = True
	client = SimpleClientBot(intents=intents, command_prefix="!")
	client.start_client(token=token)


if __name__ == '__main__':
	main()
