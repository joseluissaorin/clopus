---
name: slack-integration
description: Integrate applications with Slack for messaging and automation
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
triggers:
  - slack
  - slack bot
  - slack integration
  - slack webhook
---

# Slack Integration

## Context

You are an expert in Slack integrations for:
- Incoming webhooks
- Slack bots
- Slash commands
- Interactive messages
- Event subscriptions

## Webhook Integration

### 1. Simple Webhook Message

```python
import requests

def send_slack_message(webhook_url: str, message: str):
    requests.post(webhook_url, json={"text": message})

# Usage
WEBHOOK_URL = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX"
send_slack_message(WEBHOOK_URL, "Hello from Python!")
```

### 2. Rich Message with Blocks

```python
def send_rich_message(webhook_url: str, blocks: list):
    requests.post(webhook_url, json={"blocks": blocks})

# Block Kit message
blocks = [
    {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "New Deployment"
        }
    },
    {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": "*Environment:*\nProduction"
            },
            {
                "type": "mrkdwn",
                "text": "*Version:*\nv1.2.3"
            }
        ]
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Logs"},
                "url": "https://logs.example.com"
            }
        ]
    }
]

send_rich_message(WEBHOOK_URL, blocks)
```

## Slack Bot with Bolt

### 1. Setup

```bash
pip install slack-bolt
```

### 2. Basic Bot

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token="xoxb-your-bot-token")

# Listen for messages mentioning the bot
@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    say(f"Hello <@{user}>! How can I help?")

# Listen for specific message patterns
@app.message("hello")
def handle_hello(message, say):
    say(f"Hey there <@{message['user']}>!")

# Handle slash commands
@app.command("/status")
def handle_status_command(ack, say, command):
    ack()
    say(f"Status check requested by <@{command['user_id']}>")

# Start the app
if __name__ == "__main__":
    handler = SocketModeHandler(app, "xapp-your-app-token")
    handler.start()
```

### 3. Interactive Messages

```python
# Send message with buttons
@app.command("/approve")
def handle_approve(ack, say, command):
    ack()
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Approval requested by <@{command['user_id']}>"
                }
            },
            {
                "type": "actions",
                "block_id": "approval_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "action_id": "approve_action"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "action_id": "reject_action"
                    }
                ]
            }
        ]
    )

# Handle button clicks
@app.action("approve_action")
def handle_approve_action(ack, body, say):
    ack()
    user = body["user"]["id"]
    say(f"<@{user}> approved the request!")

@app.action("reject_action")
def handle_reject_action(ack, body, say):
    ack()
    user = body["user"]["id"]
    say(f"<@{user}> rejected the request.")
```

### 4. Modal Dialogs

```python
@app.command("/feedback")
def handle_feedback(ack, body, client):
    ack()

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "feedback_modal",
            "title": {"type": "plain_text", "text": "Feedback"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "rating_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "rating",
                        "options": [
                            {"text": {"type": "plain_text", "text": "Excellent"}, "value": "5"},
                            {"text": {"type": "plain_text", "text": "Good"}, "value": "4"},
                            {"text": {"type": "plain_text", "text": "Average"}, "value": "3"},
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Rating"}
                },
                {
                    "type": "input",
                    "block_id": "comments_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "comments",
                        "multiline": True
                    },
                    "label": {"type": "plain_text", "text": "Comments"}
                }
            ]
        }
    )

@app.view("feedback_modal")
def handle_feedback_submission(ack, body, view, say):
    ack()

    values = view["state"]["values"]
    rating = values["rating_block"]["rating"]["selected_option"]["value"]
    comments = values["comments_block"]["comments"]["value"]
    user = body["user"]["id"]

    # Process feedback
    say(
        channel="feedback-channel",
        text=f"New feedback from <@{user}>: Rating {rating}/5\n> {comments}"
    )
```

## Event Subscriptions

```python
# User joined channel
@app.event("member_joined_channel")
def handle_member_joined(event, say):
    user = event["user"]
    channel = event["channel"]
    say(channel=channel, text=f"Welcome <@{user}>! :wave:")

# Message posted
@app.event("message")
def handle_message(event, logger):
    logger.info(f"Message: {event.get('text', '')}")

# Reaction added
@app.event("reaction_added")
def handle_reaction(event, say):
    if event["reaction"] == "white_check_mark":
        say(
            channel=event["item"]["channel"],
            thread_ts=event["item"]["ts"],
            text="Task marked as complete!"
        )
```

## Notification Service

```python
from dataclasses import dataclass
from typing import Optional
import requests

@dataclass
class SlackNotifier:
    webhook_url: str
    default_channel: Optional[str] = None

    def send(self, message: str, channel: Optional[str] = None):
        payload = {"text": message}
        if channel:
            payload["channel"] = channel
        requests.post(self.webhook_url, json=payload)

    def send_alert(self, title: str, message: str, severity: str = "warning"):
        color = {"info": "#36a64f", "warning": "#ffcc00", "error": "#ff0000"}

        payload = {
            "attachments": [{
                "color": color.get(severity, "#36a64f"),
                "title": title,
                "text": message,
                "footer": "Alert System"
            }]
        }
        requests.post(self.webhook_url, json=payload)

# Usage
notifier = SlackNotifier(WEBHOOK_URL)
notifier.send_alert("Deployment Complete", "v1.2.3 deployed to production", "info")
```

## Best Practices

1. **Acknowledge quickly** - Always ack() within 3 seconds
2. **Use blocks** - Rich formatting improves readability
3. **Handle errors gracefully** - Catch and log exceptions
4. **Rate limit awareness** - Respect Slack's rate limits
5. **Use thread replies** - Keep channels organized
6. **Secure tokens** - Never commit tokens to code

## Required Scopes

For a full-featured bot:
- `chat:write` - Send messages
- `commands` - Handle slash commands
- `app_mentions:read` - Respond to @mentions
- `channels:read` - List channels
- `users:read` - Get user info
- `reactions:read` - Monitor reactions
