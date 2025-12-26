---
title: "N+1 Query Problem"
type: mistake
technologies: [sql, orm, prisma, sqlalchemy, django]
confidence: 0.98
created: 2025-12-26
last_used: 2025-12-26
use_count: 0
---

# N+1 Query Problem

A common performance anti-pattern that causes excessive database queries.

## The Mistake

When fetching a list of items and then querying for related data in a loop:

```python
# BAD: N+1 queries
users = await db.query(User).all()  # 1 query
for user in users:
    posts = await db.query(Post).filter(Post.user_id == user.id).all()  # N queries
    user.posts = posts
```

This results in 1 + N queries where N is the number of users.

## Why It's Bad

- **Performance**: Each query has network latency overhead
- **Database load**: Many small queries are worse than one larger query
- **Scaling issues**: Problem worsens as data grows

## How to Fix

### SQLAlchemy (Eager Loading)

```python
# GOOD: Use joinedload or selectinload
from sqlalchemy.orm import joinedload, selectinload

# For one-to-one or many-to-one
users = await db.query(User).options(joinedload(User.profile)).all()

# For one-to-many (preferred)
users = await db.query(User).options(selectinload(User.posts)).all()
```

### Prisma

```typescript
// GOOD: Use include
const users = await prisma.user.findMany({
  include: {
    posts: true,
    profile: true,
  },
});
```

### Django ORM

```python
# GOOD: Use select_related (ForeignKey) or prefetch_related (Many)
users = User.objects.select_related('profile').prefetch_related('posts').all()
```

### Raw SQL

```sql
-- GOOD: Use JOIN
SELECT users.*, posts.*
FROM users
LEFT JOIN posts ON posts.user_id = users.id;
```

## Detection

### SQLAlchemy

```python
# Enable query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Prisma

```typescript
// Enable query logging
const prisma = new PrismaClient({
  log: ['query'],
});
```

### Django

```python
# Use django-debug-toolbar in development
INSTALLED_APPS += ['debug_toolbar']
```

## Prevention Checklist

- [ ] Review all loops that access related objects
- [ ] Use ORM eager loading features
- [ ] Enable query logging in development
- [ ] Set up database query monitoring
- [ ] Write tests that assert query counts
