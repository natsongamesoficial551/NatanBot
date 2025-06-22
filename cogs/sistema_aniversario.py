import discord
from discord.ext import commands
import json
import os
from datetime import datetime

ARQUIVO = 'aniversarios.json'

class Aniversarios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = self.carregar_dados()

    def carregar_dados(self):
        if os.path.exists(ARQUIVO):
            with open(ARQUIVO, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def salvar_dados(self):
        with open(ARQUIVO, 'w', encoding='utf-8') as f:
            json.dump(self.dados, f, indent=4, ensure_ascii=False)

    @commands.command(name="setaniversario")
    async def setar_aniversario(self, ctx, data: str):
        """Define seu aniversário no formato DD/MM"""
        try:
            datetime.strptime(data, "%d/%m")
        except ValueError:
            await ctx.send("❌ Formato inválido. Use `!setaniversario dd/mm`.")
            return

        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        if guild_id not in self.dados:
            self.dados[guild_id] = {}

        self.dados[guild_id][user_id] = {
            "nome": ctx.author.name,
            "data": data
        }
        self.salvar_dados()
        await ctx.send(f"🎉 Aniversário registrado como `{data}` para {ctx.author.mention}!")

    @commands.command(name="veraniversarios")
    async def ver_aniversarios(self, ctx):
        """Mostra todos os aniversários cadastrados no servidor"""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.dados or not self.dados[guild_id]:
            await ctx.send("📭 Nenhum aniversário cadastrado.")
            return

        aniversarios = self.dados[guild_id].values()
        ordenado = sorted(aniversarios, key=lambda x: datetime.strptime(x['data'], "%d/%m"))

        embed = discord.Embed(title="🎂 Aniversários Cadastrados", color=discord.Color.purple())
        for item in ordenado:
            embed.add_field(name=item["nome"], value=item["data"], inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="rankaniversarios")
    async def rank_aniversarios(self, ctx):
        """Mostra os aniversariantes do mês atual"""
        mes_atual = datetime.utcnow().strftime("%m")
        guild_id = str(ctx.guild.id)

        if guild_id not in self.dados or not self.dados[guild_id]:
            await ctx.send("📭 Nenhum aniversário cadastrado.")
            return

        aniversariantes = [
            (v["nome"], v["data"]) for v in self.dados[guild_id].values()
            if v["data"].split("/")[1] == mes_atual
        ]

        if not aniversariantes:
            await ctx.send("📭 Nenhum aniversário neste mês.")
            return

        aniversariantes.sort(key=lambda x: int(x[1].split("/")[0]))

        embed = discord.Embed(
            title=f"🎉 Aniversariantes de {datetime.utcnow().strftime('%B')}",
            color=discord.Color.gold()
        )
        for nome, data in aniversariantes:
            embed.add_field(name=nome, value=data, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Aniversarios(bot))
