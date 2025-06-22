import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta

CAMINHO_XP = "data/xp.json"

def carregar_dados():
    if not os.path.exists(CAMINHO_XP):
        return {}
    with open(CAMINHO_XP, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(CAMINHO_XP, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

class SistemaXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = carregar_dados()
        self.cooldowns = {}  # user_id: datetime

    def salvar(self):
        salvar_dados(self.dados)

    def get_config(self):
        if "config" not in self.dados:
            self.dados["config"] = {
                "mensagens_por_xp": 10,
                "xp_base": 10,
                "xp_por_nivel": 10,
                "cooldown": 60,
                # Configurações VIP
                "vip_multiplicador_xp": 2.0,
                "vip_reducao_cooldown": 0.5,  # 50% de redução
                "vip_bonus_nivel": 1.5,  # Bônus no cálculo de XP necessário
                "vip_mensagens_bonus": 5  # A cada 5 mensagens ganha XP extra
            }
        return self.dados["config"]

    def get_usuario(self, guild_id, user_id):
        gid = str(guild_id)
        uid = str(user_id)
        if gid not in self.dados:
            self.dados[gid] = {}
        if uid not in self.dados[gid]:
            self.dados[gid][uid] = {
                "xp": 0,
                "nivel": 1,
                "mensagens": 0,
                "vip": False,
                "vip_expira": None  # Timestamp para quando o VIP expira
            }
        return self.dados[gid][uid]

    def is_vip_ativo(self, usuario):
        """Verifica se o usuário tem VIP ativo"""
        if not usuario.get("vip", False):
            return False
        
        # Se não tem data de expiração, é VIP permanente
        if not usuario.get("vip_expira"):
            return True
            
        # Verifica se ainda não expirou
        expira = datetime.fromisoformat(usuario["vip_expira"])
        return datetime.utcnow() < expira

    def get_multiplicador_xp(self, usuario):
        """Retorna o multiplicador de XP baseado no status VIP"""
        if self.is_vip_ativo(usuario):
            return self.get_config()["vip_multiplicador_xp"]
        return 1.0

    def get_cooldown_usuario(self, usuario):
        """Retorna o cooldown baseado no status VIP"""
        config = self.get_config()
        cooldown_base = config["cooldown"]
        
        if self.is_vip_ativo(usuario):
            return int(cooldown_base * config["vip_reducao_cooldown"])
        return cooldown_base

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        now = datetime.utcnow()
        usuario = self.get_usuario(message.guild.id, user_id)

        # Cooldown personalizado baseado no status VIP
        cooldown = self.get_cooldown_usuario(usuario)
        last = self.cooldowns.get(user_id)
        if last and now - last < timedelta(seconds=cooldown):
            return

        self.cooldowns[user_id] = now
        usuario["mensagens"] += 1

        config = self.get_config()
        xp_ganho = 0
        is_vip = self.is_vip_ativo(usuario)

        # Ganho de XP normal
        if usuario["mensagens"] % config["mensagens_por_xp"] == 0:
            xp_base = config["xp_base"]
            multiplicador = self.get_multiplicador_xp(usuario)
            xp_ganho = int(xp_base * multiplicador)
            usuario["xp"] += xp_ganho

        # Bônus VIP: XP extra a cada X mensagens
        if is_vip and usuario["mensagens"] % config["vip_mensagens_bonus"] == 0:
            bonus_xp = int(config["xp_base"] * 0.5)  # 50% do XP base como bônus
            usuario["xp"] += bonus_xp
            xp_ganho += bonus_xp

        # Verificar level up
        if xp_ganho > 0:
            xp_necessario = config["xp_por_nivel"] * usuario["nivel"]
            
            # Bônus VIP: XP necessário ligeiramente reduzido
            if is_vip:
                xp_necessario = int(xp_necessario / config["vip_bonus_nivel"])

            if usuario["xp"] >= xp_necessario:
                usuario["xp"] -= xp_necessario
                usuario["nivel"] += 1

                # Embed de level up diferenciado para VIP
                if is_vip:
                    embed = discord.Embed(
                        title="✨ VIP Level Up! ✨",
                        description=f"{message.author.mention} subiu para o **nível {usuario['nivel']}**!\n💎 *Benefício VIP ativo*",
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="⭐ Status VIP ativo")
                else:
                    embed = discord.Embed(
                        title="📈 Level Up!",
                        description=f"{message.author.mention} subiu para o **nível {usuario['nivel']}**!",
                        color=discord.Color.green()
                    )
                
                embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
                await message.channel.send(embed=embed)

        self.salvar()

    @commands.command(name="xp")
    async def ver_xp(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        usuario = self.get_usuario(ctx.guild.id, membro.id)
        nivel = usuario["nivel"]
        xp = usuario["xp"]
        mensagens = usuario["mensagens"]
        is_vip = self.is_vip_ativo(usuario)
        
        config = self.get_config()
        xp_max = config["xp_por_nivel"] * nivel
        
        # Ajustar XP necessário se for VIP
        if is_vip:
            xp_max = int(xp_max / config["vip_bonus_nivel"])

        porcentagem = int((xp / xp_max) * 10) if xp_max > 0 else 0
        barra = "█" * porcentagem + "░" * (10 - porcentagem)

        # Cor e título diferentes para VIP
        if is_vip:
            embed = discord.Embed(title=f"✨ Perfil VIP de {membro.display_name}", color=discord.Color.gold())
            embed.set_footer(text="⭐ Status VIP ativo")
        else:
            embed = discord.Embed(title=f"📊 Perfil de {membro.display_name}", color=discord.Color.blurple())

        embed.add_field(name="Nível", value=nivel, inline=True)
        embed.add_field(name="XP", value=f"{xp}/{xp_max}", inline=True)
        embed.add_field(name="Mensagens", value=mensagens, inline=True)
        embed.add_field(name="Progresso", value=f"[{barra}] {int((xp / xp_max) * 100) if xp_max > 0 else 0}%", inline=False)
        
        if is_vip:
            multiplicador = config["vip_multiplicador_xp"]
            cooldown_reduzido = int(config["cooldown"] * config["vip_reducao_cooldown"])
            embed.add_field(
                name="💎 Benefícios VIP",
                value=f"• {multiplicador}x XP\n• Cooldown: {cooldown_reduzido}s\n• Bônus a cada {config['vip_mensagens_bonus']} msgs",
                inline=False
            )
            
            # Mostrar data de expiração se tiver
            if usuario.get("vip_expira"):
                expira = datetime.fromisoformat(usuario["vip_expira"])
                embed.add_field(
                    name="⏰ VIP expira em",
                    value=f"<t:{int(expira.timestamp())}:R>",
                    inline=False
                )

        embed.set_thumbnail(url=membro.avatar.url if membro.avatar else None)
        await ctx.send(embed=embed)

    @commands.command(name="topxp")
    async def top_xp(self, ctx):
        gid = str(ctx.guild.id)
        if gid not in self.dados:
            return await ctx.send("Nenhum dado de XP encontrado.")

        usuarios = []
        for uid, info in self.dados[gid].items():
            try:
                user_id = int(uid)
                is_vip = self.is_vip_ativo(info)
                usuarios.append((user_id, info["nivel"], info["xp"], is_vip))
            except ValueError:
                continue
                
        top = sorted(usuarios, key=lambda x: (x[1], x[2]), reverse=True)[:10]

        embed = discord.Embed(title="🏆 Top XP do Servidor", color=discord.Color.gold())
        
        for i, (uid, nivel, xp, is_vip) in enumerate(top, start=1):
            membro = ctx.guild.get_member(uid)
            nome = membro.display_name if membro else f"<Usuário {uid}>"
            
            # Adicionar indicador VIP
            vip_indicator = " ✨" if is_vip else ""
            emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            
            embed.add_field(
                name=f"{emoji} {i}º - {nome}{vip_indicator}",
                value=f"Nível {nivel} | {xp} XP",
                inline=False
            )

        await ctx.send(embed=embed)

    # Comandos de administração VIP
    @commands.command(name="addvip")
    @commands.has_permissions(administrator=True)
    async def add_vip(self, ctx, membro: discord.Member, dias: int = None):
        """Adiciona VIP a um usuário. Se não especificar dias, será permanente."""
        usuario = self.get_usuario(ctx.guild.id, membro.id)
        usuario["vip"] = True
        
        if dias:
            expira = datetime.utcnow() + timedelta(days=dias)
            usuario["vip_expira"] = expira.isoformat()
            await ctx.send(f"✨ VIP adicionado para {membro.mention} por {dias} dias!")
        else:
            usuario["vip_expira"] = None
            await ctx.send(f"✨ VIP permanente adicionado para {membro.mention}!")
        
        self.salvar()

    @commands.command(name="removevip")
    @commands.has_permissions(administrator=True)
    async def remove_vip(self, ctx, membro: discord.Member):
        """Remove VIP de um usuário."""
        usuario = self.get_usuario(ctx.guild.id, membro.id)
        usuario["vip"] = False
        usuario["vip_expira"] = None
        await ctx.send(f"❌ VIP removido de {membro.mention}.")
        self.salvar()

    @commands.command(name="listvips")
    @commands.has_permissions(administrator=True)
    async def list_vips(self, ctx):
        """Lista todos os usuários VIP do servidor."""
        gid = str(ctx.guild.id)
        if gid not in self.dados:
            return await ctx.send("Nenhum dado encontrado.")

        vips = []
        for uid, info in self.dados[gid].items():
            if self.is_vip_ativo(info):
                try:
                    user_id = int(uid)
                    membro = ctx.guild.get_member(user_id)
                    nome = membro.display_name if membro else f"<Usuário {uid}>"
                    
                    if info.get("vip_expira"):
                        expira = datetime.fromisoformat(info["vip_expira"])
                        vips.append(f"• {nome} - Expira <t:{int(expira.timestamp())}:R>")
                    else:
                        vips.append(f"• {nome} - Permanente")
                except ValueError:
                    continue

        if not vips:
            return await ctx.send("Nenhum usuário VIP ativo.")

        embed = discord.Embed(title="✨ Usuários VIP", color=discord.Color.gold())
        embed.description = "\n".join(vips)
        await ctx.send(embed=embed)

    # Comandos de configuração existentes + novos para VIP
    @commands.command(name="verxpconfig")
    @commands.has_permissions(administrator=True)
    async def ver_config(self, ctx):
        config = self.get_config()
        embed = discord.Embed(title="⚙️ Configurações de XP", color=discord.Color.blue())
        embed.add_field(name="Mensagens por XP", value=config["mensagens_por_xp"], inline=True)
        embed.add_field(name="XP Base", value=config["xp_base"], inline=True)
        embed.add_field(name="Multiplicador por Nível", value=config["xp_por_nivel"], inline=True)
        embed.add_field(name="Cooldown (segundos)", value=config["cooldown"], inline=True)
        
        # Configurações VIP
        embed.add_field(name="✨ VIP Multiplicador XP", value=f"{config['vip_multiplicador_xp']}x", inline=True)
        embed.add_field(name="✨ VIP Redução Cooldown", value=f"{int(config['vip_reducao_cooldown']*100)}%", inline=True)
        embed.add_field(name="✨ VIP Bonus Nível", value=f"{config['vip_bonus_nivel']}x", inline=True)
        embed.add_field(name="✨ VIP Mensagens Bonus", value=config["vip_mensagens_bonus"], inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="setvipxp")
    @commands.has_permissions(administrator=True)
    async def set_vip_multiplicador(self, ctx, valor: float):
        """Define o multiplicador de XP para usuários VIP."""
        self.get_config()["vip_multiplicador_xp"] = valor
        self.salvar()
        await ctx.send(f"✨ Multiplicador VIP de XP definido como {valor}x.")

    @commands.command(name="setvipcooldown")
    @commands.has_permissions(administrator=True)
    async def set_vip_cooldown(self, ctx, porcentagem: float):
        """Define a redução de cooldown para VIPs (0.5 = 50% de redução)."""
        self.get_config()["vip_reducao_cooldown"] = porcentagem
        self.salvar()
        await ctx.send(f"⏱️ Redução de cooldown VIP definida como {int(porcentagem*100)}%.")

    # Comandos de configuração existentes
    @commands.command(name="setmensagensporxp")
    @commands.has_permissions(administrator=True)
    async def set_mensagens_por_xp(self, ctx, valor: int):
        self.get_config()["mensagens_por_xp"] = valor
        self.salvar()
        await ctx.send(f"✅ Mensagens por XP definido como {valor}.")

    @commands.command(name="setxpbase")
    @commands.has_permissions(administrator=True)
    async def set_xp_base(self, ctx, valor: int):
        self.get_config()["xp_base"] = valor
        self.salvar()
        await ctx.send(f"✅ XP base definido como {valor}.")

    @commands.command(name="setxppornivel")
    @commands.has_permissions(administrator=True)
    async def set_xp_por_nivel(self, ctx, valor: int):
        self.get_config()["xp_por_nivel"] = valor
        self.salvar()
        await ctx.send(f"✅ Multiplicador de XP por nível definido como {valor}.")

    @commands.command(name="setxpcooldown")
    @commands.has_permissions(administrator=True)
    async def set_cooldown(self, ctx, segundos: int):
        self.get_config()["cooldown"] = segundos
        self.salvar()
        await ctx.send(f"⏱️ Cooldown ajustado para {segundos} segundos.")

async def setup(bot):
    await bot.add_cog(SistemaXP(bot))