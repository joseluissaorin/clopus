---
name: python-django
description: Django web application development
version: 1.0.0
category: development
technologies: [python, django, postgresql, redis]
triggers:
  - django
  - django rest framework
  - drf
  - python web app
---

# Python Django Development

Expert-level Django web application development.

## Capabilities

- Django project setup and configuration
- Django REST Framework API development
- Authentication (JWT, Session, OAuth)
- Database models and migrations
- Admin customization
- Celery async tasks
- Django Channels (WebSockets)
- Testing with pytest-django

## Project Structure

```
project/
├── config/              # Project settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   └── {app_name}/
│       ├── models.py
│       ├── views.py
│       ├── serializers.py
│       ├── urls.py
│       └── tests/
├── templates/
├── static/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── manage.py
```

## Commands

```bash
# Create project
django-admin startproject config .

# Create app
python manage.py startapp apps/{name}

# Database
python manage.py makemigrations
python manage.py migrate

# Run server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Shell
python manage.py shell_plus

# Tests
pytest --cov=apps
```

## Best Practices

1. Use environment variables for secrets
2. Separate settings for dev/prod
3. Use Django REST Framework for APIs
4. Write model tests
5. Use select_related/prefetch_related
6. Implement proper permissions
7. Use Django's security middleware
