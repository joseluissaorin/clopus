# CLI Tool Template

A modern command-line interface tool built with TypeScript.

## Features

- **Commander.js** - Command and option parsing
- **Inquirer.js** - Interactive prompts
- **Chalk** - Colored terminal output
- **Ora** - Elegant spinners
- **Configstore** - Persistent configuration
- **TypeScript** - Type safety

## Project Structure

```
{{PROJECT_NAME}}/
├── src/
│   ├── index.ts                # Entry point
│   ├── cli.ts                  # CLI setup
│   ├── commands/               # Command implementations
│   │   ├── init.ts
│   │   ├── create.ts
│   │   └── config.ts
│   ├── lib/
│   │   ├── config.ts           # Configuration manager
│   │   ├── logger.ts           # Logging utilities
│   │   └── utils.ts            # Helper functions
│   └── types/
│       └── index.ts
├── bin/
│   └── {{BIN_NAME}}            # Executable entry
├── tests/
│   └── commands.test.ts
├── package.json
├── tsconfig.json
└── README.md
```

## Setup

```bash
# Create directory
mkdir {{PROJECT_NAME}}
cd {{PROJECT_NAME}}

# Initialize npm
npm init -y

# Install dependencies
npm install commander inquirer chalk ora configstore
npm install -D typescript @types/node @types/inquirer vitest

# Initialize TypeScript
npx tsc --init
```

## Configuration

### package.json

```json
{
  "name": "{{PROJECT_NAME}}",
  "version": "1.0.0",
  "description": "{{DESCRIPTION}}",
  "bin": {
    "{{BIN_NAME}}": "./bin/{{BIN_NAME}}"
  },
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc -w",
    "start": "node dist/index.js",
    "test": "vitest",
    "link": "npm run build && npm link"
  },
  "engines": {
    "node": ">=18"
  }
}
```

### bin/{{BIN_NAME}}

```bash
#!/usr/bin/env node
require('../dist/index.js');
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

## Implementation

### Entry Point

```typescript
// src/index.ts
import { cli } from './cli';

cli.parse(process.argv);
```

### CLI Setup

```typescript
// src/cli.ts
import { Command } from 'commander';
import { initCommand } from './commands/init';
import { createCommand } from './commands/create';
import { configCommand } from './commands/config';

export const cli = new Command()
  .name('{{BIN_NAME}}')
  .description('{{DESCRIPTION}}')
  .version('1.0.0');

cli
  .command('init')
  .description('Initialize a new project')
  .option('-t, --template <name>', 'Template to use', 'default')
  .action(initCommand);

cli
  .command('create <name>')
  .description('Create a new resource')
  .option('-f, --force', 'Overwrite existing files')
  .action(createCommand);

cli
  .command('config')
  .description('Manage configuration')
  .option('--get <key>', 'Get a config value')
  .option('--set <key=value>', 'Set a config value')
  .action(configCommand);
```

### Command Implementation

```typescript
// src/commands/init.ts
import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import { logger } from '../lib/logger';

interface InitOptions {
  template: string;
}

export async function initCommand(options: InitOptions) {
  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'projectName',
      message: 'Project name:',
      default: 'my-project',
    },
    {
      type: 'list',
      name: 'language',
      message: 'Select language:',
      choices: ['TypeScript', 'JavaScript'],
    },
    {
      type: 'confirm',
      name: 'useGit',
      message: 'Initialize git repository?',
      default: true,
    },
  ]);

  const spinner = ora('Creating project...').start();

  try {
    // Create project logic here
    await createProject(answers);

    spinner.succeed(chalk.green('Project created successfully!'));

    logger.info(`\nNext steps:`);
    logger.info(`  cd ${answers.projectName}`);
    logger.info(`  npm install`);
    logger.info(`  npm run dev`);
  } catch (error) {
    spinner.fail(chalk.red('Failed to create project'));
    logger.error(error);
    process.exit(1);
  }
}
```

### Logger Utility

```typescript
// src/lib/logger.ts
import chalk from 'chalk';

export const logger = {
  info: (message: string) => console.log(chalk.blue('ℹ'), message),
  success: (message: string) => console.log(chalk.green('✓'), message),
  warn: (message: string) => console.log(chalk.yellow('⚠'), message),
  error: (message: string) => console.log(chalk.red('✗'), message),
  debug: (message: string) => {
    if (process.env.DEBUG) {
      console.log(chalk.gray('[debug]'), message);
    }
  },
};
```

### Configuration Manager

```typescript
// src/lib/config.ts
import Configstore from 'configstore';

const config = new Configstore('{{BIN_NAME}}', {
  defaultTemplate: 'typescript',
  gitInit: true,
});

export const configManager = {
  get: (key: string) => config.get(key),
  set: (key: string, value: unknown) => config.set(key, value),
  getAll: () => config.all,
  delete: (key: string) => config.delete(key),
  clear: () => config.clear(),
};
```

## Testing

```typescript
// tests/commands.test.ts
import { describe, it, expect, vi } from 'vitest';
import { initCommand } from '../src/commands/init';

vi.mock('inquirer', () => ({
  default: {
    prompt: vi.fn().mockResolvedValue({
      projectName: 'test-project',
      language: 'TypeScript',
      useGit: true,
    }),
  },
}));

describe('init command', () => {
  it('creates project with provided options', async () => {
    await initCommand({ template: 'default' });
    // Assert project creation
  });
});
```

## Development

```bash
# Build and link globally
npm run link

# Now use the CLI
{{BIN_NAME}} --help
{{BIN_NAME}} init
{{BIN_NAME}} create my-resource
```

## Publishing

```bash
# Build
npm run build

# Publish to npm
npm publish
```

## Best Practices

1. **Provide helpful --help output** - Clear descriptions for all commands
2. **Use spinners for async operations** - Visual feedback
3. **Color code output** - Success (green), errors (red), warnings (yellow)
4. **Support both flags and prompts** - CLI flags for automation, prompts for interactive use
5. **Validate input** - Check required args before proceeding
6. **Graceful error handling** - Catch errors, show helpful messages
7. **Exit codes** - Return non-zero on error for scripting
