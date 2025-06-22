import discord
from discord.ext import commands
import re
import asyncio
from typing import Set, Dict, List
import json
import os

class SmartModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_warnings: Dict[int, int] = {}
        self.load_config()
        
    def load_config(self):
        """Load moderation config from file"""
        try:
            with open('moderation_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.blocked_words = set(config.get('blocked_words', []))
                self.max_warnings = config.get('max_warnings', 3)
                self.warning_decay_hours = config.get('warning_decay_hours', 24)
        except FileNotFoundError:
            # Default minimal config
            self.blocked_words = set(['spam', 'teste_palavra'])
            self.max_warnings = 3
            self.warning_decay_hours = 24
            self.save_config()
    
    def save_config(self):
        """Save current config to file"""
        config = {
            'blocked_words': list(self.blocked_words),
            'max_warnings': self.max_warnings,
            'warning_decay_hours': self.warning_decay_hours
        }
        with open('moderation_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def contains_blocked_content(self, text: str) -> bool:
        """Check if text contains blocked content using multiple methods"""
        text_lower = text.lower()
        
        # Remove special characters and spaces for bypass detection
        cleaned_text = re.sub(r'[^a-záàâãéèêíìîóòôõúùûç]', '', text_lower)
        
        # Check direct matches
        if any(word in text_lower for word in self.blocked_words):
            return True
            
        # Check for common bypass attempts (l33t speak, spacing, etc.)
        bypass_patterns = {
            'a': ['@', '4', 'á', 'à', 'â', 'ã'],
            'e': ['3', 'é', 'è', 'ê'],
            'i': ['1', '!', 'í', 'ì', 'î'],
            'o': ['0', 'ó', 'ò', 'ô', 'õ'],
            'u': ['ú', 'ù', 'û'],
            's': ['$', '5'],
        }
        
        normalized_text = text_lower
        for normal, variants in bypass_patterns.items():
            for variant in variants:
                normalized_text = normalized_text.replace(variant, normal)
        
        return any(word in normalized_text for word in self.blocked_words)
    
    async def handle_violation(self, message: discord.Message):
        """Handle when a user violates moderation rules"""
        user_id = message.author.id
        
        # Increment warnings
        self.user_warnings[user_id] = self.user_warnings.get(user_id, 0) + 1
        warnings = self.user_warnings[user_id]
        
        try:
            await message.delete()
            
            if warnings >= self.max_warnings:
                # Timeout user for repeated violations
                try:
                    timeout_duration = discord.utils.utcnow() + discord.timedelta(minutes=10)
                    await message.author.timeout(timeout_duration, reason="Múltiplas violações de moderação")
                    
                    embed = discord.Embed(
                        title="⚠️ Usuário Temporariamente Silenciado",
                        description=f"{message.author.mention} foi silenciado por 10 minutos devido a múltiplas violações.",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed, delete_after=10)
                    
                    # Reset warnings after timeout
                    self.user_warnings[user_id] = 0
                    
                except discord.Forbidden:
                    # Fallback if can't timeout
                    embed = discord.Embed(
                        title="⚠️ Múltiplas Violações Detectadas",
                        description=f"{message.author.mention}, você atingiu o limite de avisos. Moderadores foram notificados.",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed, delete_after=10)
            else:
                # Regular warning
                embed = discord.Embed(
                    title="⚠️ Mensagem Removida",
                    description=f"{message.author.mention}, sua mensagem violou as regras do servidor.\n**Avisos: {warnings}/{self.max_warnings}**",
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=embed, delete_after=8)
                
        except discord.Forbidden:
            # If can't delete message, just warn
            embed = discord.Embed(
                title="⚠️ Conteúdo Inapropriado Detectado",
                description=f"{message.author.mention}, por favor, mantenha um ambiente respeitoso.",
                color=discord.Color.yellow()
            )
            await message.channel.send(embed=embed, delete_after=5)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots and system messages
        if message.author.bot or message.is_system():
            return
            
        # Skip if user has administrator permissions
        if message.author.guild_permissions.administrator:
            return
            
        # Check for violations
        if self.contains_blocked_content(message.content):
            await self.handle_violation(message)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Also check edited messages"""
        if after.author.bot or after.is_system():
            return
            
        if after.author.guild_permissions.administrator:
            return
            
        if self.contains_blocked_content(after.content):
            await self.handle_violation(after)
    
    # Admin commands for managing the moderation system
    @commands.group(name='modconfig', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def mod_config(self, ctx):
        """Configurações de moderação"""
        embed = discord.Embed(
            title="🛡️ Configurações de Moderação",
            description="Use os subcomandos para gerenciar a moderação:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Comandos Disponíveis",
            value="`modconfig add <palavra>` - Adicionar palavra bloqueada\n"
                  "`modconfig remove <palavra>` - Remover palavra bloqueada\n"
                  "`modconfig list` - Listar palavras bloqueadas\n"
                  "`modconfig warnings <usuário>` - Ver avisos de usuário\n"
                  "`modconfig reset <usuário>` - Resetar avisos de usuário",
            inline=False
        )
        await ctx.send(embed=embed)
    
    @mod_config.command(name='add')
    @commands.has_permissions(administrator=True)
    async def add_blocked_word(self, ctx, *, word: str):
        """Adicionar palavra à lista de bloqueados"""
        word_lower = word.lower()
        if word_lower not in self.blocked_words:
            self.blocked_words.add(word_lower)
            self.save_config()
            await ctx.send(f"✅ Palavra '{word}' adicionada à lista de bloqueados.")
        else:
            await ctx.send(f"⚠️ Palavra '{word}' já está na lista de bloqueados.")
    
    @mod_config.command(name='remove')
    @commands.has_permissions(administrator=True)
    async def remove_blocked_word(self, ctx, *, word: str):
        """Remover palavra da lista de bloqueados"""
        word_lower = word.lower()
        if word_lower in self.blocked_words:
            self.blocked_words.remove(word_lower)
            self.save_config()
            await ctx.send(f"✅ Palavra '{word}' removida da lista de bloqueados.")
        else:
            await ctx.send(f"⚠️ Palavra '{word}' não está na lista de bloqueados.")
    
    @mod_config.command(name='list')
    @commands.has_permissions(administrator=True)
    async def list_blocked_words(self, ctx):
        """Listar palavras bloqueadas (via DM)"""
        if not self.blocked_words:
            await ctx.send("📝 Nenhuma palavra bloqueada configurada.")
            return
            
        word_list = ", ".join(sorted(self.blocked_words))
        try:
            await ctx.author.send(f"📝 **Palavras bloqueadas:** {word_list}")
            await ctx.send("✅ Lista enviada via DM.")
        except discord.Forbidden:
            await ctx.send("❌ Não foi possível enviar a lista via DM. Verifique suas configurações de privacidade.")
    
    @mod_config.command(name='warnings')
    @commands.has_permissions(administrator=True)
    async def check_warnings(self, ctx, user: discord.Member):
        """Verificar avisos de um usuário"""
        warnings = self.user_warnings.get(user.id, 0)
        embed = discord.Embed(
            title="📊 Status de Avisos",
            description=f"**Usuário:** {user.mention}\n**Avisos:** {warnings}/{self.max_warnings}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    @mod_config.command(name='reset')
    @commands.has_permissions(administrator=True)
    async def reset_warnings(self, ctx, user: discord.Member):
        """Resetar avisos de um usuário"""
        if user.id in self.user_warnings:
            del self.user_warnings[user.id]
        await ctx.send(f"✅ Avisos de {user.mention} foram resetados.")

async def setup(bot):
    await bot.add_cog(SmartModeration(bot))