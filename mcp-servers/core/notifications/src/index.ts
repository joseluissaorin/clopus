/**
 * CLOPUS MCP Server - Notifications
 * Provides push notification capabilities via Firebase, OneSignal, etc.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Firebase Admin SDK setup
let firebaseApp: any = null;
let firebaseMessaging: any = null;

async function initFirebase() {
  if (firebaseApp) return;

  try {
    const admin = await import("firebase-admin");
    const serviceAccount = process.env.FIREBASE_SERVICE_ACCOUNT
      ? JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT)
      : null;

    if (serviceAccount) {
      firebaseApp = admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
      });
      firebaseMessaging = admin.messaging();
    }
  } catch (error) {
    console.error("Firebase initialization failed:", error);
  }
}

// OneSignal configuration
const oneSignalAppId = process.env.ONESIGNAL_APP_ID;
const oneSignalApiKey = process.env.ONESIGNAL_API_KEY;

const server = new Server(
  { name: "clopus-notifications", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_firebase_notification",
      description: "Send a push notification via Firebase Cloud Messaging",
      inputSchema: {
        type: "object",
        properties: {
          token: { type: "string", description: "FCM device token" },
          title: { type: "string", description: "Notification title" },
          body: { type: "string", description: "Notification body" },
          data: { type: "object", description: "Additional data payload" },
          image: { type: "string", description: "Image URL" },
        },
        required: ["token", "title", "body"],
      },
    },
    {
      name: "send_firebase_topic",
      description: "Send notification to a Firebase topic",
      inputSchema: {
        type: "object",
        properties: {
          topic: { type: "string", description: "Topic name" },
          title: { type: "string", description: "Notification title" },
          body: { type: "string", description: "Notification body" },
          data: { type: "object", description: "Additional data payload" },
        },
        required: ["topic", "title", "body"],
      },
    },
    {
      name: "send_firebase_multicast",
      description: "Send notification to multiple devices",
      inputSchema: {
        type: "object",
        properties: {
          tokens: { type: "array", items: { type: "string" }, description: "FCM device tokens" },
          title: { type: "string", description: "Notification title" },
          body: { type: "string", description: "Notification body" },
          data: { type: "object", description: "Additional data payload" },
        },
        required: ["tokens", "title", "body"],
      },
    },
    {
      name: "subscribe_to_topic",
      description: "Subscribe tokens to a Firebase topic",
      inputSchema: {
        type: "object",
        properties: {
          tokens: { type: "array", items: { type: "string" }, description: "Device tokens" },
          topic: { type: "string", description: "Topic name" },
        },
        required: ["tokens", "topic"],
      },
    },
    {
      name: "unsubscribe_from_topic",
      description: "Unsubscribe tokens from a Firebase topic",
      inputSchema: {
        type: "object",
        properties: {
          tokens: { type: "array", items: { type: "string" }, description: "Device tokens" },
          topic: { type: "string", description: "Topic name" },
        },
        required: ["tokens", "topic"],
      },
    },
    {
      name: "send_onesignal_notification",
      description: "Send a push notification via OneSignal",
      inputSchema: {
        type: "object",
        properties: {
          player_ids: { type: "array", items: { type: "string" }, description: "Player IDs" },
          headings: { type: "object", description: "Notification titles by language" },
          contents: { type: "object", description: "Notification body by language" },
          data: { type: "object", description: "Additional data" },
          url: { type: "string", description: "URL to open" },
        },
        required: ["contents"],
      },
    },
    {
      name: "send_onesignal_segment",
      description: "Send notification to OneSignal segments",
      inputSchema: {
        type: "object",
        properties: {
          segments: { type: "array", items: { type: "string" }, description: "Segment names" },
          headings: { type: "object", description: "Notification titles by language" },
          contents: { type: "object", description: "Notification body by language" },
          data: { type: "object", description: "Additional data" },
        },
        required: ["segments", "contents"],
      },
    },
    {
      name: "create_onesignal_segment",
      description: "Create a new OneSignal segment",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Segment name" },
          filters: { type: "array", description: "Segment filters" },
        },
        required: ["name", "filters"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "send_firebase_notification": {
        await initFirebase();
        if (!firebaseMessaging) {
          return { content: [{ type: "text", text: "Firebase not configured" }], isError: true };
        }

        const message = {
          token: args.token as string,
          notification: {
            title: args.title as string,
            body: args.body as string,
            imageUrl: args.image as string,
          },
          data: args.data as Record<string, string>,
        };

        const response = await firebaseMessaging.send(message);
        return { content: [{ type: "text", text: JSON.stringify({ messageId: response }, null, 2) }] };
      }

      case "send_firebase_topic": {
        await initFirebase();
        if (!firebaseMessaging) {
          return { content: [{ type: "text", text: "Firebase not configured" }], isError: true };
        }

        const message = {
          topic: args.topic as string,
          notification: {
            title: args.title as string,
            body: args.body as string,
          },
          data: args.data as Record<string, string>,
        };

        const response = await firebaseMessaging.send(message);
        return { content: [{ type: "text", text: JSON.stringify({ messageId: response }, null, 2) }] };
      }

      case "send_firebase_multicast": {
        await initFirebase();
        if (!firebaseMessaging) {
          return { content: [{ type: "text", text: "Firebase not configured" }], isError: true };
        }

        const message = {
          tokens: args.tokens as string[],
          notification: {
            title: args.title as string,
            body: args.body as string,
          },
          data: args.data as Record<string, string>,
        };

        const response = await firebaseMessaging.sendEachForMulticast(message);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  successCount: response.successCount,
                  failureCount: response.failureCount,
                },
                null,
                2
              ),
            },
          ],
        };
      }

      case "subscribe_to_topic": {
        await initFirebase();
        if (!firebaseMessaging) {
          return { content: [{ type: "text", text: "Firebase not configured" }], isError: true };
        }

        const response = await firebaseMessaging.subscribeToTopic(
          args.tokens as string[],
          args.topic as string
        );
        return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
      }

      case "unsubscribe_from_topic": {
        await initFirebase();
        if (!firebaseMessaging) {
          return { content: [{ type: "text", text: "Firebase not configured" }], isError: true };
        }

        const response = await firebaseMessaging.unsubscribeFromTopic(
          args.tokens as string[],
          args.topic as string
        );
        return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
      }

      case "send_onesignal_notification": {
        if (!oneSignalAppId || !oneSignalApiKey) {
          return { content: [{ type: "text", text: "OneSignal not configured" }], isError: true };
        }

        const payload: any = {
          app_id: oneSignalAppId,
          contents: args.contents,
          headings: args.headings,
          data: args.data,
          url: args.url,
        };

        if (args.player_ids) {
          payload.include_player_ids = args.player_ids;
        } else {
          payload.included_segments = ["All"];
        }

        const response = await fetch("https://onesignal.com/api/v1/notifications", {
          method: "POST",
          headers: {
            Authorization: `Basic ${oneSignalApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "send_onesignal_segment": {
        if (!oneSignalAppId || !oneSignalApiKey) {
          return { content: [{ type: "text", text: "OneSignal not configured" }], isError: true };
        }

        const payload = {
          app_id: oneSignalAppId,
          included_segments: args.segments,
          contents: args.contents,
          headings: args.headings,
          data: args.data,
        };

        const response = await fetch("https://onesignal.com/api/v1/notifications", {
          method: "POST",
          headers: {
            Authorization: `Basic ${oneSignalApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "create_onesignal_segment": {
        if (!oneSignalAppId || !oneSignalApiKey) {
          return { content: [{ type: "text", text: "OneSignal not configured" }], isError: true };
        }

        const payload = {
          name: args.name,
          filters: args.filters,
        };

        const response = await fetch(
          `https://onesignal.com/api/v1/apps/${oneSignalAppId}/segments`,
          {
            method: "POST",
            headers: {
              Authorization: `Basic ${oneSignalApiKey}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          }
        );

        const data = await response.json();
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
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
  console.error("CLOPUS Notifications MCP server running");
}

main().catch(console.error);
