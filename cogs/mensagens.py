import discord
from discord.ext import commands, tasks
import json
import os
import asyncio

ARQUIVO = "data/mensagens.json"

class Mensagens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mensagens = self.carregar_mensagens()
        self.envio_automatico.start()

    def carregar_mensagens(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(ARQUIVO):
            with open(ARQUIVO, "w", encoding="utf-8") as f:
                json.dump([], f)
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def salvar_mensagens(self):
        with open(ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(self.mensagens, f, indent=2, ensure_ascii=False)

    @commands.command(name="setmensagem")
    @commands.has_permissions(administrator=True)
    async def set_mensagem(self, ctx, canal: discord.TextChannel, tempo: int, *, mensagem: str):
        """Adiciona uma nova mensagem automática"""
        nova = {
            "canal_id": canal.id,
            "mensagem": mensagem,
            "intervalo": tempo,
            "proximo_envio": discord.utils.utcnow().timestamp() + tempo
        }
        self.mensagens.append(nova)
        self.salvar_mensagens()
        await ctx.send(f"✅ Mensagem adicionada ao canal {canal.mention} com intervalo de {tempo} segundos.")

    @commands.command(name="removemensagem")
    @commands.has_permissions(administrator=True)
    async def remover_mensagem(self, ctx, indice: int):
        """Remove uma mensagem automática"""
        if 0 < indice <= len(self.mensagens):
            removida = self.mensagens.pop(indice - 1)
            self.salvar_mensagens()
            await ctx.send(f"🗑️ Mensagem removida do canal <#{removida['canal_id']}>:\n```{removida['mensagem']}```")
        else:
            await ctx.send("❌ Índice inválido.")

    @commands.command(name="vermensagens")
    @commands.has_permissions(administrator=True)
    async def ver_mensagens(self, ctx):
        """Mostra todas as mensagens programadas"""
        if not self.mensagens:
            return await ctx.send("📭 Nenhuma mensagem configurada.")
        
        embed = discord.Embed(title="📨 Mensagens Automáticas", color=discord.Color.blue())
        for i, msg in enumerate(self.mensagens, 1):
            canal = self.bot.get_channel(msg["canal_id"])
            embed.add_field(
                name=f"#{i} - Canal: {canal.mention if canal else 'Canal não encontrado'}",
                value=(
                    f"⏱️ Intervalo: {msg['intervalo']}s\n"
                    f"💬 Mensagem: {msg['mensagem']}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    @tasks.loop(seconds=60)
    async def envio_automatico(self):
        agora = discord.utils.utcnow().timestamp()
        for msg in self.mensagens:
            if agora >= msg.get("proximo_envio", 0):
                canal = self.bot.get_channel(msg["canal_id"])
                if canal:
                    try:
                        await canal.send(msg["mensagem"])
                    except Exception as e:
                        print(f"Erro ao enviar mensagem automática: {e}")
                msg["proximo_envio"] = agora + msg["intervalo"]
        self.salvar_mensagens()

    @envio_automatico.before_loop
    async def before_envio_automatico(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Mensagens(bot))
