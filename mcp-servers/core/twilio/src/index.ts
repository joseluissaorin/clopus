/**
 * CLOPUS MCP Server - Twilio
 * Provides SMS and voice capabilities via Twilio API
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import Twilio from "twilio";

const accountSid = process.env.TWILIO_ACCOUNT_SID || "";
const authToken = process.env.TWILIO_AUTH_TOKEN || "";
const twilioPhone = process.env.TWILIO_PHONE_NUMBER || "";

const client = Twilio(accountSid, authToken);

const server = new Server(
  { name: "clopus-twilio", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_sms",
      description: "Send an SMS message",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient phone number (E.164 format)" },
          body: { type: "string", description: "Message body" },
          from: { type: "string", description: "Sender phone number (optional, uses default)" },
        },
        required: ["to", "body"],
      },
    },
    {
      name: "send_whatsapp",
      description: "Send a WhatsApp message",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient WhatsApp number" },
          body: { type: "string", description: "Message body" },
        },
        required: ["to", "body"],
      },
    },
    {
      name: "make_call",
      description: "Initiate a voice call",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient phone number" },
          twiml: { type: "string", description: "TwiML instructions for the call" },
          url: { type: "string", description: "URL returning TwiML" },
        },
        required: ["to"],
      },
    },
    {
      name: "list_messages",
      description: "List recent messages",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Number of messages to return" },
          to: { type: "string", description: "Filter by recipient" },
          from: { type: "string", description: "Filter by sender" },
        },
      },
    },
    {
      name: "get_message",
      description: "Get details of a specific message",
      inputSchema: {
        type: "object",
        properties: {
          message_sid: { type: "string", description: "Message SID" },
        },
        required: ["message_sid"],
      },
    },
    {
      name: "list_calls",
      description: "List recent calls",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Number of calls to return" },
          to: { type: "string", description: "Filter by recipient" },
          from: { type: "string", description: "Filter by caller" },
        },
      },
    },
    {
      name: "lookup_phone",
      description: "Look up information about a phone number",
      inputSchema: {
        type: "object",
        properties: {
          phone_number: { type: "string", description: "Phone number to look up" },
          type: { type: "string", description: "Type of lookup (carrier, caller-name)" },
        },
        required: ["phone_number"],
      },
    },
    {
      name: "verify_start",
      description: "Start a phone verification (send code)",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Phone number to verify" },
          channel: { type: "string", description: "Verification channel (sms, call)" },
          service_sid: { type: "string", description: "Verify service SID" },
        },
        required: ["to", "channel", "service_sid"],
      },
    },
    {
      name: "verify_check",
      description: "Check a verification code",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Phone number being verified" },
          code: { type: "string", description: "Verification code" },
          service_sid: { type: "string", description: "Verify service SID" },
        },
        required: ["to", "code", "service_sid"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "send_sms": {
        const message = await client.messages.create({
          to: args.to as string,
          from: (args.from as string) || twilioPhone,
          body: args.body as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(message, null, 2) }] };
      }

      case "send_whatsapp": {
        const message = await client.messages.create({
          to: `whatsapp:${args.to}`,
          from: `whatsapp:${twilioPhone}`,
          body: args.body as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(message, null, 2) }] };
      }

      case "make_call": {
        const callParams: any = {
          to: args.to as string,
          from: twilioPhone,
        };
        if (args.twiml) {
          callParams.twiml = args.twiml;
        } else if (args.url) {
          callParams.url = args.url;
        } else {
          callParams.twiml = "<Response><Say>Hello from CLOPUS!</Say></Response>";
        }
        const call = await client.calls.create(callParams);
        return { content: [{ type: "text", text: JSON.stringify(call, null, 2) }] };
      }

      case "list_messages": {
        const messages = await client.messages.list({
          limit: (args.limit as number) || 20,
          to: args.to as string,
          from: args.from as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(messages, null, 2) }] };
      }

      case "get_message": {
        const message = await client.messages(args.message_sid as string).fetch();
        return { content: [{ type: "text", text: JSON.stringify(message, null, 2) }] };
      }

      case "list_calls": {
        const calls = await client.calls.list({
          limit: (args.limit as number) || 20,
          to: args.to as string,
          from: args.from as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(calls, null, 2) }] };
      }

      case "lookup_phone": {
        const lookup = await client.lookups.v2.phoneNumbers(args.phone_number as string).fetch();
        return { content: [{ type: "text", text: JSON.stringify(lookup, null, 2) }] };
      }

      case "verify_start": {
        const verification = await client.verify.v2
          .services(args.service_sid as string)
          .verifications.create({
            to: args.to as string,
            channel: args.channel as string,
          });
        return { content: [{ type: "text", text: JSON.stringify(verification, null, 2) }] };
      }

      case "verify_check": {
        const check = await client.verify.v2
          .services(args.service_sid as string)
          .verificationChecks.create({
            to: args.to as string,
            code: args.code as string,
          });
        return { content: [{ type: "text", text: JSON.stringify(check, null, 2) }] };
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
  console.error("CLOPUS Twilio MCP server running");
}

main().catch(console.error);
