import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime, timedelta

class Moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.arquivo_moderacao = 'moderacao.json'
        self.dados_moderacao = self.carregar_dados()

    def carregar_dados(self):
        """Carrega dados do arquivo JSON ou cria um novo se não existir"""
        if os.path.exists(self.arquivo_moderacao):
            try:
                with open(self.arquivo_moderacao, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Erro ao carregar {self.arquivo_moderacao}. Criando novo arquivo...")
                return self.criar_arquivo_inicial()
        else:
            print(f"Arquivo {self.arquivo_moderacao} não encontrado. Criando novo...")
            return self.criar_arquivo_inicial()

    def criar_arquivo_inicial(self):
        """Cria a estrutura inicial do arquivo JSON"""
        dados_iniciais = {
            "avisos": {},
            "mutes": {},
            "bans_temporarios": {},
            "configuracoes": {
                "canal_logs": None,
                "cargo_mute": None,
                "max_avisos": 3,
                "auto_punir": True
            },
            "historico": []
        }
        self.salvar_dados(dados_iniciais)
        print(f"✅ Arquivo {self.arquivo_moderacao} criado com sucesso!")
        return dados_iniciais

    def salvar_dados(self, dados=None):
        """Salva os dados no arquivo JSON"""
        if dados is None:
            dados = self.dados_moderacao
        
        try:
            with open(self.arquivo_moderacao, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")

    def adicionar_historico(self, acao, moderador, usuario, motivo=None, duracao=None):
        """Adiciona uma ação ao histórico"""
        entrada = {
            "acao": acao,
            "moderador": str(moderador),
            "usuario": str(usuario),
            "motivo": motivo,
            "duracao": duracao,
            "timestamp": datetime.now().isoformat()
        }
        self.dados_moderacao["historico"].append(entrada)
        self.salvar_dados()

    async def enviar_log(self, embed):
        """Envia log para o canal configurado"""
        canal_id = self.dados_moderacao["configuracoes"]["canal_logs"]
        if canal_id:
            canal = self.bot.get_channel(canal_id)
            if canal:
                try:
                    await canal.send(embed=embed)
                except discord.Forbidden:
                    print("Sem permissão para enviar no canal de logs")

    def criar_cargo_mute(self, guild):
        """Cria o cargo de mute se não existir"""
        return asyncio.create_task(self._criar_cargo_mute_async(guild))

    async def _criar_cargo_mute_async(self, guild):
        """Função assíncrona para criar cargo de mute"""
        cargo_mute = discord.utils.get(guild.roles, name="Mutado")
        if not cargo_mute:
            try:
                cargo_mute = await guild.create_role(
                    name="Mutado",
                    color=discord.Color.dark_gray(),
                    reason="Cargo criado automaticamente para sistema de mute"
                )
                
                # Aplicar permissões em todos os canais
                for canal in guild.channels:
                    try:
                        if isinstance(canal, discord.TextChannel):
                            await canal.set_permissions(
                                cargo_mute,
                                send_messages=False,
                                add_reactions=False,
                                speak=False
                            )
                        elif isinstance(canal, discord.VoiceChannel):
                            await canal.set_permissions(
                                cargo_mute,
                                speak=False,
                                stream=False
                            )
                    except discord.Forbidden:
                        continue
                
                self.dados_moderacao["configuracoes"]["cargo_mute"] = cargo_mute.id
                self.salvar_dados()
                return cargo_mute
            except discord.Forbidden:
                return None
        return cargo_mute

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def avisar(self, ctx, membro: discord.Member, *, motivo="Sem motivo especificado"):
        """Adiciona um aviso a um membro"""
        if membro == ctx.author:
            await ctx.send("❌ Você não pode se avisar!")
            return
        
        if membro.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Você não pode avisar este membro!")
            return

        user_id = str(membro.id)
        if user_id not in self.dados_moderacao["avisos"]:
            self.dados_moderacao["avisos"][user_id] = []

        aviso = {
            "motivo": motivo,
            "moderador": str(ctx.author),
            "data": datetime.now().isoformat()
        }
        
        self.dados_moderacao["avisos"][user_id].append(aviso)
        total_avisos = len(self.dados_moderacao["avisos"][user_id])
        
        self.salvar_dados()
        self.adicionar_historico("Aviso", ctx.author, membro, motivo)

        # Embed de resposta
        embed = discord.Embed(
            title="⚠️ Aviso Aplicado",
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Usuário", value=membro.mention, inline=True)
        embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
        embed.add_field(name="Total de Avisos", value=total_avisos, inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)

        await ctx.send(embed=embed)
        await self.enviar_log(embed)

        # Auto punição
        max_avisos = self.dados_moderacao["configuracoes"]["max_avisos"]
        if self.dados_moderacao["configuracoes"]["auto_punir"] and total_avisos >= max_avisos:
            try:
                await membro.kick(reason=f"Limite de avisos atingido ({total_avisos}/{max_avisos})")
                embed_kick = discord.Embed(
                    title="🦶 Auto-Kick",
                    description=f"{membro.mention} foi expulso automaticamente por atingir {max_avisos} avisos.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed_kick)
                await self.enviar_log(embed_kick)
            except discord.Forbidden:
                await ctx.send("❌ Não tenho permissão para expulsar este usuário!")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def avisos(self, ctx, membro: discord.Member = None):
        """Mostra os avisos de um membro"""
        if membro is None:
            membro = ctx.author

        user_id = str(membro.id)
        avisos = self.dados_moderacao["avisos"].get(user_id, [])

        if not avisos:
            await ctx.send(f"📋 {membro.display_name} não possui avisos.")
            return

        embed = discord.Embed(
            title=f"📋 Avisos de {membro.display_name}",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )

        for i, aviso in enumerate(avisos, 1):
            data = datetime.fromisoformat(aviso["data"]).strftime("%d/%m/%Y às %H:%M")
            embed.add_field(
                name=f"Aviso #{i}",
                value=f"**Motivo:** {aviso['motivo']}\n**Moderador:** {aviso['moderador']}\n**Data:** {data}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def limparavisos(self, ctx, membro: discord.Member):
        """Remove todos os avisos de um membro"""
        user_id = str(membro.id)
        if user_id in self.dados_moderacao["avisos"]:
            avisos_removidos = len(self.dados_moderacao["avisos"][user_id])
            del self.dados_moderacao["avisos"][user_id]
            self.salvar_dados()
            self.adicionar_historico("Limpeza de Avisos", ctx.author, membro)
            await ctx.send(f"✅ {avisos_removidos} avisos de {membro.display_name} foram removidos.")
        else:
            await ctx.send(f"❌ {membro.display_name} não possui avisos.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, membro: discord.Member, duracao: str = "10m", *, motivo="Sem motivo especificado"):
        """Silencia um membro por um tempo determinado"""
        if membro == ctx.author:
            await ctx.send("❌ Você não pode se mutar!")
            return

        if membro.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Você não pode mutar este membro!")
            return

        # Processar duração
        try:
            if duracao.endswith('s'):
                segundos = int(duracao[:-1])
            elif duracao.endswith('m'):
                segundos = int(duracao[:-1]) * 60
            elif duracao.endswith('h'):
                segundos = int(duracao[:-1]) * 3600
            elif duracao.endswith('d'):
                segundos = int(duracao[:-1]) * 86400
            else:
                segundos = int(duracao) * 60  # Default para minutos
        except ValueError:
            await ctx.send("❌ Formato de duração inválido! Use: 30s, 10m, 2h, 1d")
            return

        if segundos > 2419200:  # 28 dias
            await ctx.send("❌ Duração máxima é de 28 dias!")
            return

        # Criar/obter cargo de mute
        cargo_mute = await self._criar_cargo_mute_async(ctx.guild)
        if not cargo_mute:
            await ctx.send("❌ Não foi possível criar o cargo de mute!")
            return

        # Aplicar mute
        try:
            await membro.add_roles(cargo_mute, reason=f"Mutado por {ctx.author}: {motivo}")
            
            fim_mute = datetime.now() + timedelta(seconds=segundos)
            self.dados_moderacao["mutes"][str(membro.id)] = {
                "fim": fim_mute.isoformat(),
                "motivo": motivo,
                "moderador": str(ctx.author)
            }
            self.salvar_dados()
            self.adicionar_historico("Mute", ctx.author, membro, motivo, duracao)

            embed = discord.Embed(
                title="🔇 Membro Mutado",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Usuário", value=membro.mention, inline=True)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            embed.add_field(name="Duração", value=duracao, inline=True)
            embed.add_field(name="Motivo", value=motivo, inline=False)
            embed.add_field(name="Termina em", value=f"<t:{int(fim_mute.timestamp())}:F>", inline=False)

            await ctx.send(embed=embed)
            await self.enviar_log(embed)

            # Agendar desmute
            await asyncio.sleep(segundos)
            await self.desmutar_automatico(membro)

        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para mutar este usuário!")

    async def desmutar_automatico(self, membro):
        """Remove o mute automaticamente"""
        cargo_mute_id = self.dados_moderacao["configuracoes"]["cargo_mute"]
        if cargo_mute_id:
            cargo_mute = membro.guild.get_role(cargo_mute_id)
            if cargo_mute and cargo_mute in membro.roles:
                try:
                    await membro.remove_roles(cargo_mute, reason="Mute expirado")
                    if str(membro.id) in self.dados_moderacao["mutes"]:
                        del self.dados_moderacao["mutes"][str(membro.id)]
                        self.salvar_dados()
                except discord.Forbidden:
                    pass

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, membro: discord.Member):
        """Remove o mute de um membro"""
        cargo_mute_id = self.dados_moderacao["configuracoes"]["cargo_mute"]
        if not cargo_mute_id:
            await ctx.send("❌ Sistema de mute não configurado!")
            return

        cargo_mute = ctx.guild.get_role(cargo_mute_id)
        if not cargo_mute:
            await ctx.send("❌ Cargo de mute não encontrado!")
            return

        if cargo_mute not in membro.roles:
            await ctx.send("❌ Este membro não está mutado!")
            return

        try:
            await membro.remove_roles(cargo_mute, reason=f"Desmutado por {ctx.author}")
            if str(membro.id) in self.dados_moderacao["mutes"]:
                del self.dados_moderacao["mutes"][str(membro.id)]
                self.salvar_dados()
            
            self.adicionar_historico("Unmute", ctx.author, membro)
            await ctx.send(f"🔊 {membro.display_name} foi desmutado com sucesso!")

        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para desmutar este usuário!")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, membro: discord.Member, *, motivo="Sem motivo especificado"):
        """Expulsa um membro do servidor"""
        if membro == ctx.author:
            await ctx.send("❌ Você não pode se expulsar!")
            return

        if membro.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Você não pode expulsar este membro!")
            return

        try:
            await membro.kick(reason=f"Expulso por {ctx.author}: {motivo}")
            self.adicionar_historico("Kick", ctx.author, membro, motivo)

            embed = discord.Embed(
                title="🦶 Membro Expulso",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Usuário", value=f"{membro} ({membro.id})", inline=True)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            embed.add_field(name="Motivo", value=motivo, inline=False)

            await ctx.send(embed=embed)
            await self.enviar_log(embed)

        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para expulsar este usuário!")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, membro: discord.Member, *, motivo="Sem motivo especificado"):
        """Bane permanentemente um membro"""
        if membro == ctx.author:
            await ctx.send("❌ Você não pode se banir!")
            return

        if membro.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ Você não pode banir este membro!")
            return

        try:
            await membro.ban(reason=f"Banido por {ctx.author}: {motivo}", delete_message_days=1)
            self.adicionar_historico("Ban", ctx.author, membro, motivo)

            embed = discord.Embed(
                title="🔨 Membro Banido",
                color=discord.Color.dark_red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Usuário", value=f"{membro} ({membro.id})", inline=True)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            embed.add_field(name="Motivo", value=motivo, inline=False)

            await ctx.send(embed=embed)
            await self.enviar_log(embed)

        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para banir este usuário!")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        """Remove o ban de um usuário pelo ID"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Desbanido por {ctx.author}")
            self.adicionar_historico("Unban", ctx.author, user)
            await ctx.send(f"✅ {user} foi desbanido com sucesso!")

        except discord.NotFound:
            await ctx.send("❌ Usuário não encontrado ou não está banido!")
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para desbanir usuários!")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, quantidade: int = 10):
        """Apaga mensagens do canal"""
        if quantidade < 1 or quantidade > 100:
            await ctx.send("❌ Quantidade deve ser entre 1 e 100!")
            return

        try:
            deleted = await ctx.channel.purge(limit=quantidade + 1)  # +1 para incluir o comando
            embed = discord.Embed(
                title="🧹 Mensagens Apagadas",
                description=f"{len(deleted) - 1} mensagens foram apagadas por {ctx.author.mention}",
                color=discord.Color.green()
            )
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(3)
            await msg.delete()

        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para apagar mensagens!")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def historico(self, ctx, membro: discord.Member = None, limite: int = 10):
        """Mostra o histórico de moderação"""
        if limite > 25:
            limite = 25

        historico = self.dados_moderacao["historico"]
        if membro:
            historico = [h for h in historico if h["usuario"] == str(membro)]

        if not historico:
            await ctx.send("📋 Nenhum histórico encontrado.")
            return

        # Pegar os últimos registros
        historico_recente = historico[-limite:]
        historico_recente.reverse()

        embed = discord.Embed(
            title=f"📋 Histórico de Moderação" + (f" - {membro.display_name}" if membro else ""),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        for i, entrada in enumerate(historico_recente, 1):
            data = datetime.fromisoformat(entrada["timestamp"]).strftime("%d/%m %H:%M")
            usuario = entrada["usuario"].split("#")[0] if "#" in entrada["usuario"] else entrada["usuario"]
            moderador = entrada["moderador"].split("#")[0] if "#" in entrada["moderador"] else entrada["moderador"]
            
            valor = f"**Usuário:** {usuario}\n**Moderador:** {moderador}\n**Data:** {data}"
            if entrada.get("motivo"):
                valor += f"\n**Motivo:** {entrada['motivo']}"
            if entrada.get("duracao"):
                valor += f"\n**Duração:** {entrada['duracao']}"

            embed.add_field(
                name=f"{entrada['acao']} #{i}",
                value=valor,
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def configmod(self, ctx, opcao: str = None, *, valor=None):
        """Configura o sistema de moderação"""
        if opcao is None:
            embed = discord.Embed(title="⚙️ Configurações de Moderação", color=discord.Color.blue())
            config = self.dados_moderacao["configuracoes"]
            
            canal_logs = f"<#{config['canal_logs']}>" if config['canal_logs'] else "Não configurado"
            cargo_mute = f"<@&{config['cargo_mute']}>" if config['cargo_mute'] else "Não configurado"
            
            embed.add_field(name="Canal de Logs", value=canal_logs, inline=False)
            embed.add_field(name="Cargo de Mute", value=cargo_mute, inline=False)
            embed.add_field(name="Máximo de Avisos", value=config['max_avisos'], inline=True)
            embed.add_field(name="Auto-Punir", value="✅" if config['auto_punir'] else "❌", inline=True)
            
            embed.add_field(
                name="Comandos de Configuração",
                value="`!configmod canal_logs #canal`\n`!configmod max_avisos 3`\n`!configmod auto_punir true/false`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return

        opcao = opcao.lower()
        
        if opcao == "canal_logs":
            if valor and valor.startswith("<#") and valor.endswith(">"):
                canal_id = int(valor[2:-1])
                canal = self.bot.get_channel(canal_id)
                if canal:
                    self.dados_moderacao["configuracoes"]["canal_logs"] = canal_id
                    self.salvar_dados()
                    await ctx.send(f"✅ Canal de logs configurado para {valor}")
                else:
                    await ctx.send("❌ Canal não encontrado!")
            else:
                await ctx.send("❌ Mencione um canal válido!")
                
        elif opcao == "max_avisos":
            try:
                max_avisos = int(valor)
                if max_avisos > 0:
                    self.dados_moderacao["configuracoes"]["max_avisos"] = max_avisos
                    self.salvar_dados()
                    await ctx.send(f"✅ Máximo de avisos configurado para {max_avisos}")
                else:
                    await ctx.send("❌ Valor deve ser maior que 0!")
            except ValueError:
                await ctx.send("❌ Valor inválido!")
                
        elif opcao == "auto_punir":
            if valor.lower() in ["true", "verdadeiro", "sim", "1"]:
                self.dados_moderacao["configuracoes"]["auto_punir"] = True
                await ctx.send("✅ Auto-punição ativada!")
            elif valor.lower() in ["false", "falso", "não", "nao", "0"]:
                self.dados_moderacao["configuracoes"]["auto_punir"] = False
                await ctx.send("✅ Auto-punição desativada!")
            else:
                await ctx.send("❌ Use: true ou false")
        else:
            await ctx.send("❌ Opção inválida! Use: canal_logs, max_avisos, auto_punir")

        self.salvar_dados()

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento chamado quando o bot fica online"""
        print(f"Sistema de Moderação carregado! Arquivo: {self.arquivo_moderacao}")

async def setup(bot):
    await bot.add_cog(Moderacao(bot))