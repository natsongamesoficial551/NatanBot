import discord
from discord.ext import commands
import json
import os
from datetime import datetime

ARQUIVO_LOGS = "data/logs.json"

def carregar_logs():
    if not os.path.exists(ARQUIVO_LOGS):
        return {}
    with open(ARQUIVO_LOGS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_logs(data):
    with open(ARQUIVO_LOGS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = carregar_logs()

    def salvar(self):
        salvar_logs(self.log_channels)

    def get_log_channel(self, guild):
        channel_id = self.log_channels.get(str(guild.id))
        return guild.get_channel(channel_id) if channel_id else None

    def criar_embed(self, titulo, descricao, cor=discord.Color.blue(), autor=None):
        embed = discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.utcnow())
        if autor:
            embed.set_author(name=str(autor), icon_url=autor.display_avatar.url)
        return embed

    async def log_event(self, guild, embed):
        canal = self.get_log_channel(guild)
        if canal:
            try:
                await canal.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.command(name="setlogcanal")
    @commands.has_permissions(administrator=True)
    async def set_log_canal(self, ctx, canal: discord.TextChannel):
        """Define o canal de logs para o servidor."""
        self.log_channels[str(ctx.guild.id)] = canal.id
        self.salvar()
        await ctx.send(f"✅ Canal de logs definido para {canal.mention}.")

    # === Eventos monitorados ===

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = self.criar_embed("👋 Membro entrou", f"{member.mention} entrou no servidor.", discord.Color.green(), member)
        await self.log_event(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = self.criar_embed("👋 Membro saiu", f"{member.mention} saiu do servidor.", discord.Color.orange(), member)
        await self.log_event(member.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        embed = self.criar_embed("🗑️ Mensagem apagada", f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}\n**Conteúdo:** {message.content}", discord.Color.red(), message.author)
        await self.log_event(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = self.criar_embed("✏️ Mensagem editada", f"**Autor:** {before.author.mention}\n**Canal:** {before.channel.mention}\n**Antes:** {before.content}\n**Depois:** {after.content}", discord.Color.orange(), before.author)
        await self.log_event(before.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = self.criar_embed("📁 Canal criado", f"**Nome:** {channel.name}\n**ID:** {channel.id}", discord.Color.green())
        await self.log_event(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = self.criar_embed("🗑️ Canal deletado", f"**Nome:** {channel.name}", discord.Color.red())
        await self.log_event(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            embed = self.criar_embed("🔁 Canal renomeado", f"**Antes:** {before.name}\n**Depois:** {after.name}")
            await self.log_event(before.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            embed = self.criar_embed("🔄 Nickname alterado", f"**Usuário:** {after.mention}\n**Antes:** {before.nick}\n**Depois:** {after.nick}", discord.Color.yellow(), after)
            await self.log_event(after.guild, embed)
        elif before.roles != after.roles:
            roles_antes = ", ".join([r.name for r in before.roles[1:]]) or "Nenhum"
            roles_depois = ", ".join([r.name for r in after.roles[1:]]) or "Nenhum"
            embed = self.criar_embed("🎭 Cargos alterados", f"**Usuário:** {after.mention}\n**Antes:** {roles_antes}\n**Depois:** {roles_depois}", discord.Color.purple(), after)
            await self.log_event(after.guild, embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.name != after.name:
            embed = self.criar_embed("🆕 Username alterado", f"**Antes:** {before.name}\n**Depois:** {after.name}")
            for guild in self.bot.guilds:
                if guild.get_member(after.id):
                    await self.log_event(guild, embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.name != after.name:
            embed = self.criar_embed("🏷️ Nome do servidor alterado", f"**Antes:** {before.name}\n**Depois:** {after.name}")
            await self.log_event(after, embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))
