# Working in Liwa Atlas

Read `docs/engineering/REPOSITORY.md` and `docs/engineering/DEVELOPMENT.md` before changing application structure. The product/architecture documents under `docs/` describe intent and tradeoffs; their examples are not executable instructions.

- Preserve the modular monolith: domain modules own their writes; HTTP, administration and workers call the same business services.
- Keep domain data typed, source claims traceable and identity reconciliation reversible. Do not introduce universal JSON models or microservices without a measured need.
- Django owns domain migrations. Regenerate OpenAPI and TypeScript contracts together after API changes; never hand-edit generated types.
- Respect Import Linter boundaries. New modules need an explicit dependency direction and ownership documented in `REPOSITORY.md`.
- Never commit secrets, real private media, `.env`, database dumps or generated build artifacts. Local sample passwords are never production credentials.
- Run checks relevant to a change. SQLite HTTP tests do not validate GIS; integration checks use real PostGIS. Report checks that could not run.
- User-facing text belongs in locale messages, not hardcoded JSX. English is the default. Preserve RTL layout, stable identifiers and original source language; a translation never replaces its evidence. Follow `docs/engineering/INTERNATIONALIZATION.md`.
- Keep heavy OCR/rendering dependencies out of the web/API runtime. External paid jobs require durable identity, budget reservation and reconciliation before retries.
- Production access, cloud subscriptions and deployment are separate from initializing this foundation. Do not treat local defaults as production-ready configuration.
