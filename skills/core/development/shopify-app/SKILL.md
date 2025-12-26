---
name: shopify-app
description: Shopify app development
version: 1.0.0
category: development
technologies: [shopify, node, react, graphql]
triggers:
  - shopify
  - shopify app
  - shopify theme
  - liquid
---

# Shopify App Development

Shopify app and theme development.

## Capabilities

- Embedded app development
- Shopify Admin API (REST/GraphQL)
- Storefront API
- Theme development (Liquid)
- Shopify CLI
- App billing
- Webhooks
- Polaris UI components

## App Project Structure

```
project/
├── app/
│   ├── routes/
│   │   ├── app._index.jsx
│   │   └── webhooks.jsx
│   ├── shopify.server.js
│   └── entry.server.jsx
├── extensions/
├── prisma/
├── shopify.app.toml
└── package.json
```

## Setup

```bash
# Create app
npm init @shopify/app@latest

# Install Shopify CLI
npm install -g @shopify/cli @shopify/app

# Development
shopify app dev

# Deploy
shopify app deploy
```

## GraphQL Query

```javascript
const response = await admin.graphql(
  `#graphql
  query getProducts($first: Int!) {
    products(first: $first) {
      nodes {
        id
        title
        handle
        variants(first: 10) {
          nodes {
            id
            price
          }
        }
      }
    }
  }`,
  { variables: { first: 10 } }
);
```

## Theme Development

```liquid
{% comment %} sections/hero.liquid {% endcomment %}
<section class="hero">
  <h1>{{ section.settings.heading }}</h1>
  <p>{{ section.settings.text }}</p>
</section>

{% schema %}
{
  "name": "Hero",
  "settings": [
    {
      "type": "text",
      "id": "heading",
      "label": "Heading"
    }
  ]
}
{% endschema %}
```

## Best Practices

1. Use Shopify CLI for development
2. Follow Polaris design guidelines
3. Implement proper OAuth flow
4. Handle webhooks idempotently
5. Use GraphQL over REST
6. Implement app billing properly
7. Test with development stores
