import discord
from discord.ext import commands

class Ajuda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ajuda", help="Mostra todos os comandos organizados por categoria")
    async def ajuda(self, ctx):
        embed = discord.Embed(
            title="📖 Comandos do NatanBot",
            description="Veja abaixo os comandos disponíveis organizados por categoria:",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎮 Economia e Diversão",
            value=(
                "`!saldo`, `!bal`, `!balance`, `!diario`, `!daily`, `!trabalhar`, `!work`, `!crime`, `!roubar @usuário`,\n"
                "`!depositar <valor>`, `!sacar <valor>`, `!transferir @usuário <valor>`,\n"
                "`!apostar <valor>`, `!bet <valor>`, `!loteria`, `!presentear @usuário <emoji> [qtd]`"
            ),
            inline=False
        )

        embed.add_field(
            name="🛒 Loja e Itens",
            value=(
                "`!loja`, `!shop`, `!comprar <emoji>`, `!buy <emoji>`,\n"
                "`!vender <emoji> [quantidade]`, `!sell <emoji> [quantidade]`,\n"
                "`!inventario`, `!inv`, `!inventory`, `!abrir_bau`, `!missoes`, `!empregos`, `!emprego`"
            ),
            inline=False
        )

        embed.add_field(
            name="👑 Sistema VIP",
            value=(
                "`!setvip @usuário <dias>`, `!removervip @usuário`, `!listvip`, `!vipstatus [@usuário]`\n"
                "**Benefícios VIP:** `+50$` no `!daily`, `+50%` no `!work`, `+10%` chance extra em `!apostar`, XP boost"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ Administração de Economia",
            value=(
                "`!additem <emoji> <preço> <nome> - <descrição>`\n"
                "`!removeitem <emoji>`, `!dar @usuário <valor>`, `!give @usuário <valor>`"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Moderação",
            value=(
                "`!avisar @usuário [motivo]`, `!avisos [@usuário]`, `!limparavisos @usuário`\n"
                "`!mute @usuário [tempo] [motivo]`, `!unmute @usuário`\n"
                "`!kick @usuário [motivo]`, `!ban @usuário [motivo]`, `!unban <user_id>`\n"
                "`!clear [quantidade]`, `!historico [@usuário] [limite]`, `!configmod`,\n"
                "`!configmod canal_logs #canal`, `!configmod max_avisos 3`, `!configmod auto_punir true/false`"
            ),
            inline=False
        )

        embed.add_field(
            name="🔧 Sistema de Boas-Vindas",
            value=(
                "**Comandos de Configuração:**\n"
                "`!setar-admin #canal`, `!setar-boas-vindas #canal`\n\n"
                "**Comandos de Ativação:**\n"
                "`!ativar-entrada`, `!ativar-saida`, `!desativar-entrada`, `!desativar-saida`\n\n"
                "**Personalização:**\n"
                "`!msg-entrada [mensagem]`, `!msg-saida [mensagem]`\n"
                "Use `{user}` na mensagem para mencionar o usuário.\n\n"
                "**Informações:**\n"
                "`!config-bv`, `!help-bv`"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Mensagens Personalizadas",
            value=(
                "`!setmensagem #canal <intervalo_horas> <mensagem>`\n"
                "`!removemensagem <id>`, `!vermensagens`"
            ),
            inline=False
        )

        embed.add_field(
            name="🧠 Sistema Anti-Palavrão",
            value=(
                "`!modconfig add <palavra>`, `!modconfig remove <palavra>`, `!modconfig list`\n"
                "`!modconfig warnings @usuário`, `!modconfig reset @usuário`"
            ),
            inline=False
        )

        embed.add_field(
            name="🎉 XP e Nível",
            value=(
                "`!xp`, `!topxp`\n"
                "`!setmensagensporxp <valor>`, `!setxpbase <valor>`, `!setxppornivel <valor>`\n"
                "`!setxpcooldown <segundos>`, `!verxpconfig`, `!setvipxp <valor>`, `!setvipcooldown <valor>`"
            ),
            inline=False
        )

        embed.add_field(
            name="🎁 Sorteios e Eventos",
            value=(
                "`!sorteio <prêmio>`, `!vencedor`, `!encerrarsorteio`, `!mostrarsorteio`\n"
                "`!setsorteiocanal #canal`, `!setcomandocanal #canal`"
            ),
            inline=False
        )

        embed.add_field(
            name="📚 Utilidades",
            value="`!userinfo`, `!serverinfo`, `!botinfo`, `!ping`, `!avatar`, `!banner`, `!rankcoins`",
            inline=False
        )

        embed.add_field(
            name="🎂 Aniversários",
            value="`!setaniversario`, `!veraniversarios`, `!rankaniversarios`",
            inline=False
        )

        embed.add_field(
            name="📌 Logs e Status",
            value="`!setlogcanal #canal`, alternância automática de status",
            inline=False
        )

        embed.add_field(
            name="🎟️ Sistema de Tickets",
            value=(
                "`!ticket`, `!fecharticket`, `!setticketcategoria <categoria>`\n"
                "`!setticketcomando #canal`, `!mostrarticketconfig`"
            ),
            inline=False
        )

        embed.set_footer(
            text=f"Pedido por {ctx.author}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Ajuda(bot))
