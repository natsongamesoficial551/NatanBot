import discord
from discord.ext import commands
import asyncio
import json
import random
from datetime import datetime, timedelta
import os

# Dados do sistema (em produção use banco de dados)
data = {
    'users': {},
    'shop': {
        'items': {
            '🎮': {'name': 'Game Premium', 'price': 1000, 'description': 'Jogo premium exclusivo'},
            '💎': {'name': 'Diamante', 'price': 500, 'description': 'Diamante raro e brilhante'},
            '🔥': {'name': 'Fire Boost', 'price': 200, 'description': 'Dobra XP por 1 hora'},
            '🌟': {'name': 'Estrela da Sorte', 'price': 300, 'description': 'Aumenta chance de sucesso'},
            '🎁': {'name': 'Caixa Misteriosa', 'price': 150, 'description': 'Pode conter qualquer coisa!'}
        }
    },
    'vip': {}
}

def save_data():
    with open('economy_data.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)

def load_data():
    global data
    if os.path.exists('economy_data.json'):
        with open('economy_data.json', 'r') as f:
            data = json.load(f)

def get_user_data(user_id):
    if str(user_id) not in data['users']:
        data['users'][str(user_id)] = {
            'money': 100,
            'bank': 0,
            'inventory': {},
            'daily_claimed': None,
            'work_cooldown': None,
            'level': 1,
            'xp': 0
        }
    return data['users'][str(user_id)]

def is_vip(user_id):
    vip_data = data['vip'].get(str(user_id))
    if not vip_data:
        return False
    if datetime.fromisoformat(vip_data['expires']) > datetime.now():
        return True
    else:
        del data['vip'][str(user_id)]
        return False

async def add_xp(user_id, amount):
    user_data = get_user_data(user_id)
    user_data['xp'] += amount
    level_up_xp = user_data['level'] * 100
    if user_data['xp'] >= level_up_xp:
        user_data['level'] += 1
        user_data['xp'] = 0
        return True
    return False

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_data()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Sistema de Economia carregado!')

    # COMANDOS DE ECONOMIA

    @commands.command(name='saldo', aliases=['balance', 'bal'])
    async def balance(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        user_data = get_user_data(member.id)
        vip_status = "👑 VIP" if is_vip(member.id) else "Comum"
        
        embed = discord.Embed(title=f"💰 Saldo de {member.display_name}", color=0x00ff00)
        embed.add_field(name="Carteira", value=f"${user_data['money']}", inline=True)
        embed.add_field(name="Banco", value=f"${user_data['bank']}", inline=True)
        embed.add_field(name="Total", value=f"${user_data['money'] + user_data['bank']}", inline=True)
        embed.add_field(name="Level", value=f"{user_data['level']} ({user_data['xp']} XP)", inline=True)
        embed.add_field(name="Status", value=vip_status, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name='daily', aliases=['diario'])
    async def daily(self, ctx):
        user_data = get_user_data(ctx.author.id)
        now = datetime.now()
        
        if user_data['daily_claimed']:
            last_claim = datetime.fromisoformat(user_data['daily_claimed'])
            if now - last_claim < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_claim)
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(f"⏰ Você já coletou hoje! Volte em {hours}h {minutes}m")
                return
        
        base_reward = 100
        vip_bonus = 50 if is_vip(ctx.author.id) else 0
        total_reward = base_reward + vip_bonus
        
        user_data['money'] += total_reward
        user_data['daily_claimed'] = now.isoformat()
        
        embed = discord.Embed(title="🎁 Daily Coletado!", color=0x00ff00)
        embed.add_field(name="Recompensa Base", value=f"${base_reward}", inline=True)
        if vip_bonus > 0:
            embed.add_field(name="Bônus VIP", value=f"${vip_bonus}", inline=True)
        embed.add_field(name="Total Recebido", value=f"${total_reward}", inline=True)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='work', aliases=['trabalhar'])
    async def work(self, ctx):
        user_data = get_user_data(ctx.author.id)
        now = datetime.now()
        
        if user_data['work_cooldown']:
            last_work = datetime.fromisoformat(user_data['work_cooldown'])
            if now - last_work < timedelta(hours=1):
                remaining = timedelta(hours=1) - (now - last_work)
                minutes, seconds = divmod(remaining.seconds, 60)
                await ctx.send(f"⏰ Você está cansado! Descanse por {minutes}m {seconds}s")
                return
        
        jobs = [
            "programou um bot", "entregou pizza", "lavou carros", "cuidou de pets",
            "deu aulas", "fez stream", "vendeu doces", "cortou grama"
        ]
        
        base_pay = random.randint(50, 150)
        vip_bonus = int(base_pay * 0.5) if is_vip(ctx.author.id) else 0
        total_pay = base_pay + vip_bonus
        
        user_data['money'] += total_pay
        user_data['work_cooldown'] = now.isoformat()
        
        job = random.choice(jobs)
        embed = discord.Embed(title="💼 Trabalho Concluído!", 
                             description=f"Você {job} e ganhou ${total_pay}!", 
                             color=0x00ff00)
        
        # Chance de ganhar XP
        if await add_xp(ctx.author.id, random.randint(5, 15)):
            embed.add_field(name="🎉 Level Up!", value=f"Você chegou ao level {user_data['level']}!", inline=False)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='apostar', aliases=['bet'])
    async def bet(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Valor inválido!")
            return
        
        user_data = get_user_data(ctx.author.id)
        if user_data['money'] < amount:
            await ctx.send("❌ Você não tem dinheiro suficiente!")
            return
        
        # VIP tem melhor chance de ganhar
        win_chance = 0.55 if is_vip(ctx.author.id) else 0.45
        
        if random.random() < win_chance:
            winnings = int(amount * random.uniform(1.5, 2.5))
            user_data['money'] += winnings - amount
            embed = discord.Embed(title="🎰 Você Ganhou!", 
                                 description=f"Apostou ${amount} e ganhou ${winnings}!", 
                                 color=0x00ff00)
        else:
            user_data['money'] -= amount
            embed = discord.Embed(title="💸 Você Perdeu!", 
                                 description=f"Perdeu ${amount} na aposta!", 
                                 color=0xff0000)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='roubar', aliases=['rob', 'steal'])
    async def rob(self, ctx, member: discord.Member):
        if member == ctx.author:
            await ctx.send("❌ Você não pode roubar de si mesmo!")
            return
        
        if member.bot:
            await ctx.send("❌ Você não pode roubar de bots!")
            return
        
        robber_data = get_user_data(ctx.author.id)
        target_data = get_user_data(member.id)
        
        # Cooldown de 2 horas para roubar
        now = datetime.now()
        cooldown_key = f'rob_cooldown_{ctx.author.id}'
        
        if hasattr(robber_data, 'rob_cooldown') and robber_data.get('rob_cooldown'):
            last_rob = datetime.fromisoformat(robber_data['rob_cooldown'])
            if now - last_rob < timedelta(hours=2):
                remaining = timedelta(hours=2) - (now - last_rob)
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(f"⏰ Você já roubou recentemente! Espere {hours}h {minutes}m")
                return
        
        # Verifica se o alvo tem dinheiro suficiente
        if target_data['money'] < 50:
            await ctx.send(f"💸 {member.display_name} está muito pobre para ser roubado! (mín. $50)")
            return
        
        # Chances de sucesso
        base_chance = 0.35
        if is_vip(ctx.author.id):
            base_chance += 0.15  # VIP tem mais chance
        
        # Se o alvo é VIP, é mais difícil roubar
        if is_vip(member.id):
            base_chance -= 0.10
        
        success = random.random() < base_chance
        
        if success:
            # Roubo bem-sucedido
            max_steal = min(target_data['money'] // 3, 500)  # Max 1/3 do dinheiro ou $500
            stolen_amount = random.randint(25, max_steal)
            
            target_data['money'] -= stolen_amount
            robber_data['money'] += stolen_amount
            robber_data['rob_cooldown'] = now.isoformat()
            
            embed = discord.Embed(title="💰 Roubo Bem-sucedido!", 
                                 description=f"{ctx.author.mention} roubou ${stolen_amount} de {member.mention}!", 
                                 color=0x00ff00)
            
            # Chance de ganhar XP no roubo
            if await add_xp(ctx.author.id, random.randint(10, 20)):
                embed.add_field(name="🎉 Level Up!", value=f"Você chegou ao level {robber_data['level']}!", inline=False)
        else:
            # Roubo falhou - ladrão perde dinheiro
            penalty = random.randint(50, 150)
            penalty = min(penalty, robber_data['money'])
            
            robber_data['money'] -= penalty
            robber_data['rob_cooldown'] = now.isoformat()
            
            embed = discord.Embed(title="🚨 Roubo Falhou!", 
                                 description=f"{ctx.author.mention} foi pego tentando roubar {member.mention} e perdeu ${penalty}!", 
                                 color=0xff0000)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='loteria', aliases=['lottery', 'loto'])
    async def lottery(self, ctx, *numbers):
        ticket_price = 100
        user_data = get_user_data(ctx.author.id)
        
        if user_data['money'] < ticket_price:
            await ctx.send(f"❌ Você precisa de ${ticket_price} para comprar um bilhete da loteria!")
            return
        
        # Se não forneceu números, gera aleatoriamente
        if not numbers:
            user_numbers = [random.randint(1, 50) for _ in range(6)]
        else:
            try:
                user_numbers = [int(num) for num in numbers[:6]]
                if len(user_numbers) != 6:
                    await ctx.send("❌ Você deve escolher exatamente 6 números de 1 a 50!")
                    return
                if any(num < 1 or num > 50 for num in user_numbers):
                    await ctx.send("❌ Os números devem estar entre 1 e 50!")
                    return
                if len(set(user_numbers)) != 6:
                    await ctx.send("❌ Não é possível repetir números!")
                    return
            except ValueError:
                await ctx.send("❌ Por favor, digite apenas números válidos!")
                return
        
        # Cobrar o bilhete
        user_data['money'] -= ticket_price
        
        # Gerar números sorteados
        winning_numbers = random.sample(range(1, 51), 6)
        
        # Verificar acertos
        matches = len(set(user_numbers) & set(winning_numbers))
        
        # Calcular prêmio
        prizes = {
            6: 10000,  # Sena
            5: 2000,   # Quina
            4: 500,    # Quadra
            3: 100,    # Terno
        }
        
        prize = prizes.get(matches, 0)
        
        embed = discord.Embed(title="🎲 Resultado da Loteria", color=0x9932cc)
        embed.add_field(name="Seus Números", value=" - ".join(map(str, sorted(user_numbers))), inline=False)
        embed.add_field(name="Números Sorteados", value=" - ".join(map(str, sorted(winning_numbers))), inline=False)
        embed.add_field(name="Acertos", value=f"{matches}/6", inline=True)
        
        if prize > 0:
            # Bônus VIP
            if is_vip(ctx.author.id):
                vip_bonus = int(prize * 0.25)
                prize += vip_bonus
                embed.add_field(name="Bônus VIP", value=f"+${vip_bonus}", inline=True)
            
            user_data['money'] += prize
            embed.add_field(name="🎉 Prêmio", value=f"${prize}", inline=True)
            embed.color = 0x00ff00
            
            # XP por ganhar na loteria
            if await add_xp(ctx.author.id, matches * 5):
                embed.add_field(name="🎉 Level Up!", value=f"Você chegou ao level {user_data['level']}!", inline=False)
        else:
            embed.add_field(name="😢 Prêmio", value="Mais sorte na próxima!", inline=True)
            embed.color = 0xff0000
        
        embed.set_footer(text=f"Bilhete custou ${ticket_price}")
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='loja', aliases=['shop'])
    async def shop(self, ctx):
        embed = discord.Embed(title="🛒 Loja do Servidor", color=0x0099ff)
        
        for emoji, item in data['shop']['items'].items():
            embed.add_field(
                name=f"{emoji} {item['name']} - ${item['price']}", 
                value=item['description'], 
                inline=False
            )
        
        embed.set_footer(text="Use !comprar <emoji> para comprar um item")
        await ctx.send(embed=embed)

    @commands.command(name='comprar', aliases=['buy'])
    async def buy(self, ctx, item_emoji: str):
        if item_emoji not in data['shop']['items']:
            await ctx.send("❌ Item não encontrado na loja!")
            return
        
        user_data = get_user_data(ctx.author.id)
        item = data['shop']['items'][item_emoji]
        
        if user_data['money'] < item['price']:
            await ctx.send(f"❌ Você precisa de ${item['price']} para comprar {item['name']}!")
            return
        
        user_data['money'] -= item['price']
        
        if item_emoji not in user_data['inventory']:
            user_data['inventory'][item_emoji] = 0
        user_data['inventory'][item_emoji] += 1
        
        embed = discord.Embed(title="✅ Compra Realizada!", 
                             description=f"Você comprou {item_emoji} {item['name']} por ${item['price']}!", 
                             color=0x00ff00)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='inventario', aliases=['inv', 'inventory'])
    async def inventory(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        
        user_data = get_user_data(member.id)
        
        if not user_data['inventory']:
            await ctx.send(f"📦 {member.display_name} não possui itens no inventário!")
            return
        
        embed = discord.Embed(title=f"📦 Inventário de {member.display_name}", color=0x9932cc)
        
        for emoji, quantity in user_data['inventory'].items():
            item_name = data['shop']['items'].get(emoji, {}).get('name', 'Item Desconhecido')
            embed.add_field(name=f"{emoji} {item_name}", value=f"Quantidade: {quantity}", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='vender', aliases=['sell'])
    async def sell(self, ctx, item_emoji: str, quantity: int = 1):
        user_data = get_user_data(ctx.author.id)
        
        if item_emoji not in user_data['inventory'] or user_data['inventory'][item_emoji] < quantity:
            await ctx.send("❌ Você não possui este item em quantidade suficiente!")
            return
        
        if item_emoji not in data['shop']['items']:
            await ctx.send("❌ Este item não pode ser vendido!")
            return
        
        item = data['shop']['items'][item_emoji]
        sell_price = int(item['price'] * 0.7 * quantity)  # 70% do preço original
        
        user_data['inventory'][item_emoji] -= quantity
        if user_data['inventory'][item_emoji] == 0:
            del user_data['inventory'][item_emoji]
        
        user_data['money'] += sell_price
        
        embed = discord.Embed(title="💰 Item Vendido!", 
                             description=f"Você vendeu {quantity}x {item_emoji} {item['name']} por ${sell_price}!", 
                             color=0x00ff00)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='depositar', aliases=['dep'])
    async def deposit(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Valor inválido!")
            return
        
        user_data = get_user_data(ctx.author.id)
        if user_data['money'] < amount:
            await ctx.send("❌ Você não tem dinheiro suficiente!")
            return
        
        user_data['money'] -= amount
        user_data['bank'] += amount
        
        await ctx.send(f"✅ Você depositou ${amount} no banco!")
        save_data()

    @commands.command(name='sacar', aliases=['withdraw'])
    async def withdraw(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Valor inválido!")
            return
        
        user_data = get_user_data(ctx.author.id)
        if user_data['bank'] < amount:
            await ctx.send("❌ Você não tem dinheiro suficiente no banco!")
            return
        
        user_data['bank'] -= amount
        user_data['money'] += amount
        
        await ctx.send(f"✅ Você sacou ${amount} do banco!")
        save_data()

    # COMANDOS VIP (apenas admins)

    @commands.command(name='setvip')
    @commands.has_permissions(administrator=True)
    async def set_vip(self, ctx, member: discord.Member, days: int):
        if days <= 0:
            await ctx.send("❌ Número de dias inválido!")
            return
        
        expire_date = datetime.now() + timedelta(days=days)
        data['vip'][str(member.id)] = {
            'expires': expire_date.isoformat(),
            'granted_by': ctx.author.id
        }
        
        embed = discord.Embed(title="👑 VIP Concedido!", 
                             description=f"{member.mention} agora é VIP por {days} dias!", 
                             color=0xffd700)
        embed.add_field(name="Expira em", value=expire_date.strftime("%d/%m/%Y %H:%M"), inline=False)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='removervip')
    @commands.has_permissions(administrator=True)
    async def remove_vip(self, ctx, member: discord.Member):
        if str(member.id) not in data['vip']:
            await ctx.send("❌ Este usuário não é VIP!")
            return
        
        del data['vip'][str(member.id)]
        
        embed = discord.Embed(title="👑 VIP Removido!", 
                             description=f"VIP de {member.mention} foi removido!", 
                             color=0xff0000)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='listvip')
    @commands.has_permissions(administrator=True)
    async def list_vip(self, ctx):
        if not data['vip']:
            await ctx.send("📋 Nenhum usuário VIP encontrado!")
            return
        
        embed = discord.Embed(title="👑 Lista de VIPs", color=0xffd700)
        
        for user_id, vip_data in data['vip'].items():
            try:
                user = self.bot.get_user(int(user_id))
                expires = datetime.fromisoformat(vip_data['expires'])
                embed.add_field(
                    name=f"{user.display_name if user else 'Usuário Desconhecido'}", 
                    value=f"Expira: {expires.strftime('%d/%m/%Y %H:%M')}", 
                    inline=False
                )
            except:
                continue
        
        await ctx.send(embed=embed)

    @commands.command(name='additem')
    @commands.has_permissions(administrator=True)
    async def add_item(self, ctx, emoji: str, price: int, *, name_description: str):
        parts = name_description.split(' - ', 1)
        if len(parts) != 2:
            await ctx.send("❌ Formato: !additem <emoji> <preço> <nome> - <descrição>")
            return
        
        name, description = parts
        data['shop']['items'][emoji] = {
            'name': name.strip(),
            'price': price,
            'description': description.strip()
        }
        
        embed = discord.Embed(title="✅ Item Adicionado!", 
                             description=f"{emoji} {name} foi adicionado à loja por ${price}!", 
                             color=0x00ff00)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='removeitem')
    @commands.has_permissions(administrator=True)
    async def remove_item(self, ctx, emoji: str):
        if emoji not in data['shop']['items']:
            await ctx.send("❌ Item não encontrado na loja!")
            return
        
        item_name = data['shop']['items'][emoji]['name']
        del data['shop']['items'][emoji]
        
        embed = discord.Embed(title="✅ Item Removido!", 
                             description=f"{emoji} {item_name} foi removido da loja!", 
                             color=0xff0000)
        
        save_data()
        await ctx.send(embed=embed)

    @commands.command(name='dar', aliases=['give'])
    @commands.has_permissions(administrator=True)
    async def give_money(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send("❌ Valor inválido!")
            return
        
        user_data = get_user_data(member.id)
        user_data['money'] += amount
        
        embed = discord.Embed(title="💰 Dinheiro Concedido!", 
                             description=f"{member.mention} recebeu ${amount}!", 
                             color=0x00ff00)
        
        save_data()
        await ctx.send(embed=embed)

    # Comando de ajuda personalizado
    @commands.command(name='economia', aliases=['eco'])
    async def economy_help(self, ctx):
        embed = discord.Embed(title="💰 Sistema de Economia", color=0x0099ff)
        
        embed.add_field(name="💵 Comandos Básicos", 
                        value="`!saldo` - Ver seu saldo\n`!daily` - Recompensa diária\n`!work` - Trabalhar por dinheiro", 
                        inline=False)
        
        embed.add_field(name="🛒 Loja", 
                        value="`!loja` - Ver itens\n`!comprar <emoji>` - Comprar item\n`!vender <emoji> [qtd]` - Vender item", 
                        inline=False)
        
        embed.add_field(name="🏦 Banco", 
                        value="`!depositar <valor>` - Depositar no banco\n`!sacar <valor>` - Sacar do banco", 
                        inline=False)
        
        embed.add_field(name="🎰 Diversão", 
                        value="`!apostar <valor>` - Apostar dinheiro\n`!roubar @usuário` - Tentar roubar alguém\n`!loteria [números]` - Jogar na loteria\n`!inventario` - Ver seus itens", 
                        inline=False)
        
        embed.add_field(name="👑 Benefícios VIP", 
                        value="• Bônus de 50% no daily\n• Bônus de 50% no work\n• Maior chance nas apostas", 
                        inline=False)
        
        await ctx.send(embed=embed)

# Função setup necessária para cogs
async def setup(bot):
    await bot.add_cog(Economy(bot))