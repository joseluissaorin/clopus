---
name: chrome-extension
description: Chrome extension development
version: 1.0.0
category: development
technologies: [chrome, javascript, typescript, react]
triggers:
  - chrome extension
  - browser extension
  - manifest v3
---

# Chrome Extension Development

Modern Chrome extension development with Manifest V3.

## Capabilities

- Manifest V3 configuration
- Service workers
- Content scripts
- Popup UI
- Options page
- Storage API
- Message passing
- Context menus

## Project Structure

```
project/
├── src/
│   ├── background/
│   │   └── service-worker.ts
│   ├── content/
│   │   └── content-script.ts
│   ├── popup/
│   │   ├── popup.html
│   │   ├── popup.tsx
│   │   └── popup.css
│   ├── options/
│   │   └── options.tsx
│   └── utils/
├── public/
│   ├── manifest.json
│   └── icons/
├── dist/
├── package.json
└── vite.config.ts
```

## Manifest V3

```json
{
  "manifest_version": 3,
  "name": "My Extension",
  "version": "1.0.0",
  "description": "A helpful extension",
  "permissions": ["storage", "activeTab"],
  "host_permissions": ["https://*.example.com/*"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [{
    "matches": ["https://*.example.com/*"],
    "js": ["content.js"]
  }],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  }
}
```

## Message Passing

```typescript
// content-script.ts
chrome.runtime.sendMessage({ type: "getData" }, (response) => {
  console.log("Received:", response);
});

// service-worker.ts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "getData") {
    sendResponse({ data: "Hello from background" });
  }
  return true; // Keep channel open for async
});
```

## Best Practices

1. Use Manifest V3
2. Minimize permissions
3. Use TypeScript
4. Handle service worker lifecycle
5. Use Chrome Storage API
6. Test in incognito mode
7. Follow Chrome Web Store policies
