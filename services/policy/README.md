# Policy service

Stateless rules engine. No database. Called by Expense at `POST /api/evaluate`.

Environment (ConfigMap): `POLICY_MAX_CLAIM_EUR` (default 500), `POLICY_MAX_MEALS_EUR` (80), `POLICY_MAX_OTHER_EUR` (25).

`GET /health` checks this process only.
