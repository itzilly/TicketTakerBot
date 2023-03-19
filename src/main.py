import os
import json
import discord
from discord.ext import commands


CONFIG_FILE_PATH = '../config.json'


def main():
	if not os.path.exists(CONFIG_FILE_PATH) and not os.path.isfile(CONFIG_FILE_PATH):
		with open(CONFIG_FILE_PATH, 'w') as config_file:
			json.dump({'token': ''}, config_file, indent=2)

	with open(CONFIG_FILE_PATH, 'r') as config_file:
		token = json.load(config_file)['token']

	intents = discord.Intents.default()
	client = commands.Bot(intents=intents, command_prefix="!")

	@client.event
	async def on_ready():
		print(f"Logged in as {client.user.name} ({client.user.id})")
		print("Guilds:")
		for guild in client.guilds:
			print(f"Located Guild | {guild.name} ({guild.id})")

	client.run(token=token)


if __name__ == '__main__':
	main()
