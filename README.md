# OpenCart payment & delivery tests

Pytest suite for OpenCart: delivery API (Europarcel), payment webhooks (Mobilpay/Netopia), SQL checks, optional UI smoke.

**No secrets. No shop source. No fake orders on prod.**

## Test strategy

| Layer | Marker | What | Needs shop? |
|-------|--------|------|-------------|
| Unit / sandbox | default | rules, webhook, COD vs card, filters, contract fixture | no |
| Integration | `integration` | read-only API GET / SQL SELECT | env only |
| UI smoke | `ui` | home → cart → checkout **without** confirm | `MOP_UI_SMOKE=1` |

CI runs only sandbox/unit (green without credentials).

## Run

```bash
pip install -r requirements.txt
pytest -m "not integration and not ui"
pytest -m integration
pytest -m ui
```

## Layout

```
├── .github/workflows/ci.yml
├── conftest.py
├── rules.py / order_flow.py / europarcel_filters.py / safe_assert.py
├── pages/                 # UI page objects
├── fixtures/
├── tests/                 # pytest suite (repo root = this project)
├── requirements.txt
├── pytest.ini
└── .env.example
```

## Guardrails

- Sandbox orders live in memory only
- Live API/SQL: GET/SELECT only
- UI never clicks Confirm / Pay
- Asserts avoid PII (`safe_assert`)
- Secrets via env; `.env` gitignored
