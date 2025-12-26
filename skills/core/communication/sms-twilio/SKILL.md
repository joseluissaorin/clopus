---
name: sms-twilio
description: SMS messaging with Twilio
version: 1.0.0
category: communication
technologies: [twilio, python, node, sms]
triggers:
  - sms
  - twilio
  - text message
  - sms notification
---

# SMS with Twilio

SMS messaging and automation using Twilio.

## Setup

```bash
# Python
pip install twilio

# Node.js
npm install twilio
```

## Send SMS (Python)

```python
from twilio.rest import Client

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_number = os.environ['TWILIO_PHONE_NUMBER']

client = Client(account_sid, auth_token)

# Send single message
message = client.messages.create(
    body="Hello from CLOPUS!",
    from_=twilio_number,
    to="+1234567890"
)

print(f"Message SID: {message.sid}")
```

## Send SMS (Node.js)

```javascript
const twilio = require('twilio');

const client = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

async function sendSMS(to, body) {
  const message = await client.messages.create({
    body: body,
    from: process.env.TWILIO_PHONE_NUMBER,
    to: to
  });

  console.log(`Message SID: ${message.sid}`);
  return message;
}
```

## Receive SMS (Webhook)

```python
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/sms", methods=['POST'])
def sms_reply():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')

    resp = MessagingResponse()

    if 'hello' in incoming_msg:
        resp.message("Hi there! How can I help?")
    elif 'help' in incoming_msg:
        resp.message("Commands: HELLO, HELP, STATUS")
    else:
        resp.message("I didn't understand. Reply HELP for options.")

    return str(resp)
```

## Bulk SMS

```python
def send_bulk_sms(recipients: list, message: str):
    results = []

    for recipient in recipients:
        try:
            msg = client.messages.create(
                body=message,
                from_=twilio_number,
                to=recipient['phone']
            )
            results.append({
                'phone': recipient['phone'],
                'status': 'sent',
                'sid': msg.sid
            })
        except Exception as e:
            results.append({
                'phone': recipient['phone'],
                'status': 'failed',
                'error': str(e)
            })

    return results
```

## SMS Verification

```python
# Start verification
verification = client.verify.v2.services(VERIFY_SERVICE_SID) \
    .verifications \
    .create(to="+1234567890", channel='sms')

# Check code
verification_check = client.verify.v2.services(VERIFY_SERVICE_SID) \
    .verification_checks \
    .create(to="+1234567890", code="123456")

if verification_check.status == 'approved':
    print("Phone verified!")
```

## Best Practices

1. Validate phone numbers (E.164 format)
2. Handle rate limits
3. Use Messaging Services for scale
4. Implement opt-out handling
5. Log all messages sent
6. Use templates for consistency
7. Test with Twilio sandbox first
8. Monitor delivery status
