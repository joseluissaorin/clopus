/**
 * CLOPUS MCP Server - OpenAI
 * Provides OpenAI API operations for comparison and fallback
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const server = new Server(
  { name: "clopus-openai", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "chat_completion",
      description: "Generate a chat completion using GPT models",
      inputSchema: {
        type: "object",
        properties: {
          messages: {
            type: "array",
            items: {
              type: "object",
              properties: {
                role: { type: "string", enum: ["system", "user", "assistant"] },
                content: { type: "string" },
              },
            },
            description: "Chat messages",
          },
          model: { type: "string", description: "Model to use (default: gpt-4o)" },
          temperature: { type: "number", description: "Temperature (0-2)" },
          max_tokens: { type: "number", description: "Max tokens to generate" },
        },
        required: ["messages"],
      },
    },
    {
      name: "create_embedding",
      description: "Create text embeddings",
      inputSchema: {
        type: "object",
        properties: {
          input: { type: "string", description: "Text to embed" },
          model: { type: "string", description: "Embedding model (default: text-embedding-3-small)" },
        },
        required: ["input"],
      },
    },
    {
      name: "create_image",
      description: "Generate an image using DALL-E",
      inputSchema: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Image description" },
          model: { type: "string", description: "Model (dall-e-2, dall-e-3)" },
          size: { type: "string", description: "Image size (1024x1024, 1792x1024, etc.)" },
          quality: { type: "string", description: "Quality (standard, hd)" },
          n: { type: "number", description: "Number of images" },
        },
        required: ["prompt"],
      },
    },
    {
      name: "transcribe_audio",
      description: "Transcribe audio using Whisper",
      inputSchema: {
        type: "object",
        properties: {
          file_path: { type: "string", description: "Path to audio file" },
          language: { type: "string", description: "Language code" },
          prompt: { type: "string", description: "Optional prompt to guide transcription" },
        },
        required: ["file_path"],
      },
    },
    {
      name: "text_to_speech",
      description: "Convert text to speech",
      inputSchema: {
        type: "object",
        properties: {
          input: { type: "string", description: "Text to convert" },
          voice: { type: "string", description: "Voice (alloy, echo, fable, onyx, nova, shimmer)" },
          model: { type: "string", description: "Model (tts-1, tts-1-hd)" },
          output_path: { type: "string", description: "Output file path" },
        },
        required: ["input", "output_path"],
      },
    },
    {
      name: "moderate_content",
      description: "Check content for policy violations",
      inputSchema: {
        type: "object",
        properties: {
          input: { type: "string", description: "Content to moderate" },
        },
        required: ["input"],
      },
    },
    {
      name: "list_models",
      description: "List available OpenAI models",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "analyze_image",
      description: "Analyze an image using GPT-4 Vision",
      inputSchema: {
        type: "object",
        properties: {
          image_url: { type: "string", description: "URL of the image" },
          prompt: { type: "string", description: "Question about the image" },
        },
        required: ["image_url", "prompt"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "chat_completion": {
        const completion = await openai.chat.completions.create({
          model: (args.model as string) || "gpt-4o",
          messages: args.messages as any[],
          temperature: args.temperature as number,
          max_tokens: args.max_tokens as number,
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  content: completion.choices[0]?.message?.content,
                  usage: completion.usage,
                  model: completion.model,
                },
                null,
                2
              ),
            },
          ],
        };
      }

      case "create_embedding": {
        const embedding = await openai.embeddings.create({
          model: (args.model as string) || "text-embedding-3-small",
          input: args.input as string,
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  embedding: embedding.data[0].embedding.slice(0, 10).concat(["..."]),
                  dimensions: embedding.data[0].embedding.length,
                  usage: embedding.usage,
                },
                null,
                2
              ),
            },
          ],
        };
      }

      case "create_image": {
        const image = await openai.images.generate({
          model: (args.model as string) || "dall-e-3",
          prompt: args.prompt as string,
          size: (args.size as any) || "1024x1024",
          quality: (args.quality as any) || "standard",
          n: (args.n as number) || 1,
        });
        return { content: [{ type: "text", text: JSON.stringify(image.data, null, 2) }] };
      }

      case "transcribe_audio": {
        const fs = await import("fs");
        const file = fs.createReadStream(args.file_path as string);
        const transcription = await openai.audio.transcriptions.create({
          file: file as any,
          model: "whisper-1",
          language: args.language as string,
          prompt: args.prompt as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(transcription, null, 2) }] };
      }

      case "text_to_speech": {
        const fs = await import("fs");
        const response = await openai.audio.speech.create({
          model: (args.model as string) || "tts-1",
          voice: (args.voice as any) || "alloy",
          input: args.input as string,
        });
        const buffer = Buffer.from(await response.arrayBuffer());
        fs.writeFileSync(args.output_path as string, buffer);
        return { content: [{ type: "text", text: `Audio saved to ${args.output_path}` }] };
      }

      case "moderate_content": {
        const moderation = await openai.moderations.create({
          input: args.input as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(moderation.results, null, 2) }] };
      }

      case "list_models": {
        const models = await openai.models.list();
        const modelList = models.data.map((m) => ({ id: m.id, created: m.created }));
        return { content: [{ type: "text", text: JSON.stringify(modelList, null, 2) }] };
      }

      case "analyze_image": {
        const response = await openai.chat.completions.create({
          model: "gpt-4o",
          messages: [
            {
              role: "user",
              content: [
                { type: "text", text: args.prompt as string },
                { type: "image_url", image_url: { url: args.image_url as string } },
              ],
            },
          ],
        });
        return {
          content: [{ type: "text", text: response.choices[0]?.message?.content || "" }],
        };
      }

      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return { content: [{ type: "text", text: `Error: ${message}` }], isError: true };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("CLOPUS OpenAI MCP server running");
}

main().catch(console.error);
