import discord
from discord.ext import commands
import json
import os
from datetime import datetime

class SistemaBoasVindas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = 'data'
        self.config_file = os.path.join(self.data_dir, 'welcome.json')
        self.ensure_data_directory()
        self.welcome_config = self.load_config()

    def ensure_data_directory(self):
        """Garante que o diretório 'data' existe"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"[INFO] Diretório '{self.data_dir}' criado com sucesso!")

    def load_config(self):
        """Carrega as configurações do arquivo JSON"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[INFO] Configurações carregadas de {self.config_file}")
                    return config
            else:
                print(f"[INFO] Arquivo {self.config_file} não existe, criando configuração padrão")
                return {}
        except Exception as e:
            print(f'[ERRO] Erro ao carregar configurações: {e}')
            return {}

    def save_config(self):
        """Salva as configurações no arquivo JSON"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.welcome_config, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Configurações salvas em {self.config_file}")
        except Exception as e:
            print(f'[ERRO] Erro ao salvar configurações: {e}')

    def get_guild_config(self, guild_id):
        """Obtém a configuração de um servidor específico"""
        guild_id = str(guild_id)
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {
                'welcome_channel': None,
                'admin_channel': None,
                'welcome_message': '🎉 Bem-vindo(a) ao servidor, {user}! Esperamos que se divirta aqui!',
                'leave_message': '😢 {user} saiu do servidor. Até logo!',
                'welcome_enabled': False,
                'leave_enabled': False,
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            self.save_config()  # Salva imediatamente quando cria nova configuração
        
        # Atualiza o timestamp de última modificação
        self.welcome_config[guild_id]['last_updated'] = datetime.now().isoformat()
        return self.welcome_config[guild_id]

    async def check_admin_channel(self, ctx):
        """Verifica se o comando está sendo usado no canal correto"""
        config = self.get_guild_config(ctx.guild.id)
        
        if config['admin_channel'] and ctx.channel.id != config['admin_channel']:
            if not ctx.author.guild_permissions.administrator:
                channel = self.bot.get_channel(config['admin_channel'])
                await ctx.send(f'❌ Use este comando no canal de administração: {channel.mention}')
                return False
        return True

    @commands.command(name='setar-admin')
    @commands.has_permissions(administrator=True)
    async def setar_admin(self, ctx, channel: discord.TextChannel = None):
        """Define o canal de administração onde os comandos serão usados"""
        if channel is None:
            channel = ctx.channel
        
        config = self.get_guild_config(ctx.guild.id)
        config['admin_channel'] = channel.id
        self.save_config()
        
        await ctx.send(f'✅ Canal de administração definido como {channel.mention}!')

    @commands.command(name='setar-boas-vindas')
    @commands.has_permissions(manage_channels=True)
    async def setar_boas_vindas(self, ctx, channel: discord.TextChannel):
        """Define o canal onde aparecerão as mensagens de boas-vindas"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        config['welcome_channel'] = channel.id
        self.save_config()
        
        await ctx.send(f'✅ Canal de boas-vindas definido como {channel.mention}!')

    @commands.command(name='ativar-entrada')
    @commands.has_permissions(manage_guild=True)
    async def ativar_entrada(self, ctx):
        """Ativa as mensagens de entrada"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        
        if not config['welcome_channel']:
            await ctx.send('❌ Primeiro defina um canal de boas-vindas com `!setar-boas-vindas #canal`')
            return
        
        config['welcome_enabled'] = True
        self.save_config()
        
        await ctx.send('✅ Mensagens de entrada ativadas!')

    @commands.command(name='ativar-saida')
    @commands.has_permissions(manage_guild=True)
    async def ativar_saida(self, ctx):
        """Ativa as mensagens de saída"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        
        if not config['welcome_channel']:
            await ctx.send('❌ Primeiro defina um canal de boas-vindas com `!setar-boas-vindas #canal`')
            return
        
        config['leave_enabled'] = True
        self.save_config()
        
        await ctx.send('✅ Mensagens de saída ativadas!')

    @commands.command(name='desativar-entrada')
    @commands.has_permissions(manage_guild=True)
    async def desativar_entrada(self, ctx):
        """Desativa as mensagens de entrada"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        config['welcome_enabled'] = False
        self.save_config()
        
        await ctx.send('✅ Mensagens de entrada desativadas!')

    @commands.command(name='desativar-saida')
    @commands.has_permissions(manage_guild=True)
    async def desativar_saida(self, ctx):
        """Desativa as mensagens de saída"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        config['leave_enabled'] = False
        self.save_config()
        
        await ctx.send('✅ Mensagens de saída desativadas!')

    @commands.command(name='msg-entrada')
    @commands.has_permissions(manage_guild=True)
    async def msg_entrada(self, ctx, *, mensagem):
        """Personaliza a mensagem de entrada. Use {user} para mencionar o usuário"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        config['welcome_message'] = mensagem
        self.save_config()
        
        await ctx.send(f'✅ Mensagem de entrada personalizada definida como: "{mensagem}"')

    @commands.command(name='msg-saida')
    @commands.has_permissions(manage_guild=True)
    async def msg_saida(self, ctx, *, mensagem):
        """Personaliza a mensagem de saída. Use {user} para o nome do usuário"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        config['leave_message'] = mensagem
        self.save_config()
        
        await ctx.send(f'✅ Mensagem de saída personalizada definida como: "{mensagem}"')

    @commands.command(name='config-bv')
    async def config_bv(self, ctx):
        """Mostra as configurações atuais do sistema de boas-vindas"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        
        embed = discord.Embed(
            title='🎉 Configurações do Sistema de Boas-vindas',
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        admin_channel = self.bot.get_channel(config['admin_channel']) if config['admin_channel'] else None
        welcome_channel = self.bot.get_channel(config['welcome_channel']) if config['welcome_channel'] else None
        
        embed.add_field(
            name='📋 Canal de Administração',
            value=admin_channel.mention if admin_channel else 'Não definido',
            inline=True
        )
        embed.add_field(
            name='💬 Canal de Boas-vindas',
            value=welcome_channel.mention if welcome_channel else 'Não definido',
            inline=True
        )
        embed.add_field(
            name='📥 Entrada Ativada',
            value='✅ Sim' if config['welcome_enabled'] else '❌ Não',
            inline=True
        )
        embed.add_field(
            name='📤 Saída Ativada',
            value='✅ Sim' if config['leave_enabled'] else '❌ Não',
            inline=True
        )
        embed.add_field(
            name='💌 Mensagem de Entrada',
            value=config['welcome_message'],
            inline=False
        )
        embed.add_field(
            name='👋 Mensagem de Saída',
            value=config['leave_message'],
            inline=False
        )
        
        # Adiciona informações sobre os timestamps se existirem
        if 'created_at' in config:
            created_date = datetime.fromisoformat(config['created_at']).strftime('%d/%m/%Y às %H:%M')
            embed.add_field(
                name='📅 Configuração criada em',
                value=created_date,
                inline=True
            )
        
        if 'last_updated' in config:
            updated_date = datetime.fromisoformat(config['last_updated']).strftime('%d/%m/%Y às %H:%M')
            embed.add_field(
                name='🔄 Última atualização',
                value=updated_date,
                inline=True
            )
        
        embed.set_footer(text=f'Arquivo: {self.config_file}')
        
        await ctx.send(embed=embed)

    @commands.command(name='backup-config')
    @commands.has_permissions(administrator=True)
    async def backup_config(self, ctx):
        """Cria um backup das configurações atuais"""
        try:
            backup_filename = f"backup_welcome_{ctx.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = os.path.join(self.data_dir, backup_filename)
            
            guild_config = self.get_guild_config(ctx.guild.id)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump({str(ctx.guild.id): guild_config}, f, indent=2, ensure_ascii=False)
            
            await ctx.send(f'✅ Backup criado com sucesso: `{backup_filename}`')
            
        except Exception as e:
            await ctx.send(f'❌ Erro ao criar backup: {e}')

    @commands.command(name='test-entrada')
    @commands.has_permissions(administrator=True)
    async def test_entrada(self, ctx):
        """Testa o sistema de entrada simulando sua própria entrada"""
        if not await self.check_admin_channel(ctx):
            return
        
        config = self.get_guild_config(ctx.guild.id)
        
        if not config['welcome_enabled']:
            await ctx.send('❌ Sistema de entrada não está ativado! Use `!ativar-entrada` primeiro.')
            return
            
        if not config['welcome_channel']:
            await ctx.send('❌ Canal de boas-vindas não configurado! Use `!setar-boas-vindas #canal` primeiro.')
            return
        
        try:
            channel = self.bot.get_channel(config['welcome_channel'])
            if not channel:
                await ctx.send('❌ Canal de boas-vindas não encontrado!')
                return
            
            welcome_text = config['welcome_message'].replace('{user}', ctx.author.mention)
            
            embed = discord.Embed(
                title='🧪 TESTE - Novo Membro!',
                description=welcome_text,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.add_field(
                name='👤 Usuário',
                value=str(ctx.author),
                inline=True
            )
            embed.add_field(
                name='📅 Conta criada em',
                value=ctx.author.created_at.strftime('%d/%m/%Y'),
                inline=True
            )
            embed.add_field(
                name='📊 Membro #',
                value=str(ctx.guild.member_count),
                inline=True
            )
            
            await channel.send(embed=embed)
            await ctx.send(f'✅ Teste enviado para {channel.mention}!')
            
        except Exception as e:
            await ctx.send(f'❌ Erro no teste: {e}')

    @commands.command(name='debug-config')
    @commands.has_permissions(administrator=True)
    async def debug_config(self, ctx):
        """Mostra informações detalhadas para debug"""
        config = self.get_guild_config(ctx.guild.id)
        
        debug_info = f"""
**🔍 DEBUG - Configurações do Servidor**
**ID do Servidor:** {ctx.guild.id}
**Nome do Servidor:** {ctx.guild.name}
**Arquivo de Config:** `{self.config_file}`
**Diretório de Dados:** `{self.data_dir}`

**📋 Configuração Atual:**
- Canal Admin ID: `{config['admin_channel']}`
- Canal Boas-vindas ID: `{config['welcome_channel']}`
- Entrada Ativada: `{config['welcome_enabled']}`
- Saída Ativada: `{config['leave_enabled']}`

**🔗 Canais Encontrados:**
- Canal Admin: {self.bot.get_channel(config['admin_channel']) if config['admin_channel'] else 'Não encontrado'}
- Canal Boas-vindas: {self.bot.get_channel(config['welcome_channel']) if config['welcome_channel'] else 'Não encontrado'}

**🤖 Intents do Bot:**
- Membros: {discord.Intents.default().members}
- Conteúdo de Mensagem: {discord.Intents.default().message_content}

**📁 Status dos Arquivos:**
- Arquivo existe: {os.path.exists(self.config_file)}
- Diretório existe: {os.path.exists(self.data_dir)}
"""
        
        await ctx.send(debug_info)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Evento quando um membro entra no servidor"""
        print(f"[DEBUG] Membro {member} entrou no servidor {member.guild.name}")
        
        config = self.get_guild_config(member.guild.id)
        print(f"[DEBUG] Config carregada: {config}")
        
        if not config['welcome_enabled']:
            print(f"[DEBUG] Mensagens de entrada desabilitadas")
            return
            
        if not config['welcome_channel']:
            print(f"[DEBUG] Canal de boas-vindas não configurado")
            return
        
        try:
            channel = self.bot.get_channel(config['welcome_channel'])
            if not channel:
                print(f"[DEBUG] Canal {config['welcome_channel']} não encontrado")
                return
            
            print(f"[DEBUG] Enviando mensagem no canal {channel.name}")
            
            welcome_text = config['welcome_message'].replace('{user}', member.mention)
            
            embed = discord.Embed(
                title='🎉 Novo Membro!',
                description=welcome_text,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name='👤 Usuário',
                value=str(member),
                inline=True
            )
            embed.add_field(
                name='📅 Conta criada em',
                value=member.created_at.strftime('%d/%m/%Y'),
                inline=True
            )
            embed.add_field(
                name='📊 Membro #',
                value=str(member.guild.member_count),
                inline=True
            )
            
            await channel.send(embed=embed)
            print(f"[DEBUG] Mensagem enviada com sucesso!")
            
        except Exception as e:
            print(f'[ERRO] Erro ao enviar mensagem de boas-vindas: {e}')

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Evento quando um membro sai do servidor"""
        print(f"[DEBUG] Membro {member} saiu do servidor {member.guild.name}")
        
        config = self.get_guild_config(member.guild.id)
        print(f"[DEBUG] Config carregada: {config}")
        
        if not config['leave_enabled']:
            print(f"[DEBUG] Mensagens de saída desabilitadas")
            return
            
        if not config['welcome_channel']:
            print(f"[DEBUG] Canal de boas-vindas não configurado")
            return
        
        try:
            channel = self.bot.get_channel(config['welcome_channel'])
            if not channel:
                print(f"[DEBUG] Canal {config['welcome_channel']} não encontrado")
                return
            
            print(f"[DEBUG] Enviando mensagem de saída no canal {channel.name}")
            
            leave_text = config['leave_message'].replace('{user}', str(member))
            
            embed = discord.Embed(
                title='👋 Membro Saiu',
                description=leave_text,
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name='👤 Usuário',
                value=str(member),
                inline=True
            )
            embed.add_field(
                name='📊 Membros restantes',
                value=str(member.guild.member_count),
                inline=True
            )
            
            await channel.send(embed=embed)
            print(f"[DEBUG] Mensagem de saída enviada com sucesso!")
            
        except Exception as e:
            print(f'[ERRO] Erro ao enviar mensagem de saída: {e}')

    # Tratamento de erros
    @setar_admin.error
    async def setar_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send('❌ Você precisa ter permissão de administrador para usar este comando!')

    @setar_boas_vindas.error
    async def setar_boas_vindas_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send('❌ Você precisa ter permissão de gerenciar canais para usar este comando!')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('❌ Você precisa mencionar um canal! Exemplo: `!setar-boas-vindas #geral`')

    @ativar_entrada.error
    @ativar_saida.error
    @desativar_entrada.error
    @desativar_saida.error
    @msg_entrada.error
    @msg_saida.error
    async def manage_guild_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send('❌ Você precisa ter permissão de gerenciar servidor para usar este comando!')
        elif isinstance(error, commands.MissingRequiredArgument):
            if ctx.command.name in ['msg-entrada', 'msg-saida']:
                await ctx.send('❌ Você precisa fornecer uma mensagem! Use `{user}` para mencionar o usuário.')

async def setup(bot):
    await bot.add_cog(SistemaBoasVindas(bot))