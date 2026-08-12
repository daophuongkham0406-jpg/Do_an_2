# SQL Import

PostgreSQL style export.

```bash
psql "$DATABASE_URL" -f schema.sql
psql "$DATABASE_URL" -f inserts.sql
psql "$DATABASE_URL" -f indexes.sql
```

Insert order follows foreign-key dependencies.
