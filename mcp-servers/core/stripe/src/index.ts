/**
 * CLOPUS MCP Server - Stripe
 * Provides payment processing capabilities via Stripe API
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "", {
  apiVersion: "2023-10-16",
});

const server = new Server(
  { name: "clopus-stripe", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "create_customer",
      description: "Create a new Stripe customer",
      inputSchema: {
        type: "object",
        properties: {
          email: { type: "string", description: "Customer email" },
          name: { type: "string", description: "Customer name" },
          metadata: { type: "object", description: "Additional metadata" },
        },
        required: ["email"],
      },
    },
    {
      name: "create_payment_intent",
      description: "Create a payment intent for a transaction",
      inputSchema: {
        type: "object",
        properties: {
          amount: { type: "number", description: "Amount in cents" },
          currency: { type: "string", description: "Currency code (e.g., usd)" },
          customer_id: { type: "string", description: "Stripe customer ID" },
          description: { type: "string", description: "Payment description" },
        },
        required: ["amount", "currency"],
      },
    },
    {
      name: "create_subscription",
      description: "Create a subscription for a customer",
      inputSchema: {
        type: "object",
        properties: {
          customer_id: { type: "string", description: "Stripe customer ID" },
          price_id: { type: "string", description: "Stripe price ID" },
          trial_days: { type: "number", description: "Trial period in days" },
        },
        required: ["customer_id", "price_id"],
      },
    },
    {
      name: "cancel_subscription",
      description: "Cancel an existing subscription",
      inputSchema: {
        type: "object",
        properties: {
          subscription_id: { type: "string", description: "Subscription ID" },
          immediately: { type: "boolean", description: "Cancel immediately or at period end" },
        },
        required: ["subscription_id"],
      },
    },
    {
      name: "create_product",
      description: "Create a new product",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Product name" },
          description: { type: "string", description: "Product description" },
          metadata: { type: "object", description: "Additional metadata" },
        },
        required: ["name"],
      },
    },
    {
      name: "create_price",
      description: "Create a price for a product",
      inputSchema: {
        type: "object",
        properties: {
          product_id: { type: "string", description: "Product ID" },
          unit_amount: { type: "number", description: "Price in cents" },
          currency: { type: "string", description: "Currency code" },
          recurring_interval: { type: "string", description: "Billing interval (month, year)" },
        },
        required: ["product_id", "unit_amount", "currency"],
      },
    },
    {
      name: "list_customers",
      description: "List all customers",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Number of customers to return" },
          email: { type: "string", description: "Filter by email" },
        },
      },
    },
    {
      name: "get_customer",
      description: "Get customer details",
      inputSchema: {
        type: "object",
        properties: {
          customer_id: { type: "string", description: "Customer ID" },
        },
        required: ["customer_id"],
      },
    },
    {
      name: "list_invoices",
      description: "List invoices for a customer",
      inputSchema: {
        type: "object",
        properties: {
          customer_id: { type: "string", description: "Customer ID" },
          limit: { type: "number", description: "Number of invoices to return" },
        },
      },
    },
    {
      name: "create_checkout_session",
      description: "Create a Stripe Checkout session",
      inputSchema: {
        type: "object",
        properties: {
          price_id: { type: "string", description: "Price ID" },
          success_url: { type: "string", description: "Success redirect URL" },
          cancel_url: { type: "string", description: "Cancel redirect URL" },
          mode: { type: "string", description: "payment, subscription, or setup" },
        },
        required: ["price_id", "success_url", "cancel_url", "mode"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "create_customer": {
        const customer = await stripe.customers.create({
          email: args.email as string,
          name: args.name as string,
          metadata: args.metadata as Record<string, string>,
        });
        return { content: [{ type: "text", text: JSON.stringify(customer, null, 2) }] };
      }

      case "create_payment_intent": {
        const paymentIntent = await stripe.paymentIntents.create({
          amount: args.amount as number,
          currency: args.currency as string,
          customer: args.customer_id as string,
          description: args.description as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(paymentIntent, null, 2) }] };
      }

      case "create_subscription": {
        const subscription = await stripe.subscriptions.create({
          customer: args.customer_id as string,
          items: [{ price: args.price_id as string }],
          trial_period_days: args.trial_days as number,
        });
        return { content: [{ type: "text", text: JSON.stringify(subscription, null, 2) }] };
      }

      case "cancel_subscription": {
        const subscription = args.immediately
          ? await stripe.subscriptions.cancel(args.subscription_id as string)
          : await stripe.subscriptions.update(args.subscription_id as string, {
              cancel_at_period_end: true,
            });
        return { content: [{ type: "text", text: JSON.stringify(subscription, null, 2) }] };
      }

      case "create_product": {
        const product = await stripe.products.create({
          name: args.name as string,
          description: args.description as string,
          metadata: args.metadata as Record<string, string>,
        });
        return { content: [{ type: "text", text: JSON.stringify(product, null, 2) }] };
      }

      case "create_price": {
        const priceData: Stripe.PriceCreateParams = {
          product: args.product_id as string,
          unit_amount: args.unit_amount as number,
          currency: args.currency as string,
        };
        if (args.recurring_interval) {
          priceData.recurring = { interval: args.recurring_interval as "month" | "year" };
        }
        const price = await stripe.prices.create(priceData);
        return { content: [{ type: "text", text: JSON.stringify(price, null, 2) }] };
      }

      case "list_customers": {
        const customers = await stripe.customers.list({
          limit: (args.limit as number) || 10,
          email: args.email as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(customers.data, null, 2) }] };
      }

      case "get_customer": {
        const customer = await stripe.customers.retrieve(args.customer_id as string);
        return { content: [{ type: "text", text: JSON.stringify(customer, null, 2) }] };
      }

      case "list_invoices": {
        const invoices = await stripe.invoices.list({
          customer: args.customer_id as string,
          limit: (args.limit as number) || 10,
        });
        return { content: [{ type: "text", text: JSON.stringify(invoices.data, null, 2) }] };
      }

      case "create_checkout_session": {
        const session = await stripe.checkout.sessions.create({
          line_items: [{ price: args.price_id as string, quantity: 1 }],
          mode: args.mode as "payment" | "subscription" | "setup",
          success_url: args.success_url as string,
          cancel_url: args.cancel_url as string,
        });
        return { content: [{ type: "text", text: JSON.stringify(session, null, 2) }] };
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
  console.error("CLOPUS Stripe MCP server running");
}

main().catch(console.error);
