import discord
from discord.ext import commands
import json
import os

CAMINHO_ARQUIVO = "data/logs.json"

def carregar_logs():
    if not os.path.exists(CAMINHO_ARQUIVO):
        return {}
    with open(CAMINHO_ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_logs(logs):
    os.makedirs("data", exist_ok=True)
    with open(CAMINHO_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)

class PainelLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs = carregar_logs()

    def salvar(self):
        salvar_logs(self.logs)

    @commands.command(name="setlogcanal")
    @commands.has_permissions(manage_guild=True)
    async def set_log_canal(self, ctx, canal: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.logs:
            self.logs[guild_id] = {}

        self.logs[guild_id]["log_channel"] = canal.id
        self.salvar()

        await ctx.send(f"✅ Canal de logs configurado para {canal.mention}.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        if guild_id not in self.logs:
            return

        canal_id = self.logs[guild_id].get("log_channel")
        if not canal_id:
            return

        canal = message.guild.get_channel(canal_id)
        if not canal:
            return

        embed = discord.Embed(
            title="🗑️ Mensagem Deletada",
            description=f"Mensagem de {message.author.mention} foi deletada.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Canal", value=message.channel.mention, inline=False)
        embed.add_field(name="Conteúdo", value=message.content or "(sem conteúdo)", inline=False)
        embed.set_footer(text="NatanBot • Logs")
        await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild:
            return

        if before.content == after.content:
            return

        guild_id = str(before.guild.id)
        if guild_id not in self.logs:
            return

        canal_id = self.logs[guild_id].get("log_channel")
        if not canal_id:
            return

        canal = before.guild.get_channel(canal_id)
        if not canal:
            return

        embed = discord.Embed(
            title="✏️ Mensagem Editada",
            description=f"Mensagem de {before.author.mention} foi editada.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Canal", value=before.channel.mention, inline=False)
        embed.add_field(name="Antes", value=before.content or "(sem conteúdo)", inline=False)
        embed.add_field(name="Depois", value=after.content or "(sem conteúdo)", inline=False)
        embed.set_footer(text="NatanBot • Logs")
        await canal.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PainelLogs(bot))
