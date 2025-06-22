import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta

class AntiPalavrao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "antipalavrao_config.json"
        self.warnings_path = "antipalavrao_warnings.json"

        self.config = self.carregar_config()
        self.user_warnings = self.carregar_warnings()
        self.limpar_warnings_antigos.start()

    def carregar_config(self):
        if not os.path.exists(self.config_path):
            config_inicial = {
                "blocked_words": [],
                "max_warnings": 3,
                "warning_decay_hours": 24
            }
            self.salvar_config(config_inicial)
            return config_inicial
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def salvar_config(self, config=None):
        if config is None:
            config = self.config
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def carregar_warnings(self):
        if not os.path.exists(self.warnings_path):
            return {}
        with open(self.warnings_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def salvar_warnings(self):
        with open(self.warnings_path, "w", encoding="utf-8") as f:
            json.dump(self.user_warnings, f, indent=2, ensure_ascii=False)

    def salvar_tudo(self):
        self.salvar_config()
        self.salvar_warnings()

    def contem_palavrao(self, texto):
        texto = texto.lower()
        return any(palavra in texto for palavra in self.config.get("blocked_words", []))

    @tasks.loop(hours=1)
    async def limpar_warnings_antigos(self):
        agora = datetime.utcnow()
        expiracao = timedelta(hours=self.config.get("warning_decay_hours", 24))
        atualizados = False

        for guild_id in list(self.user_warnings.keys()):
            for user_id in list(self.user_warnings[guild_id].keys()):
                try:
                    timestamp = datetime.fromisoformat(self.user_warnings[guild_id][user_id]["timestamp"])
                    if agora - timestamp > expiracao:
                        del self.user_warnings[guild_id][user_id]
                        atualizados = True
                except Exception:
                    continue

        if atualizados:
            self.salvar_warnings()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.administrator:
            return

        if self.contem_palavrao(message.content):
            await message.delete()
            guild_id = str(message.guild.id)
            user_id = str(message.author.id)

            if guild_id not in self.user_warnings:
                self.user_warnings[guild_id] = {}

            warnings_data = self.user_warnings[guild_id].get(user_id, {"count": 0, "timestamp": datetime.utcnow().isoformat()})
            warnings_data["count"] += 1
            warnings_data["timestamp"] = datetime.utcnow().isoformat()
            self.user_warnings[guild_id][user_id] = warnings_data
            self.salvar_warnings()

            embed = discord.Embed(
                title="🚫 Linguagem Inadequada",
                description=f"{message.author.mention}, evite usar palavras ofensivas!",
                color=discord.Color.red()
            )
            embed.add_field(name="Avisos", value=str(warnings_data["count"]))
            await message.channel.send(embed=embed, delete_after=10)

            if warnings_data["count"] >= self.config.get("max_warnings", 3):
                timeout_duration = timedelta(minutes=10)
                try:
                    await message.author.timeout(timeout_duration, reason="Excesso de palavrões")
                    await message.channel.send(f"🔇 {message.author.mention} foi silenciado por 10 minutos por excesso de avisos.")
                except Exception:
                    pass

    @commands.command(name="modconfig")
    @commands.has_permissions(administrator=True)
    async def modconfig(self, ctx, acao: str, *, parametro=None):
        guild_id = str(ctx.guild.id)
        if acao == "add" and parametro:
            self.config["blocked_words"].append(parametro.lower())
            self.salvar_config()
            await ctx.send(f"✅ Palavra `{parametro}` adicionada à lista de bloqueio.")
        elif acao == "remove" and parametro:
            if parametro.lower() in self.config["blocked_words"]:
                self.config["blocked_words"].remove(parametro.lower())
                self.salvar_config()
                await ctx.send(f"✅ Palavra `{parametro}` removida da lista de bloqueio.")
            else:
                await ctx.send("❌ Palavra não encontrada na lista.")
        elif acao == "list":
            palavras = ", ".join(self.config.get("blocked_words", [])) or "Nenhuma"
            await ctx.author.send(f"🔒 Palavras bloqueadas: {palavras}")
        elif acao == "warnings" and parametro:
            membro = ctx.message.mentions[0] if ctx.message.mentions else None
            if not membro:
                await ctx.send("❌ Mencione um usuário.")
                return
            avisos = self.user_warnings.get(str(ctx.guild.id), {}).get(str(membro.id), {}).get("count", 0)
            await ctx.send(f"⚠️ {membro.mention} tem {avisos} aviso(s).")
        elif acao == "reset" and parametro:
            membro = ctx.message.mentions[0] if ctx.message.mentions else None
            if not membro:
                await ctx.send("❌ Mencione um usuário.")
                return
            self.user_warnings.get(str(ctx.guild.id), {}).pop(str(membro.id), None)
            self.salvar_warnings()
            await ctx.send(f"♻️ Avisos de {membro.mention} foram resetados.")
        else:
            await ctx.send("❌ Uso inválido. Exemplo: `!modconfig add palavrão` ou `!modconfig list`")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Sistema de Anti-Palavrões carregado! Arquivos: {self.config_path}, {self.warnings_path}")

async def setup(bot):
    await bot.add_cog(AntiPalavrao(bot))
