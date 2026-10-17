# FastAPI Scoped Middleware Service

A production-ready FastAPI microservice implementing a three-tier custom middleware pipeline: request context propagation, strict scoped CORS policies, and per-client sliding-window rate limiting.

**Live Deployment Base URL:**

`[https://fastapi-middleware-service-99tq.onrender.com](https://fastapi-middleware-service-99tq.onrender.com)`

---

## Features & Architecture

```text
Incoming Request
       │
       ▼
┌───────────────────────────────┐
│  1. Scoped CORS Middleware     │  ---> Validates Origin header (no wildcards)
└──────────────┬────────────────┘       Handles preflight OPTIONS /ping
               │
               ▼
┌───────────────────────────────┐
│  2. Request Context Propagator│  ---> Extracts or generates X-Request-ID
└──────────────┬────────────────┘       Attaches request_id to state & headers
               │
               ▼
┌───────────────────────────────┐
│  3. Per-Client Rate Limiter   │  ---> Tracks requests by X-Client-Id
└──────────────┬────────────────┘       Enforces B=8 req / 10s bucket (HTTP 429)
               │
               ▼
        GET /ping Handler

```

### Middleware Specifications

1. **Request Context Propagator (`X-Request-ID`)**
* Inspects inbound `X-Request-ID` header. Reuses existing ID or generates a UUIDv4.
* Injects `request_id` into `request.state`.
* Propagates `X-Request-ID` in all outgoing HTTP response headers and JSON body payloads.


2. **Scoped CORS Policy**
* Strictly restricts cross-origin resource sharing to `[https://app-dzm680.example.com](https://app-dzm680.example.com)` (and optional exam origin).
* Rejects wildcard (`*`) origins.
* Handles `OPTIONS /ping` preflight requests with full CORS headers (`Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`).


3. **Per-Client Rate Limiter**
* Evaluates `X-Client-Id` header per inbound request.
* **Bucket Capacity (B):** 8 requests per 10-second sliding window.
* Returns `HTTP 429 Too Many Requests` when bucket threshold is exceeded.
* Buckets are completely isolated across different `X-Client-Id` values.



---

## API Reference

### `GET /ping`

Returns service status along with request tracing metadata.

#### Request Headers

| Header | Type | Required | Description |
| --- | --- | --- | --- |
| `X-Request-ID` | `string` | Optional | Custom tracing ID. Generated automatically if omitted. |
| `X-Client-Id` | `string` | Optional | Client bucket identifier for rate limiting. |
| `Origin` | `string` | Optional | Origin domain for CORS verification. |

#### Example Response (`200 OK`)

```json
{
  "email": "your_email@example.com",
  "request_id": "a3b1c9d4-8e7f-4a2b-9c1d-0e2f4a6b8c0d"
}

```

#### Response Headers

```http
HTTP/1.1 200 OK
content-type: application/json
x-request-id: a3b1c9d4-8e7f-4a2b-9c1d-0e2f4a6b8c0d
access-control-allow-origin: https://app-dzm680.example.com

```

---

## Live API Verification Examples

### 1. Test Request ID Propagation

```bash
# Supply a custom X-Request-ID
curl -i -H "X-Request-ID: test-id-999" \
  https://fastapi-middleware-service-99tq.onrender.com/ping

```

### 2. Test CORS Preflight

```bash
# Preflight check from allowed origin
curl -i -X OPTIONS \
  -H "Origin: https://app-dzm680.example.com" \
  -H "Access-Control-Request-Method: GET" \
  https://fastapi-middleware-service-99tq.onrender.com/ping

```

### 3. Test Rate Limiting (8 req / 10s)

```bash
# Execute 9 requests rapidly under client ID 'client-alpha'
for i in {1..9}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "X-Client-Id: client-alpha" \
    https://fastapi-middleware-service-99tq.onrender.com/ping
done

```

---

## Local Development & Setup

### Prerequisites

* Python 3.10+
* `pip` or `poetry`

### Installation

1. **Clone repository & enter directory:**
```bash
git clone https://github.com/<your-username>/fastapi-middleware-service.git
cd fastapi-middleware-service

```


2. **Set up virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

```


3. **Configure environment variables:**
```bash
export USER_EMAIL="your_email@example.com"
export EXAM_ORIGIN="https://exam.example.com"

```


4. **Run development server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

```


5. **Run test suite:**
```bash
pytest test_main.py -v

```
