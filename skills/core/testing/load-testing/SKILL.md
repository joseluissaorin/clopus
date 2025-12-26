---
name: load-testing
description: Performance and load testing
version: 1.0.0
category: testing
technologies: [k6, artillery, locust]
triggers:
  - load testing
  - performance testing
  - stress testing
  - k6
  - artillery
---

# Load Testing

Performance and load testing for APIs and web applications.

## Tools

- **k6**: Modern load testing tool (Go)
- **Artillery**: Node.js based load testing
- **Locust**: Python load testing
- **Apache JMeter**: Java-based (GUI)

## k6 Example

```javascript
// load-test.js
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 20 },   // Ramp up
    { duration: "1m", target: 20 },    // Stay at 20
    { duration: "10s", target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<200"],  // 95% under 200ms
    http_req_failed: ["rate<0.01"],    // <1% errors
  },
};

export default function () {
  const res = http.get("https://api.example.com/users");

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response time < 200ms": (r) => r.timings.duration < 200,
  });

  sleep(1);
}
```

## Artillery Example

```yaml
# artillery.yml
config:
  target: "https://api.example.com"
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 50
      name: "Sustained load"
  defaults:
    headers:
      Authorization: "Bearer {{ $processEnvironment.API_TOKEN }}"

scenarios:
  - name: "Browse and purchase"
    flow:
      - get:
          url: "/products"
      - think: 1
      - post:
          url: "/cart"
          json:
            productId: "{{ $randomNumber(1, 100) }}"
```

## Locust Example

```python
# locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_products(self):
        self.client.get("/products")

    @task(1)
    def view_product(self):
        product_id = random.randint(1, 100)
        self.client.get(f"/products/{product_id}")

    def on_start(self):
        self.client.post("/login", json={
            "username": "test",
            "password": "test"
        })
```

## Commands

```bash
# k6
k6 run load-test.js
k6 run --vus 100 --duration 30s load-test.js

# Artillery
artillery run artillery.yml
artillery run --output report.json artillery.yml

# Locust
locust -f locustfile.py --host=https://api.example.com
```

## Best Practices

1. Define realistic scenarios
2. Start with baseline testing
3. Test in production-like environment
4. Monitor backend during tests
5. Set appropriate thresholds
6. Run regularly in CI/CD
7. Document performance requirements
