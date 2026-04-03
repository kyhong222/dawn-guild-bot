export default {
    name: 'interactionCreate',
    async execute(interaction) {
        // 슬래시 커맨드가 아니면 무시
        if (!interaction.isChatInputCommand()) return;

        const command = interaction.client.commands.get(interaction.commandName);

        if (!command) {
            console.error(`❌ 알 수 없는 커맨드: ${interaction.commandName}`);
            return;
        }

        try {
            await command.execute(interaction);
        } catch (error) {
            console.error(`❌ 커맨드 실행 중 에러 (${interaction.commandName}):`, error);
            
            if (interaction.replied || interaction.deferred) {
                await interaction.followUp({ 
                    content: '커맨드 실행 중 오류가 발생했습니다! 😵', 
                    ephemeral: true 
                });
            } else {
                await interaction.reply({ 
                    content: '커맨드 실행 중 오류가 발생했습니다! 😵', 
                    ephemeral: true 
                });
            }
        }
    },
};