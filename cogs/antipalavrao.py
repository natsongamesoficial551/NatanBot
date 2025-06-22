import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta

# Agora salvando os arquivos dentro da pasta data/
CONFIG_PATH = "data/moderation_config.json"
WARNINGS_PATH = "data/warnings.json"

# === Utilitários ===
def carregar_config():
    if not os.path.exists(CONFIG_PATH):
        return {"blocked_words": [], "max_warnings": 3, "warning_decay_hours": 24}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(config):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def carregar_warnings():
    if not os.path.exists(WARNINGS_PATH):
        return {}
    with open(WARNINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_warnings(warnings):
    os.makedirs("data", exist_ok=True)
    with open(WARNINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(warnings, f, indent=4, ensure_ascii=False)

class AntiPalavrao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = carregar_config()
        self.user_warnings = carregar_warnings()
        self.limpar_warnings_antigos.start()

    def salvar(self):
        salvar_config(self.config)
        salvar_warnings(self.user_warnings)

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
                timestamp = datetime.fromisoformat(self.user_warnings[guild_id][user_id]["timestamp"])
                if agora - timestamp > expiracao:
                    del self.user_warnings[guild_id][user_id]
                    atualizados = True

        if atualizados:
            self.salvar()

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
            self.salvar()

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
                except:
                    pass

    @commands.command(name="modconfig")
    @commands.has_permissions(administrator=True)
    async def modconfig(self, ctx, acao: str, *, parametro=None):
        guild_id = str(ctx.guild.id)
        if acao == "add" and parametro:
            self.config["blocked_words"].append(parametro.lower())
            self.salvar()
            await ctx.send(f"✅ Palavra `{parametro}` adicionada à lista de bloqueio.")
        elif acao == "remove" and parametro:
            if parametro.lower() in self.config["blocked_words"]:
                self.config["blocked_words"].remove(parametro.lower())
                self.salvar()
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
            self.salvar()
            await ctx.send(f"♻️ Avisos de {membro.mention} foram resetados.")
        else:
            await ctx.send("❌ Uso inválido. Exemplo: `!modconfig add palavrão` ou `!modconfig list`")

async def setup(bot):
    await bot.add_cog(AntiPalavrao(bot))
