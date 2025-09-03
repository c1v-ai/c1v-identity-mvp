## Endpoints

### POST /match
**Request body**
```json
{
  "record1": {"email": "a@x.com", "first_name": "Alex", "zip": "94107"},
  "record2": {"email": "a@x.com", "first_name": "ALEX", "zip": "94107"}
}

**Response body**
{
  "match": true,
  "confidence": 1.0,
  "reason": "naive-baseline"
}

**Request body**
curl -s -X POST http://localhost:8000/match \
  -H 'Content-Type: application/json' \
  -d '{"record1":{"email":"a@x.com","first_name":"Alex","zip":"94107"},
       "record2":{"email":"a@x.com","first_name":"ALEX","zip":"94107"}}'



### 2) Add a short “API Contract” note to **testing.md**
```bash
cat >> testing.md <<'MD'

## API Contract (enforced by tests)
- `MatchResponse`: `match: bool`, `confidence: float (0..1)`, `reason: string|null`.
- Tests must verify: HTTP 200, types of fields, and confidence within `[0,1]`.
MD
