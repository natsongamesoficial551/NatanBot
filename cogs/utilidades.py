import discord
from discord.ext import commands
import platform
import datetime

class Utilidades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo", help="Mostra informações sobre um usuário.")
    async def userinfo(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        embed = discord.Embed(title=f"Informações de {membro.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=membro.avatar.url if membro.avatar else membro.default_avatar.url)
        embed.add_field(name="ID", value=membro.id, inline=True)
        embed.add_field(name="Nome", value=membro.name, inline=True)
        embed.add_field(name="Apelido", value=membro.nick or "Nenhum", inline=True)
        embed.add_field(name="Conta criada em", value=membro.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="Entrou no servidor em", value=membro.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="Cargo mais alto", value=membro.top_role.mention, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo", help="Mostra informações sobre o servidor.")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=f"Servidor: {guild.name}", color=discord.Color.green())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Dono", value=guild.owner.mention, inline=True)
        embed.add_field(name="Membros", value=guild.member_count, inline=True)
        embed.add_field(name="Canais de texto", value=len(guild.text_channels), inline=True)
        embed.add_field(name="Canais de voz", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="Criado em", value=guild.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="botinfo", help="Mostra informações sobre o bot.")
    async def botinfo(self, ctx):
        embed = discord.Embed(title="Sobre o Bot", color=discord.Color.purple())
        embed.add_field(name="Desenvolvedor", value="SeuNome#0000")
        embed.add_field(name="Linguagem", value="Python")
        embed.add_field(name="Biblioteca", value=f"discord.py {discord.__version__}")
        embed.add_field(name="Sistema", value=platform.system())
        embed.set_footer(text=f"Ping atual: {round(self.bot.latency * 1000)}ms")
        await ctx.send(embed=embed)

    @commands.command(name="ping", help="Mostra o ping do bot.")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! Meu ping é {latency}ms")

    @commands.command(name="avatar", help="Mostra o avatar de um usuário.")
    async def avatar(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        avatar_url = membro.avatar.url if membro.avatar else membro.default_avatar.url
        embed = discord.Embed(title=f"Avatar de {membro.display_name}", color=discord.Color.random())
        embed.set_image(url=avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="banner", help="Mostra o banner de um usuário.")
    async def banner(self, ctx, membro: discord.Member = None):
        membro = membro or ctx.author
        user = await self.bot.fetch_user(membro.id)
        if user.banner:
            embed = discord.Embed(title=f"Banner de {membro.display_name}", color=discord.Color.random())
            embed.set_image(url=user.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Este usuário não possui banner.")

async def setup(bot):
    await bot.add_cog(Utilidades(bot))
