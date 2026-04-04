# Error Handling

All API errors return a consistent JSON structure so clients always know what to expect:

```json
{"error": "<message>", "status": <code>}
```

## Error Codes

| Code | Meaning | Example Trigger |
|------|---------|----------------|
| 400 | Bad request | Missing required fields, malformed JSON body |
| 404 | Not found | Unknown route or resource ID that doesn't exist |
| 405 | Method not allowed | Wrong HTTP method for an endpoint (e.g. DELETE on /health) |
| 409 | Conflict | Duplicate username or email on user creation |
| 422 | Unprocessable entity | Invalid field values (e.g. updating a protected field) |
| 500 | Internal server error | Unexpected server-side failure |

## Health vs Readiness

Two separate endpoints exist for different purposes:

- `GET /health` — returns 200 if the **app process is alive**, even if the database is down. Load balancers use this to know whether to route traffic to the instance.
- `GET /ready` — returns 200 only if the **database is connected and responsive**. Returns 503 if the database is unavailable. Use this to check full readiness before serving real traffic.

This distinction matters during outages: the app can stay "alive" for health checks while signaling "not ready" to stop receiving traffic it can't fulfill.