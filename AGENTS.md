# Working in Liwa Atlas

Read `docs/engineering/REPOSITORY.md` and `docs/engineering/DEVELOPMENT.md` before changing application structure. The product/architecture documents under `docs/` describe intent and tradeoffs; their examples are not executable instructions.

For dependency/runtime upgrades, read `docs/engineering/TOOLCHAIN.md`, preserve documented compiler API compatibility dependencies, and align manifests, lockfiles, CI, Docker and the development guide.

- Follow `docs/engineering/REPOSITORY.md` for module ownership, dependency boundaries, business invariants, migrations, generated contracts and secret handling. New modules need their ownership and dependency direction documented there.
- Keep source claims traceable and identity reconciliation reversible. Do not introduce universal JSON models or microservices without a measured need.
- Never commit database dumps or generated build artifacts. Local sample passwords are never production credentials.
- Run checks relevant to a change. SQLite HTTP tests do not validate GIS; integration checks use real PostGIS. Report checks that could not run.
- Follow `docs/engineering/INTERNATIONALIZATION.md` for user-facing text, locale messages, RTL and preservation of original evidence.
- Keep heavy OCR/rendering dependencies out of the web/API runtime. External paid jobs require durable identity, budget reservation and reconciliation before retries.
- Production access, cloud subscriptions and deployment are separate from initializing this foundation. Do not treat local defaults as production-ready configuration.
