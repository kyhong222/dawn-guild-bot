import { REST, Routes } from 'discord.js';
import { config } from 'dotenv';
import fs from 'fs';
import path from 'path';

config();

const commands = [];
const commandsPath = path.join(process.cwd(), 'src', 'commands');
const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

// 모든 커맨드 파일에서 데이터 추출
for (const file of commandFiles) {
    const filePath = path.join(commandsPath, file);
    const command = await import(filePath);
    
    if ('data' in command.default && 'execute' in command.default) {
        commands.push(command.default.data.toJSON());
        console.log(`✅ 커맨드 발견: ${command.default.data.name}`);
    } else {
        console.log(`⚠️ 잘못된 커맨드 파일: ${filePath}`);
    }
}

// Discord API에 커맨드 등록
const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

try {
    console.log(`🚀 ${commands.length}개 슬래시 커맨드를 등록 중...`);

    // 길드별 커맨드 등록 (빠른 업데이트)
    const data = await rest.put(
        Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
        { body: commands },
    );

    console.log(`✅ ${data.length}개 슬래시 커맨드가 성공적으로 등록되었습니다!`);
} catch (error) {
    console.error('❌ 커맨드 등록 중 오류 발생:', error);
}