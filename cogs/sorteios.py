import discord
from discord.ext import commands
import json
import os
import random
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Configuração de logging
logger = logging.getLogger(__name__)

class SorteioConfig:
    """Classe para gerenciar configurações de sorteio de forma mais estruturada."""
    
    def __init__(self, caminho_arquivo: str = "data/sorteios.json"):
        self.caminho_arquivo = caminho_arquivo
        self._config = self._carregar_config()
    
    def _carregar_config(self) -> Dict[str, Any]:
        """Carrega as configurações do arquivo JSON."""
        try:
            if not os.path.exists(self.caminho_arquivo):
                # Cria o diretório se não existir
                os.makedirs(os.path.dirname(self.caminho_arquivo), exist_ok=True)
                return {}
            
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return {}
    
    def salvar_config(self) -> bool:
        """Salva as configurações no arquivo JSON."""
        try:
            os.makedirs(os.path.dirname(self.caminho_arquivo), exist_ok=True)
            with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            return False
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Obtém a configuração de uma guild específica."""
        return self._config.get(str(guild_id), {})
    
    def set_guild_config(self, guild_id: int, key: str, value: Any) -> bool:
        """Define uma configuração para uma guild específica."""
        guild_str = str(guild_id)
        if guild_str not in self._config:
            self._config[guild_str] = {}
        
        self._config[guild_str][key] = value
        return self.salvar_config()

class SorteioEmbed:
    """Classe para criar embeds padronizados para sorteios."""
    
    @staticmethod
    def criar_sorteio(premio: str, autor: discord.Member) -> discord.Embed:
        """Cria embed para sorteio ativo."""
        embed = discord.Embed(
            title="🎉 SORTEIO ATIVO",
            description=f"**Prêmio:** {premio}\n\n" +
                       "Reaja com 🎉 para participar do sorteio!\n" +
                       "Boa sorte a todos os participantes!",
            color=0xFFD700,  # Cor dourada
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="📋 Como participar",
            value="Clique na reação 🎉 abaixo para entrar no sorteio",
            inline=False
        )
        embed.set_footer(
            text=f"Sorteio iniciado por {autor.display_name}",
            icon_url=autor.display_avatar.url
        )
        return embed
    
    @staticmethod
    def criar_vencedor(vencedor: discord.Member, premio: str) -> discord.Embed:
        """Cria embed para anunciar o vencedor."""
        embed = discord.Embed(
            title="🏆 TEMOS UM VENCEDOR!",
            description=f"🎉 **Parabéns {vencedor.mention}!**\n\n" +
                       f"Você ganhou: **{premio}**\n\n" +
                       "Entre em contato com a administração para resgatar seu prêmio!",
            color=0x00FF00,  # Verde
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=vencedor.display_avatar.url)
        embed.set_footer(text="Sorteio finalizado")
        return embed
    
    @staticmethod
    def criar_erro(titulo: str, descricao: str) -> discord.Embed:
        """Cria embed para mensagens de erro."""
        embed = discord.Embed(
            title=f"❌ {titulo}",
            description=descricao,
            color=0xFF0000,  # Vermelho
            timestamp=datetime.utcnow()
        )
        return embed
    
    @staticmethod
    def criar_sucesso(titulo: str, descricao: str) -> discord.Embed:
        """Cria embed para mensagens de sucesso."""
        embed = discord.Embed(
            title=f"✅ {titulo}",
            description=descricao,
            color=0x00FF00,  # Verde
            timestamp=datetime.utcnow()
        )
        return embed

class Sorteios(commands.Cog):
    """Cog para gerenciamento de sorteios no Discord."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_manager = SorteioConfig()
        self.sorteios_ativos: Dict[int, int] = {}  # guild_id: message_id
        
        logger.info("Cog de Sorteios inicializado com sucesso")
    
    def _verificar_permissao_canal(self, ctx: commands.Context) -> bool:
        """Verifica se o comando está sendo usado no canal correto."""
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        canal_comando = guild_config.get("canal_comando")
        
        if not canal_comando:
            return True  # Se não há canal definido, permite em qualquer lugar
        
        return ctx.channel.id == canal_comando
    
    def _obter_canal_sorteio(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Obtém o canal de sorteio configurado para a guild."""
        guild_config = self.config_manager.get_guild_config(guild.id)
        canal_id = guild_config.get("canal_sorteio")
        
        if not canal_id:
            return None
        
        return guild.get_channel(canal_id)
    
    async def _enviar_resposta(self, ctx: commands.Context, embed: discord.Embed, 
                              delete_after: Optional[float] = None) -> None:
        """Envia uma resposta usando embed com tratamento de erro."""
        try:
            await ctx.send(embed=embed, delete_after=delete_after)
        except discord.Forbidden:
            logger.error(f"Sem permissão para enviar mensagem no canal {ctx.channel.id}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")

    @commands.command(name="setcomandocanal", aliases=["scc"])
    @commands.has_permissions(administrator=True)
    async def set_comando_canal(self, ctx: commands.Context, canal: discord.TextChannel):
        """
        Define o canal onde os administradores podem usar os comandos de sorteio.
        
        Uso: !setcomandocanal #canal
        Aliases: !scc
        """
        try:
            sucesso = self.config_manager.set_guild_config(
                ctx.guild.id, "canal_comando", canal.id
            )
            
            if sucesso:
                embed = SorteioEmbed.criar_sucesso(
                    "Canal Configurado",
                    f"Canal de comandos de sorteio definido para {canal.mention}.\n" +
                    "Agora apenas administradores podem usar comandos de sorteio neste canal."
                )
                logger.info(f"Canal de comandos definido para {canal.name} na guild {ctx.guild.name}")
            else:
                embed = SorteioEmbed.criar_erro(
                    "Erro de Configuração",
                    "Não foi possível salvar a configuração. Tente novamente."
                )
            
            await self._enviar_resposta(ctx, embed)
            
        except Exception as e:
            logger.error(f"Erro ao configurar canal de comandos: {e}")
            embed = SorteioEmbed.criar_erro(
                "Erro Interno",
                "Ocorreu um erro inesperado ao configurar o canal."
            )
            await self._enviar_resposta(ctx, embed)

    @commands.command(name="setsorteiocanal", aliases=["ssc"])
    @commands.has_permissions(administrator=True)
    async def set_sorteio_canal(self, ctx: commands.Context, canal: discord.TextChannel):
        """
        Define o canal onde os sorteios serão postados.
        
        Uso: !setsorteiocanal #canal
        Aliases: !ssc
        """
        try:
            sucesso = self.config_manager.set_guild_config(
                ctx.guild.id, "canal_sorteio", canal.id
            )
            
            if sucesso:
                embed = SorteioEmbed.criar_sucesso(
                    "Canal Configurado",
                    f"Canal de sorteios definido para {canal.mention}.\n" +
                    "Todos os sorteios serão postados neste canal."
                )
                logger.info(f"Canal de sorteios definido para {canal.name} na guild {ctx.guild.name}")
            else:
                embed = SorteioEmbed.criar_erro(
                    "Erro de Configuração",
                    "Não foi possível salvar a configuração. Tente novamente."
                )
            
            await self._enviar_resposta(ctx, embed)
            
        except Exception as e:
            logger.error(f"Erro ao configurar canal de sorteios: {e}")
            embed = SorteioEmbed.criar_erro(
                "Erro Interno",
                "Ocorreu um erro inesperado ao configurar o canal."
            )
            await self._enviar_resposta(ctx, embed)

    @commands.command(name="sorteio")
    @commands.has_permissions(administrator=True)
    async def iniciar_sorteio(self, ctx: commands.Context, *, premio: str):
        """
        Inicia um sorteio com o prêmio informado.
        
        Uso: !sorteio [prêmio]
        Exemplo: !sorteio Nitro por 1 mês
        """
        # Verificar se está no canal correto
        if not self._verificar_permissao_canal(ctx):
            embed = SorteioEmbed.criar_erro(
                "Canal Incorreto",
                "Este comando só pode ser usado no canal autorizado de comandos."
            )
            await self._enviar_resposta(ctx, embed, delete_after=10)
            return
        
        # Verificar se já existe um sorteio ativo
        if ctx.guild.id in self.sorteios_ativos:
            embed = SorteioEmbed.criar_erro(
                "Sorteio Ativo",
                "Já existe um sorteio ativo neste servidor. Finalize-o antes de iniciar outro."
            )
            await self._enviar_resposta(ctx, embed, delete_after=10)
            return
        
        # Obter canal de sorteio
        canal_sorteio = self._obter_canal_sorteio(ctx.guild)
        if not canal_sorteio:
            embed = SorteioEmbed.criar_erro(
                "Canal Não Configurado",
                "O canal de sorteios ainda não foi configurado.\n" +
                "Use `!setsorteiocanal #canal` para configurar."
            )
            await self._enviar_resposta(ctx, embed)
            return
        
        try:
            # Criar e enviar embed do sorteio
            embed_sorteio = SorteioEmbed.criar_sorteio(premio, ctx.author)
            msg_sorteio = await canal_sorteio.send(embed=embed_sorteio)
            await msg_sorteio.add_reaction("🎉")
            
            # Registrar sorteio ativo
            self.sorteios_ativos[ctx.guild.id] = msg_sorteio.id
            
            # Confirmar criação
            embed_confirmacao = SorteioEmbed.criar_sucesso(
                "Sorteio Iniciado",
                f"Sorteio criado com sucesso em {canal_sorteio.mention}!\n" +
                f"**Prêmio:** {premio}"
            )
            await self._enviar_resposta(ctx, embed_confirmacao)
            
            logger.info(f"Sorteio iniciado na guild {ctx.guild.name} por {ctx.author.name}")
            
        except discord.Forbidden:
            embed = SorteioEmbed.criar_erro(
                "Permissões Insuficientes",
                f"Não tenho permissão para enviar mensagens em {canal_sorteio.mention}."
            )
            await self._enviar_resposta(ctx, embed)
        except Exception as e:
            logger.error(f"Erro ao iniciar sorteio: {e}")
            embed = SorteioEmbed.criar_erro(
                "Erro Interno",
                "Ocorreu um erro inesperado ao iniciar o sorteio."
            )
            await self._enviar_resposta(ctx, embed)

    @commands.command(name="vencedor")
    @commands.has_permissions(administrator=True)
    async def escolher_vencedor(self, ctx: commands.Context):
        """
        Escolhe aleatoriamente um vencedor do sorteio atual.
        
        Uso: !vencedor
        """
        # Verificar se está no canal correto
        if not self._verificar_permissao_canal(ctx):
            embed = SorteioEmbed.criar_erro(
                "Canal Incorreto",
                "Este comando só pode ser usado no canal autorizado de comandos."
            )
            await self._enviar_resposta(ctx, embed, delete_after=10)
            return
        
        # Verificar se há sorteio ativo
        if ctx.guild.id not in self.sorteios_ativos:
            embed = SorteioEmbed.criar_erro(
                "Nenhum Sorteio Ativo",
                "Não há sorteio ativo para escolher vencedor."
            )
            await self._enviar_resposta(ctx, embed)
            return
        
        canal_sorteio = self._obter_canal_sorteio(ctx.guild)
        if not canal_sorteio:
            embed = SorteioEmbed.criar_erro(
                "Canal Não Encontrado",
                "O canal de sorteios configurado não foi encontrado."
            )
            await self._enviar_resposta(ctx, embed)
            return
        
        try:
            # Buscar mensagem do sorteio
            msg_id = self.sorteios_ativos[ctx.guild.id]
            msg_sorteio = await canal_sorteio.fetch_message(msg_id)
            
            # Encontrar reação do sorteio
            reaction = discord.utils.get(msg_sorteio.reactions, emoji="🎉")
            if not reaction:
                embed = SorteioEmbed.criar_erro(
                    "Sem Reações",
                    "Nenhuma reação encontrada no sorteio."
                )
                await self._enviar_resposta(ctx, embed)
                return
            
            # Obter participantes (excluindo bots)
            participantes = []
            async for user in reaction.users():
                if not user.bot:
                    participantes.append(user)
            
            if not participantes:
                embed = SorteioEmbed.criar_erro(
                    "Sem Participantes",
                    "Nenhum participante válido encontrado no sorteio."
                )
                await self._enviar_resposta(ctx, embed)
                return
            
            # Escolher vencedor aleatoriamente
            vencedor = random.choice(participantes)
            
            # Extrair prêmio do embed original
            premio = msg_sorteio.embeds[0].description.split("**Prêmio:** ")[1].split("\n")[0]
            
            # Anunciar vencedor
            embed_vencedor = SorteioEmbed.criar_vencedor(vencedor, premio)
            await canal_sorteio.send(embed=embed_vencedor)
            
            # Remover sorteio ativo
            del self.sorteios_ativos[ctx.guild.id]
            
            # Confirmar para o administrador
            embed_confirmacao = SorteioEmbed.criar_sucesso(
                "Vencedor Escolhido",
                f"Vencedor anunciado: {vencedor.mention}\n" +
                f"Total de participantes: **{len(participantes)}**"
            )
            await self._enviar_resposta(ctx, embed_confirmacao)
            
            logger.info(f"Vencedor escolhido na guild {ctx.guild.name}: {vencedor.name}")
            
        except discord.NotFound:
            embed = SorteioEmbed.criar_erro(
                "Mensagem Não Encontrada",
                "A mensagem do sorteio não foi encontrada."
            )
            await self._enviar_resposta(ctx, embed)
            # Limpar sorteio inválido
            if ctx.guild.id in self.sorteios_ativos:
                del self.sorteios_ativos[ctx.guild.id]
        except Exception as e:
            logger.error(f"Erro ao escolher vencedor: {e}")
            embed = SorteioEmbed.criar_erro(
                "Erro Interno",
                f"Ocorreu um erro inesperado: {str(e)[:100]}..."
            )
            await self._enviar_resposta(ctx, embed)

    @commands.command(name="encerrarsorteio")
    @commands.has_permissions(administrator=True)
    async def encerrar_sorteio(self, ctx: commands.Context):
        """
        Encerra o sorteio atual sem escolher vencedor.
        
        Uso: !encerrarsorteio
        """
        # Verificar se está no canal correto
        if not self._verificar_permissao_canal(ctx):
            embed = SorteioEmbed.criar_erro(
                "Canal Incorreto",
                "Este comando só pode ser usado no canal autorizado de comandos."
            )
            await self._enviar_resposta(ctx, embed, delete_after=10)
            return
        
        # Verificar se há sorteio ativo
        if ctx.guild.id not in self.sorteios_ativos:
            embed = SorteioEmbed.criar_erro(
                "Nenhum Sorteio Ativo",
                "Não há sorteio ativo para encerrar."
            )
            await self._enviar_resposta(ctx, embed)
            return
        
        canal_sorteio = self._obter_canal_sorteio(ctx.guild)
        if not canal_sorteio:
            embed = SorteioEmbed.criar_erro(
                "Canal Não Encontrado",
                "O canal de sorteios configurado não foi encontrado."
            )
            await self._enviar_resposta(ctx, embed)
            return
        
        try:
            # Buscar e limpar mensagem do sorteio
            msg_id = self.sorteios_ativos[ctx.guild.id]
            msg_sorteio = await canal_sorteio.fetch_message(msg_id)
            await msg_sorteio.clear_reactions()
            
            # Remover sorteio ativo
            del self.sorteios_ativos[ctx.guild.id]
            
            # Confirmar encerramento
            embed_confirmacao = SorteioEmbed.criar_sucesso(
                "Sorteio Encerrado",
                "O sorteio foi encerrado com sucesso e as reações foram removidas."
            )
            await self._enviar_resposta(ctx, embed_confirmacao)
            
            logger.info(f"Sorteio encerrado na guild {ctx.guild.name} por {ctx.author.name}")
            
        except discord.NotFound:
            # Limpar sorteio inválido
            del self.sorteios_ativos[ctx.guild.id]
            embed = SorteioEmbed.criar_erro(
                "Mensagem Não Encontrada",
                "A mensagem do sorteio não foi encontrada, mas o registro foi limpo."
            )
            await self._enviar_resposta(ctx, embed)
        except discord.Forbidden:
            embed = SorteioEmbed.criar_erro(
                "Permissões Insuficientes",
                "Não tenho permissão para remover reações da mensagem."
            )
            await self._enviar_resposta(ctx, embed)
        except Exception as e:
            logger.error(f"Erro ao encerrar sorteio: {e}")
            embed = SorteioEmbed.criar_erro(
                "Erro Interno",
                f"Ocorreu um erro inesperado: {str(e)[:100]}..."
            )
            await self._enviar_resposta(ctx, embed)

    @commands.command(name="mostrarsorteio", aliases=["statussorteio", "configsorteio"])
    async def mostrar_sorteio(self, ctx: commands.Context):
        """
        Mostra as configurações atuais de sorteios do servidor.
        
        Uso: !mostrarsorteio
        Aliases: !statussorteio, !configsorteio
        """
        guild_config = self.config_manager.get_guild_config(ctx.guild.id)
        
        canal_sorteio = ctx.guild.get_channel(guild_config.get("canal_sorteio", 0))
        canal_comando = ctx.guild.get_channel(guild_config.get("canal_comando", 0))
        
        # Status do sorteio ativo
        sorteio_ativo = "✅ Sim" if ctx.guild.id in self.sorteios_ativos else "❌ Não"
        
        embed = discord.Embed(
            title="🎲 Configurações de Sorteio",
            description="Configurações atuais do sistema de sorteios",
            color=0x3498DB,  # Azul
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📺 Canal de Sorteios",
            value=canal_sorteio.mention if canal_sorteio else "❌ Não configurado",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Canal de Comandos",
            value=canal_comando.mention if canal_comando else "❌ Não configurado",
            inline=True
        )
        
        embed.add_field(
            name="🎉 Sorteio Ativo",
            value=sorteio_ativo,
            inline=True
        )
        
        embed.add_field(
            name="📋 Comandos Disponíveis",
            value="`!setsorteiocanal` - Configurar canal de sorteios\n" +
                  "`!setcomandocanal` - Configurar canal de comandos\n" +
                  "`!sorteio` - Iniciar sorteio\n" +
                  "`!vencedor` - Escolher vencedor\n" +
                  "`!encerrarsorteio` - Encerrar sorteio",
            inline=False
        )
        
        embed.set_footer(
            text=f"Servidor: {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        await self._enviar_resposta(ctx, embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Remove configurações quando o bot sai de um servidor."""
        if guild.id in self.sorteios_ativos:
            del self.sorteios_ativos[guild.id]
        
        # Opcionalmente, limpar configurações salvas
        # guild_config = self.config_manager._config.pop(str(guild.id), None)
        # if guild_config:
        #     self.config_manager.salvar_config()
        
        logger.info(f"Bot removido da guild {guild.name}, limpando dados temporários")

async def setup(bot: commands.Bot):
    """Função para adicionar o cog ao bot."""
    await bot.add_cog(Sorteios(bot))