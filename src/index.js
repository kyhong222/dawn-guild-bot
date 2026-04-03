import { Client, Collection, GatewayIntentBits } from 'discord.js';
import { config } from 'dotenv';
import fs from 'fs';
import path from 'path';

// 환경변수 로드
config();

// Discord 클라이언트 생성
const client = new Client({ 
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ] 
});

// 커맨드 컬렉션
client.commands = new Collection();

// 커맨드 파일 로드
const commandsPath = path.join(process.cwd(), 'src', 'commands');
if (fs.existsSync(commandsPath)) {
    const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));
    
    for (const file of commandFiles) {
        const filePath = path.join(commandsPath, file);
        const command = await import(filePath);
        
        if ('data' in command.default && 'execute' in command.default) {
            client.commands.set(command.default.data.name, command.default);
            console.log(`✅ 커맨드 로드: ${command.default.data.name}`);
        } else {
            console.log(`⚠️ 커맨드 파일이 올바르지 않습니다: ${filePath}`);
        }
    }
}

// 이벤트 파일 로드
const eventsPath = path.join(process.cwd(), 'src', 'events');
if (fs.existsSync(eventsPath)) {
    const eventFiles = fs.readdirSync(eventsPath).filter(file => file.endsWith('.js'));
    
    for (const file of eventFiles) {
        const filePath = path.join(eventsPath, file);
        const event = await import(filePath);
        
        if (event.default.once) {
            client.once(event.default.name, (...args) => event.default.execute(...args));
        } else {
            client.on(event.default.name, (...args) => event.default.execute(...args));
        }
        console.log(`✅ 이벤트 로드: ${event.default.name}`);
    }
}

// 봇 로그인
client.login(process.env.DISCORD_TOKEN);