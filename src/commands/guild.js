import { SlashCommandBuilder, EmbedBuilder } from 'discord.js';

export default {
    data: new SlashCommandBuilder()
        .setName('길드')
        .setDescription('새벽 길드 정보를 확인합니다'),
    
    async execute(interaction) {
        const embed = new EmbedBuilder()
            .setColor('#FF6B35') // 새벽 색상
            .setTitle('🌅 메이플랜드 새벽 길드')
            .setDescription('메이플랜드에서 활동하는 새벽 길드입니다!')
            .addFields(
                { name: '🎮 게임', value: '메이플랜드', inline: true },
                { name: '⏰ 활동시간', value: '새벽/밤', inline: true },
                { name: '👥 길드원', value: `${interaction.guild.memberCount}명`, inline: true }
            )
            .setTimestamp()
            .setFooter({ 
                text: '새벽 길드봇', 
                iconURL: interaction.client.user.displayAvatarURL() 
            });

        await interaction.reply({ embeds: [embed] });
    },
};