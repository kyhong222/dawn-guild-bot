import { SlashCommandBuilder } from 'discord.js';

export default {
    data: new SlashCommandBuilder()
        .setName('핑')
        .setDescription('봇의 응답 속도를 확인합니다'),
    
    async execute(interaction) {
        const sent = await interaction.reply({ 
            content: '🏓 퐁! 측정 중...', 
            fetchReply: true 
        });
        
        const roundtrip = sent.createdTimestamp - interaction.createdTimestamp;
        const apiLatency = Math.round(interaction.client.ws.ping);
        
        await interaction.editReply({
            content: `🏓 **퐁!**\n` +
                    `📡 API 지연시간: ${apiLatency}ms\n` +
                    `🔄 왕복 시간: ${roundtrip}ms`
        });
    },
};