---
name: email-automation
description: Automate email sending, campaigns, and workflows
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
triggers:
  - email
  - email automation
  - email campaign
  - newsletter
  - transactional email
---

# Email Automation

## Context

You are an expert in email automation for:
- Transactional emails
- Marketing campaigns
- Drip sequences
- Newsletter distribution
- Email templates

## Email Providers

### 1. Resend (Modern, Developer-First)

```python
import resend

resend.api_key = "re_123456789"

# Send simple email
resend.Emails.send({
    "from": "hello@yourdomain.com",
    "to": ["user@example.com"],
    "subject": "Welcome!",
    "html": "<p>Welcome to our platform!</p>"
})

# Send with template
resend.Emails.send({
    "from": "hello@yourdomain.com",
    "to": ["user@example.com"],
    "subject": "Your order confirmation",
    "react": OrderConfirmationEmail(order=order_data)
})
```

### 2. SendGrid

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

sg = SendGridAPIClient(api_key='SG.xxx')

message = Mail(
    from_email='hello@yourdomain.com',
    to_emails='user@example.com',
    subject='Welcome!',
    html_content='<p>Welcome to our platform!</p>'
)

response = sg.send(message)
print(response.status_code)
```

### 3. Amazon SES

```python
import boto3

ses = boto3.client('ses', region_name='us-east-1')

response = ses.send_email(
    Source='hello@yourdomain.com',
    Destination={
        'ToAddresses': ['user@example.com']
    },
    Message={
        'Subject': {'Data': 'Welcome!'},
        'Body': {
            'Html': {'Data': '<p>Welcome to our platform!</p>'}
        }
    }
)
```

### 4. SMTP (Generic)

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to, subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = 'hello@yourdomain.com'
    msg['To'] = to

    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login('user@gmail.com', 'app_password')
        server.send_message(msg)
```

## Email Templates

### 1. HTML Email Template

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ subject }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 20px 0;
        }
        .content {
            background: #f9f9f9;
            padding: 30px;
            border-radius: 8px;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background: #0066cc;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            padding: 20px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ logo_url }}" alt="Logo" height="40">
    </div>

    <div class="content">
        <h1>{{ title }}</h1>
        <p>{{ body }}</p>

        {% if cta_url %}
        <a href="{{ cta_url }}" class="button">{{ cta_text }}</a>
        {% endif %}
    </div>

    <div class="footer">
        <p>© 2024 Company Name. All rights reserved.</p>
        <p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
    </div>
</body>
</html>
```

### 2. Template Rendering with Jinja2

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('welcome.html')

html_content = template.render(
    subject="Welcome!",
    title="Welcome to Our Platform",
    body="We're excited to have you on board.",
    cta_url="https://app.example.com/get-started",
    cta_text="Get Started",
    unsubscribe_url="https://example.com/unsubscribe"
)
```

## Email Automation Workflows

### 1. Drip Campaign

```python
from datetime import datetime, timedelta
from celery import Celery

app = Celery('email_tasks')

WELCOME_SEQUENCE = [
    {"delay_days": 0, "template": "welcome", "subject": "Welcome!"},
    {"delay_days": 1, "template": "getting_started", "subject": "Getting Started"},
    {"delay_days": 3, "template": "tips", "subject": "Pro Tips"},
    {"delay_days": 7, "template": "check_in", "subject": "How's it going?"},
]

@app.task
def start_welcome_sequence(user_id, email):
    for step in WELCOME_SEQUENCE:
        send_drip_email.apply_async(
            args=[user_id, email, step["template"], step["subject"]],
            eta=datetime.utcnow() + timedelta(days=step["delay_days"])
        )

@app.task
def send_drip_email(user_id, email, template_name, subject):
    # Check if user is still subscribed
    if not is_subscribed(user_id):
        return

    html = render_template(template_name, user_id=user_id)
    send_email(to=email, subject=subject, html=html)
```

### 2. Transactional Email Service

```python
from enum import Enum
from dataclasses import dataclass

class EmailType(Enum):
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    ORDER_CONFIRMATION = "order_confirmation"
    INVOICE = "invoice"
    NOTIFICATION = "notification"

@dataclass
class EmailConfig:
    template: str
    subject_template: str
    from_email: str = "hello@yourdomain.com"

EMAIL_CONFIGS = {
    EmailType.WELCOME: EmailConfig(
        template="welcome.html",
        subject_template="Welcome to {company_name}!"
    ),
    EmailType.PASSWORD_RESET: EmailConfig(
        template="password_reset.html",
        subject_template="Reset your password",
        from_email="security@yourdomain.com"
    ),
    EmailType.ORDER_CONFIRMATION: EmailConfig(
        template="order_confirmation.html",
        subject_template="Order #{order_id} confirmed"
    ),
}

def send_transactional_email(email_type: EmailType, to: str, **context):
    config = EMAIL_CONFIGS[email_type]

    html = render_template(config.template, **context)
    subject = config.subject_template.format(**context)

    return send_email(
        from_email=config.from_email,
        to=to,
        subject=subject,
        html=html
    )
```

## Best Practices

1. **Use verified domains** - Improve deliverability
2. **Include unsubscribe links** - Legal requirement
3. **Test across email clients** - Use Litmus or Email on Acid
4. **Use inline CSS** - Better email client support
5. **Keep images hosted** - Don't embed base64
6. **Monitor bounce rates** - Clean lists regularly
7. **Implement double opt-in** - Better list quality
8. **A/B test subject lines** - Improve open rates

## Deliverability Checklist

- [ ] SPF record configured
- [ ] DKIM signature enabled
- [ ] DMARC policy set
- [ ] Domain verified with provider
- [ ] Unsubscribe link included
- [ ] Physical address in footer
- [ ] Test on major email clients
- [ ] Image alt text included
