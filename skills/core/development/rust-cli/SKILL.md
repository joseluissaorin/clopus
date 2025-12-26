---
name: rust-cli
description: Rust CLI application development
version: 1.0.0
category: development
technologies: [rust, clap, tokio]
triggers:
  - rust cli
  - rust command line
  - rust tool
---

# Rust CLI Development

High-performance Rust CLI application development.

## Capabilities

- Argument parsing with clap
- Async runtime with tokio
- Error handling with anyhow/thiserror
- Configuration with config-rs
- Colored output
- Progress bars
- File I/O
- Testing

## Project Structure

```
project/
├── src/
│   ├── main.rs
│   ├── lib.rs
│   ├── cli.rs
│   ├── commands/
│   │   ├── mod.rs
│   │   └── {command}.rs
│   ├── config.rs
│   └── error.rs
├── tests/
├── Cargo.toml
└── README.md
```

## Setup

```toml
# Cargo.toml
[package]
name = "mycli"
version = "0.1.0"
edition = "2021"

[dependencies]
clap = { version = "4", features = ["derive"] }
tokio = { version = "1", features = ["full"] }
anyhow = "1"
thiserror = "1"
serde = { version = "1", features = ["derive"] }
colored = "2"
indicatif = "0.17"
```

## CLI Pattern

```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "mycli")]
#[command(about = "My awesome CLI tool")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    #[arg(short, long, global = true)]
    verbose: bool,
}

#[derive(Subcommand)]
enum Commands {
    Init { name: String },
    Build { #[arg(short, long)] release: bool },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Init { name } => init(&name).await?,
        Commands::Build { release } => build(release).await?,
    }

    Ok(())
}
```

## Best Practices

1. Use derive macros for clap
2. Use anyhow for application errors
3. Use thiserror for library errors
4. Provide helpful error messages
5. Support --verbose and --quiet flags
6. Use colored output sparingly
7. Write integration tests
