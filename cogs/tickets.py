import discord
from discord.ext import commands
import json
import os
import asyncio  # necessário para o sleep

CAMINHO_TICKETS = "data/tickets.json"

def carregar_config():
    if not os.path.exists(CAMINHO_TICKETS):
        return {}
    with open(CAMINHO_TICKETS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(config):
    with open(CAMINHO_TICKETS, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = carregar_config()

    def salvar(self):
        salvar_config(self.config)

    @commands.command(name="ticket")
    async def abrir_ticket(self, ctx):
        """Abre um ticket em um canal privado para suporte."""
        guild_id = str(ctx.guild.id)
        author = ctx.author

        guild_config = self.config.get(guild_id, {})
        canal_autorizado = guild_config.get("canal_comando")
        categoria_id = guild_config.get("categoria_id")

        # Verifica se o comando está no canal autorizado
        if canal_autorizado and ctx.channel.id != canal_autorizado:
            await ctx.send(f"{author.mention}, você só pode usar esse comando no canal correto.")
            return

        # Verifica se o usuário já tem um ticket aberto
        for canal in ctx.guild.text_channels:
            if canal.name == f"ticket-{author.id}":
                await ctx.send(f"{author.mention}, você já tem um ticket aberto: {canal.mention}")
                return

        # Busca a categoria para criar o canal
        categoria = ctx.guild.get_channel(categoria_id) if categoria_id else None

        # Permissões para o canal
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        canal = await ctx.guild.create_text_channel(
            name=f"ticket-{author.id}",
            category=categoria,
            overwrites=overwrites,
            reason="Abertura de ticket"
        )

        await canal.send(f"{author.mention}, este é seu canal de suporte. Um administrador responderá em breve.")
        await ctx.send(f"{author.mention}, seu ticket foi criado: {canal.mention}")

    @commands.command(name="fecharticket")
    @commands.has_permissions(administrator=True)
    async def fechar_ticket(self, ctx):
        """Fecha o ticket atual (só administradores podem)."""
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("Este comando só pode ser usado dentro de um canal de ticket.")
            return

        await ctx.send("Fechando o ticket em 3 segundos...")
        await asyncio.sleep(3)
        await ctx.channel.delete()

    @commands.command(name="setticketcategoria")
    @commands.has_permissions(administrator=True)
    async def set_categoria(self, ctx, categoria: discord.CategoryChannel):
        """Define a categoria onde os tickets serão criados."""
        guild_id = str(ctx.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {}

        self.config[guild_id]["categoria_id"] = categoria.id
        self.salvar()

        await ctx.send(f"Categoria de tickets definida para **{categoria.name}**.")

    @commands.command(name="setticketcomando")
    @commands.has_permissions(administrator=True)
    async def set_comando_ticket(self, ctx, canal: discord.TextChannel):
        """Define o canal onde o comando !ticket pode ser usado."""
        guild_id = str(ctx.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {}

        self.config[guild_id]["canal_comando"] = canal.id
        self.salvar()

        await ctx.send(f"O comando `!ticket` agora só pode ser usado em {canal.mention}.")

    @commands.command(name="mostrarticketconfig")
    async def mostrar_config(self, ctx):
        """Mostra a configuração atual dos tickets."""
        guild_id = str(ctx.guild.id)
        conf = self.config.get(guild_id)

        if not conf:
            await ctx.send("Nenhuma configuração de ticket encontrada.")
            return

        canal = ctx.guild.get_channel(conf.get("canal_comando")) if conf.get("canal_comando") else None
        categoria = ctx.guild.get_channel(conf.get("categoria_id")) if conf.get("categoria_id") else None

        msg = f"**Canal para comando !ticket:** {canal.mention if canal else 'Não definido'}\n"
        msg += f"**Categoria dos tickets:** {categoria.name if categoria else 'Não definida'}"

        await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
