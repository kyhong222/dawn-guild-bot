export default {
    name: 'ready',
    once: true,
    execute(client) {
        console.log(`🌅 새벽 길드봇이 준비되었습니다! (${client.user.tag})`);
        console.log(`📊 ${client.guilds.cache.size}개 서버에서 활동 중`);
        
        // 봇 상태 설정
        client.user.setActivity('메이플랜드 새벽 길드', { type: 'WATCHING' });
    }
};