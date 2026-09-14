---
name: FastAPI startup lifecycle
description: Where critical startup initialization must run when the application uses an explicit lifespan handler.
---

Run critical database bootstrap and seeding inside the configured FastAPI lifespan, not in `@app.on_event("startup")` handlers.

**Why:** FastAPI does not execute legacy startup/shutdown event handlers when an explicit lifespan handler is supplied. Putting required initialization there can leave a healthy-looking app with missing seeded data and failing routes.

**How to apply:** Any initialization required before the first request—admin bootstrap, catalog seeding, required indexes, and connection verification—must complete in the lifespan before it yields. Only non-critical work may run in background threads.