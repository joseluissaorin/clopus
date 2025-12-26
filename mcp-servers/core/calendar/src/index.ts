/**
 * CLOPUS MCP Server - Calendar
 * Provides Google Calendar operations
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { google, calendar_v3 } from "googleapis";

// OAuth2 client setup
const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  process.env.GOOGLE_REDIRECT_URI
);

// Set credentials if refresh token is available
if (process.env.GOOGLE_REFRESH_TOKEN) {
  oauth2Client.setCredentials({
    refresh_token: process.env.GOOGLE_REFRESH_TOKEN,
  });
}

const calendar = google.calendar({ version: "v3", auth: oauth2Client });

const server = new Server(
  { name: "clopus-calendar", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_calendars",
      description: "List all calendars",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "list_events",
      description: "List events from a calendar",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID (default: primary)" },
          time_min: { type: "string", description: "Start time (ISO format)" },
          time_max: { type: "string", description: "End time (ISO format)" },
          max_results: { type: "number", description: "Maximum events to return" },
          query: { type: "string", description: "Search query" },
        },
      },
    },
    {
      name: "get_event",
      description: "Get details of a specific event",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID" },
          event_id: { type: "string", description: "Event ID" },
        },
        required: ["event_id"],
      },
    },
    {
      name: "create_event",
      description: "Create a new calendar event",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID (default: primary)" },
          summary: { type: "string", description: "Event title" },
          description: { type: "string", description: "Event description" },
          location: { type: "string", description: "Event location" },
          start_time: { type: "string", description: "Start time (ISO format)" },
          end_time: { type: "string", description: "End time (ISO format)" },
          attendees: { type: "array", items: { type: "string" }, description: "Attendee emails" },
          send_notifications: { type: "boolean", description: "Send email notifications" },
        },
        required: ["summary", "start_time", "end_time"],
      },
    },
    {
      name: "update_event",
      description: "Update an existing event",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID" },
          event_id: { type: "string", description: "Event ID" },
          summary: { type: "string", description: "Event title" },
          description: { type: "string", description: "Event description" },
          location: { type: "string", description: "Event location" },
          start_time: { type: "string", description: "Start time (ISO format)" },
          end_time: { type: "string", description: "End time (ISO format)" },
        },
        required: ["event_id"],
      },
    },
    {
      name: "delete_event",
      description: "Delete an event",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID" },
          event_id: { type: "string", description: "Event ID" },
          send_notifications: { type: "boolean", description: "Send cancellation emails" },
        },
        required: ["event_id"],
      },
    },
    {
      name: "find_free_time",
      description: "Find free/busy time for calendars",
      inputSchema: {
        type: "object",
        properties: {
          calendar_ids: { type: "array", items: { type: "string" }, description: "Calendar IDs" },
          time_min: { type: "string", description: "Start of range (ISO format)" },
          time_max: { type: "string", description: "End of range (ISO format)" },
        },
        required: ["time_min", "time_max"],
      },
    },
    {
      name: "quick_add",
      description: "Quickly add an event using natural language",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID" },
          text: { type: "string", description: "Natural language event description" },
        },
        required: ["text"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_calendars": {
        const response = await calendar.calendarList.list();
        return { content: [{ type: "text", text: JSON.stringify(response.data.items, null, 2) }] };
      }

      case "list_events": {
        const response = await calendar.events.list({
          calendarId: (args.calendar_id as string) || "primary",
          timeMin: args.time_min as string,
          timeMax: args.time_max as string,
          maxResults: (args.max_results as number) || 10,
          singleEvents: true,
          orderBy: "startTime",
          q: args.query as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(response.data.items, null, 2) }] };
      }

      case "get_event": {
        const response = await calendar.events.get({
          calendarId: (args.calendar_id as string) || "primary",
          eventId: args.event_id as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }] };
      }

      case "create_event": {
        const event: calendar_v3.Schema$Event = {
          summary: args.summary as string,
          description: args.description as string,
          location: args.location as string,
          start: {
            dateTime: args.start_time as string,
            timeZone: "UTC",
          },
          end: {
            dateTime: args.end_time as string,
            timeZone: "UTC",
          },
        };

        if (args.attendees) {
          event.attendees = (args.attendees as string[]).map((email) => ({ email }));
        }

        const response = await calendar.events.insert({
          calendarId: (args.calendar_id as string) || "primary",
          requestBody: event,
          sendUpdates: args.send_notifications ? "all" : "none",
        });
        return { content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }] };
      }

      case "update_event": {
        const updateData: calendar_v3.Schema$Event = {};
        if (args.summary) updateData.summary = args.summary as string;
        if (args.description) updateData.description = args.description as string;
        if (args.location) updateData.location = args.location as string;
        if (args.start_time) {
          updateData.start = { dateTime: args.start_time as string, timeZone: "UTC" };
        }
        if (args.end_time) {
          updateData.end = { dateTime: args.end_time as string, timeZone: "UTC" };
        }

        const response = await calendar.events.patch({
          calendarId: (args.calendar_id as string) || "primary",
          eventId: args.event_id as string,
          requestBody: updateData,
        });
        return { content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }] };
      }

      case "delete_event": {
        await calendar.events.delete({
          calendarId: (args.calendar_id as string) || "primary",
          eventId: args.event_id as string,
          sendUpdates: args.send_notifications ? "all" : "none",
        });
        return { content: [{ type: "text", text: "Event deleted successfully" }] };
      }

      case "find_free_time": {
        const calendarIds = (args.calendar_ids as string[]) || ["primary"];
        const response = await calendar.freebusy.query({
          requestBody: {
            timeMin: args.time_min as string,
            timeMax: args.time_max as string,
            items: calendarIds.map((id) => ({ id })),
          },
        });
        return { content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }] };
      }

      case "quick_add": {
        const response = await calendar.events.quickAdd({
          calendarId: (args.calendar_id as string) || "primary",
          text: args.text as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(response.data, null, 2) }] };
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
  console.error("CLOPUS Calendar MCP server running");
}

main().catch(console.error);
