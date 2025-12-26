---
name: discord-bot
description: Discord bot development
version: 1.0.0
category: communication
technologies: [discord.js, discord.py, python, node]
triggers:
  - discord bot
  - discord
  - discord.js
  - discord.py
---

# Discord Bot Development

Discord bot development with discord.js or discord.py.

## discord.js (Node.js)

### Setup

```bash
npm init -y
npm install discord.js
```

### Basic Bot

```javascript
const { Client, GatewayIntentBits, SlashCommandBuilder } = require('discord.js');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ]
});

client.once('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
});

// Slash command
client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;

  if (interaction.commandName === 'ping') {
    await interaction.reply('Pong!');
  }
});

// Message event
client.on('messageCreate', (message) => {
  if (message.author.bot) return;

  if (message.content === '!hello') {
    message.reply('Hello there!');
  }
});

client.login(process.env.DISCORD_TOKEN);
```

### Register Slash Commands

```javascript
const { REST, Routes } = require('discord.js');

const commands = [
  new SlashCommandBuilder()
    .setName('ping')
    .setDescription('Replies with Pong!'),
  new SlashCommandBuilder()
    .setName('user')
    .setDescription('Get user info')
    .addUserOption(option =>
      option.setName('target').setDescription('The user').setRequired(true)
    ),
];

const rest = new REST().setToken(process.env.DISCORD_TOKEN);

(async () => {
  await rest.put(
    Routes.applicationCommands(CLIENT_ID),
    { body: commands.map(cmd => cmd.toJSON()) },
  );
})();
```

## discord.py (Python)

### Setup

```bash
pip install discord.py
```

### Basic Bot

```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello, {ctx.author.name}!')

@bot.tree.command(name='ping', description='Replies with Pong!')
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('Pong!')

@bot.tree.command(name='embed', description='Send an embed')
async def embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

bot.run(os.environ['DISCORD_TOKEN'])
```

## Project Structure

```
bot/
├── src/
│   ├── index.js
│   ├── commands/
│   │   ├── ping.js
│   │   └── user.js
│   ├── events/
│   │   ├── ready.js
│   │   └── messageCreate.js
│   └── utils/
├── config.json
└── package.json
```

## Best Practices

1. Use slash commands (required for verified bots)
2. Handle rate limits gracefully
3. Use embeds for rich messages
4. Implement proper error handling
5. Use environment variables for tokens
6. Add proper intents
7. Test in a development server
