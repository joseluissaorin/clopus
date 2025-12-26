---
name: cold-outreach
description: Cold email and outreach campaigns
version: 1.0.0
category: communication
technologies: [email, automation, crm]
triggers:
  - cold outreach
  - cold email
  - email campaign
  - outreach
---

# Cold Outreach

Cold email campaigns and outreach automation.

## Strategy Components

1. **List Building**: Finding and validating prospects
2. **Personalization**: Tailoring messages
3. **Sequencing**: Follow-up automation
4. **Tracking**: Opens, clicks, replies
5. **Optimization**: A/B testing, iteration

## Email Template Structure

```
Subject: [Personalized + Benefit]

Hi {first_name},

[1-2 sentences showing you did research]

[Problem statement they likely face]

[How you can help - specific value proposition]

[Social proof or credibility]

[Clear, low-friction CTA]

Best,
{your_name}
```

## Example Templates

### Initial Outreach
```
Subject: Quick question about {company}'s {specific_thing}

Hi {first_name},

Noticed {company} recently {specific_observation}. Congrats on that!

I've been helping companies in {industry} solve {problem} - typically seeing {specific_result}.

Would you be open to a quick 15-min call next week to explore if this could help {company}?

Best,
{your_name}
```

### Follow-up #1 (3 days later)
```
Subject: Re: Quick question about {company}'s {specific_thing}

Hi {first_name},

Just floating this back up - I know inboxes get busy.

To give you more context: we recently helped {similar_company} achieve {specific_result} in {timeframe}.

Worth a quick chat?

{your_name}
```

### Breakup Email (after 3-4 follow-ups)
```
Subject: Should I close your file?

Hi {first_name},

I haven't heard back, so I'm going to assume the timing isn't right.

If things change, here's a link to book time directly: {calendar_link}

All the best with {specific_initiative}!

{your_name}
```

## Automation Script

```python
import csv
from datetime import datetime, timedelta
from email_service import send_email, schedule_email

def run_campaign(prospects_file: str, templates: dict):
    with open(prospects_file) as f:
        prospects = list(csv.DictReader(f))

    for prospect in prospects:
        # Personalize and send initial email
        email_1 = templates['initial'].format(**prospect)
        send_email(
            to=prospect['email'],
            subject=templates['subject_1'].format(**prospect),
            body=email_1
        )

        # Schedule follow-ups
        schedule_email(
            to=prospect['email'],
            subject=f"Re: {templates['subject_1'].format(**prospect)}",
            body=templates['followup_1'].format(**prospect),
            send_at=datetime.now() + timedelta(days=3)
        )
```

## Best Practices

1. **Research first** - Know the prospect
2. **Keep it short** - Under 150 words
3. **One CTA only** - Make it easy to respond
4. **Personalize genuinely** - Not just {first_name}
5. **Test subject lines** - 40% of success
6. **Follow up** - 80% of deals come from follow-ups
7. **Track everything** - Opens, clicks, replies
8. **Respect unsubscribes** - Comply with laws
