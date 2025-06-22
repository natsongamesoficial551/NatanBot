import discord
from discord.ext import commands, tasks
import itertools
import asyncio

class StatusCustom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Lista de status que serão mostrados
        self.status_list = itertools.cycle([
            discord.Activity(type=discord.ActivityType.listening, name="!ajuda"),
            discord.Activity(type=discord.ActivityType.playing, name="comandos divertidos"),
            discord.Activity(type=discord.ActivityType.watching, name="os servidores"),
            discord.Activity(type=discord.ActivityType.listening, name="seus problemas"),
            discord.Activity(type=discord.ActivityType.watching, name="você digitando"),
            discord.Activity(type=discord.ActivityType.playing, name="economia virtual"),
            discord.Activity(type=discord.ActivityType.listening, name="!ticket para suporte")
        ])

        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    @tasks.loop(seconds=20)
    async def status_loop(self):
        # Troca para o próximo status da lista a cada 20 segundos
        await self.bot.change_presence(activity=next(self.status_list))

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(StatusCustom(bot))
