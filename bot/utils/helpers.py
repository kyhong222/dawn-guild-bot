"""
유틸리티 함수들
"""
import discord
import asyncio
from typing import Optional, List
from bot.config.settings import BOT_COLOR

async def send_embed_message(
    ctx,
    title: str,
    description: str = "",
    color: int = BOT_COLOR,
    fields: List[dict] = None,
    footer: str = None,
    thumbnail_url: str = None
) -> discord.Message:
    """임베드 메시지를 쉽게 전송하는 헬퍼 함수"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=ctx.message.created_at
    )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', ''),
                value=field.get('value', ''),
                inline=field.get('inline', True)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    return await ctx.send(embed=embed)

async def confirm_action(ctx, message: str, timeout: int = 30) -> bool:
    """사용자 확인을 받는 함수"""
    embed = discord.Embed(
        title="⚠️ 확인 필요",
        description=f"{message}\n\n✅ 계속하려면 '예'\n❌ 취소하려면 '아니오'",
        color=0xFFCC02
    )
    
    confirm_msg = await ctx.send(embed=embed)
    
    def check(m):
        return (
            m.author == ctx.author and 
            m.channel == ctx.channel and 
            m.content.lower() in ['예', 'yes', 'y', '아니오', 'no', 'n']
        )
    
    try:
        response = await ctx.bot.wait_for('message', check=check, timeout=timeout)
        return response.content.lower() in ['예', 'yes', 'y']
    except asyncio.TimeoutError:
        await confirm_msg.edit(
            embed=discord.Embed(
                title="⏰ 시간 초과",
                description="확인 시간이 초과되어 작업이 취소되었습니다.",
                color=0xFF3333
            )
        )
        return False

def format_time_korean(seconds: int) -> str:
    """초를 한국어 시간 형식으로 변환"""
    if seconds < 60:
        return f"{seconds}초"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds:
            return f"{minutes}분 {remaining_seconds}초"
        return f"{minutes}분"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes:
            return f"{hours}시간 {remaining_minutes}분"
        return f"{hours}시간"

def is_admin(ctx) -> bool:
    """관리자 권한 확인"""
    return (
        ctx.author.guild_permissions.administrator or
        ctx.author.guild_permissions.manage_guild or
        ctx.author.id == ctx.guild.owner_id
    )

async def paginate_list(
    ctx, 
    items: List[str], 
    title: str, 
    items_per_page: int = 10
) -> None:
    """긴 리스트를 페이지네이션으로 표시"""
    if not items:
        await send_embed_message(ctx, title, "표시할 항목이 없습니다.")
        return
    
    pages = [items[i:i + items_per_page] for i in range(0, len(items), items_per_page)]
    current_page = 0
    
    def create_embed(page_num: int) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description="\n".join(pages[page_num]),
            color=BOT_COLOR
        )
        embed.set_footer(text=f"페이지 {page_num + 1}/{len(pages)}")
        return embed
    
    if len(pages) == 1:
        await ctx.send(embed=create_embed(0))
        return
    
    message = await ctx.send(embed=create_embed(current_page))
    
    # 페이지네이션 버튼 추가
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")
    
    def check(reaction, user):
        return (
            user == ctx.author and 
            str(reaction.emoji) in ["⬅️", "➡️"] and 
            reaction.message.id == message.id
        )
    
    while True:
        try:
            reaction, user = await ctx.bot.wait_for(
                'reaction_add', timeout=60.0, check=check
            )
            
            if str(reaction.emoji) == "➡️" and current_page < len(pages) - 1:
                current_page += 1
                await message.edit(embed=create_embed(current_page))
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=create_embed(current_page))
            
            # 사용자 반응 제거
            await message.remove_reaction(reaction, user)
            
        except asyncio.TimeoutError:
            # 타임아웃 시 모든 반응 제거
            await message.clear_reactions()
            break