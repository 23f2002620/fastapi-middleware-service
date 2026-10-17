# FastAPI Scoped Middleware Service

A production-oriented **FastAPI microservice** implementing a three-tier custom middleware pipeline for request context propagation, strict scoped Cross-Origin Resource Sharing (CORS), and per-client sliding-window rate limiting.

**Live Deployment:** https://fastapi-middleware-service-99tq.onrender.com

![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688.svg?style=flat&logo=fastapi&logoColor=white)
![Middleware](https://img.shields.io/badge/Custom-Middleware-blue.svg?style=flat)
![Deployment](https://img.shields.io/badge/Deployed%20on-Render-46E3B7.svg?style=flat&logo=render&logoColor=white)

---

## ✨ Features

- **Request ID Propagation:** Reuses an incoming `X-Request-ID` or generates a UUID v4 when one is not provided.
- **Request Context Management:** Stores the request ID in `request.state` and includes it in response headers and JSON payloads.
- **Strict Scoped CORS:** Allows cross-origin access only from explicitly configured origins, without wildcard origins.
- **Preflight Request Handling:** Supports CORS `OPTIONS` requests with the appropriate access-control headers.
- **Per-Client Rate Limiting:** Enforces a limit of 8 requests per client within a 10-second sliding window.
- **Client Isolation:** Maintains independent rate-limit buckets for different `X-Client-Id` values.
- **HTTP 429 Responses:** Rejects requests that exceed the configured rate limit.
- **Configurable Environment:** Supports environment variables for the user email and an optional additional exam origin.

## 🏗️ Middleware Architecture

The application processes incoming requests through three logical middleware layers before reaching the endpoint handler.

```text
                 Incoming Request
                        |
                        v
          +----------------------------+
          | 1. Scoped CORS Middleware  |
          | Validate Origin            |
          | Handle OPTIONS preflight   |
          +-------------+--------------+
                        |
                        v
          +----------------------------+
          | 2. Request Context          |
          | Reuse or generate UUID v4  |
          | Set request.state           |
          +-------------+--------------+
                        |
                        v
          +----------------------------+
          | 3. Per-Client Rate Limiter  |
          | Identify X-Client-Id        |
          | Enforce 8 requests / 10 sec |
          +-------------+--------------+
                        |
                        v
                 GET /ping Handler
                        |
                        v
                  JSON Response
```

The diagram represents the intended logical pipeline. Actual execution order depends on how middleware is registered in FastAPI.

## ⚙️ Middleware Specifications

### 1. Request Context Propagator

The request context middleware manages request tracing through the `X-Request-ID` header.

**Behavior:**

- Checks for an existing `X-Request-ID` request header.
- Reuses the supplied ID or generates a UUID v4 if it is absent.
- Stores the ID in `request.state.request_id`.
- Includes the request ID in outgoing response headers.
- Includes the request ID in JSON response bodies where applicable.

Example header:

```http
X-Request-ID: a3b1c9d4-8e7f-4a2b-9c1d-0e2f4a6b8c0d
```

### 2. Scoped CORS Policy

The service restricts browser-based cross-origin requests to explicitly permitted origins.

**Primary allowed origin:**

```text
https://app-dzm680.example.com
```

An additional origin can optionally be configured using the `EXAM_ORIGIN` environment variable.

The policy:

- Avoids wildcard (`*`) origins.
- Handles CORS preflight requests using the `OPTIONS` method.
- Configures allowed methods and request headers.
- Does not authorize unapproved origins through `Access-Control-Allow-Origin`.

Example response header:

```http
Access-Control-Allow-Origin: https://app-dzm680.example.com
```

**Security note:** CORS is not authentication. Non-browser clients can still send direct HTTP requests, so sensitive endpoints require independent access controls.

### 3. Per-Client Sliding-Window Rate Limiter

The rate limiter tracks requests using the `X-Client-Id` request header.

| Configuration | Value |
|---|---|
| Rate-limit strategy | Sliding window |
| Bucket capacity | 8 requests |
| Window duration | 10 seconds |
| Client identifier | `X-Client-Id` |
| Exceeded-limit response | `429 Too Many Requests` |

**Behavior:**

- Requests are counted independently for each client ID.
- Up to 8 requests are allowed within the configured 10-second window.
- Additional requests are rejected when the limit is exceeded.
- Different client IDs use separate rate-limit buckets.

The implementation's exact boundary behavior depends on how timestamps are stored and expired.

## 🚀 Live API Reference

### `GET /ping`

Returns service status metadata and request-tracing information.

**Base URL**

```text
https://fastapi-middleware-service-99tq.onrender.com
```

**Endpoint**

```text
GET /ping
```

### Request Headers

| Header | Required | Description |
|---|---|---|
| `X-Request-ID` | No | Optional request-tracing ID |
| `X-Client-Id` | No | Client identifier used for rate limiting |
| `Origin` | No | Origin used for CORS evaluation |

### Example Request

```bash
curl -i \
  -H "X-Request-ID: test-id-999" \
  -H "X-Client-Id: client-alpha" \
  "https://fastapi-middleware-service-99tq.onrender.com/ping"
```

### Example Response — `200 OK`

```json
{
  "email": "your_email@example.com",
  "request_id": "test-id-999"
}
```

The email and request ID above are examples. The actual email depends on deployment configuration, and the returned request ID depends on the supplied header or generated UUID.

### Example Response Headers

```http
HTTP/1.1 200 OK
content-type: application/json
x-request-id: test-id-999
access-control-allow-origin: https://app-dzm680.example.com
```

The CORS header is expected when the request originates from an allowed origin. Header names are case-insensitive.

## 🧪 Live API Verification

Use the following commands to test the deployed service.

### 1. Test Request ID Propagation

Send a custom request ID and verify that it is returned in the response.

```bash
curl -i \
  -H "X-Request-ID: test-id-999" \
  "https://fastapi-middleware-service-99tq.onrender.com/ping"
```

**Expected behavior:**

- The request succeeds if it is within the rate limit.
- The response includes `X-Request-ID: test-id-999`.
- The JSON response contains the same request ID.

### 2. Test CORS Preflight

Send a preflight request from the configured allowed origin.

```bash
curl -i -X OPTIONS \
  -H "Origin: https://app-dzm680.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-Request-ID, X-Client-Id" \
  "https://fastapi-middleware-service-99tq.onrender.com/ping"
```

**Expected behavior:**

- The response permits the configured origin.
- The response includes appropriate allowed-method and allowed-header information.
- Middleware-generated headers are present if the middleware is configured to cover preflight responses.

### 3. Test a Disallowed CORS Origin

```bash
curl -i -X OPTIONS \
  -H "Origin: https://unauthorized-domain.com" \
  -H "Access-Control-Request-Method: GET" \
  "https://fastapi-middleware-service-99tq.onrender.com/ping"
```

**Expected behavior:**

The response should not include an `Access-Control-Allow-Origin` header authorizing `https://unauthorized-domain.com`.

A disallowed CORS origin may still receive an HTTP response. CORS controls whether a browser permits the requesting page to access the response; it does not necessarily reject the HTTP request itself.

### 4. Test Rate Limiting

The following Bash loop sends 9 requests rapidly using the same client ID.

```bash
for i in {1..9}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "X-Client-Id: client-alpha" \
    "https://fastapi-middleware-service-99tq.onrender.com/ping"
done
```

**Expected behavior:**

- Requests within the configured limit return the endpoint's success status.
- The request that exceeds the limit returns `429 Too Many Requests`, assuming all nine requests fall within the same sliding window and the bucket starts empty.

Wait for the 10-second window to expire before repeating the test with the same client ID.

### 5. Test Client Isolation

Use different client IDs to verify independent rate-limit buckets.

```bash
curl -i \
  -H "X-Client-Id: client-alpha" \
  "https://fastapi-middleware-service-99tq.onrender.com/ping"

curl -i \
  -H "X-Client-Id: client-beta" \
  "https://fastapi-middleware-service-99tq.onrender.com/ping"
```

Requests from `client-beta` should not consume `client-alpha`'s rate-limit allowance.

## 🛠️ Local Development and Setup

### Prerequisites

- Python 3.10 or later
- pip
- Git

### 1. Clone the Repository

Replace `your-username` with your GitHub username.

```bash
git clone https://github.com/your-username/fastapi-middleware-service.git
cd fastapi-middleware-service
```

### 2. Create a Virtual Environment

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ensure that `requirements.txt` contains FastAPI, Uvicorn, and any other dependencies required by the implementation.

### 4. Configure Environment Variables

**Linux / macOS**

```bash
export USER_EMAIL="your_email@example.com"
export EXAM_ORIGIN="https://exam.example.com"
```

**Windows PowerShell**

```powershell
$env:USER_EMAIL = "your_email@example.com"
$env:EXAM_ORIGIN = "https://exam.example.com"
```

The `EXAM_ORIGIN` variable is optional if the application supports operation with only the primary allowed origin.

Use the exact environment-variable names expected by your application code.

### 5. Start the Development Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

- API endpoint: http://127.0.0.1:8000/ping
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 6. Run the Test Suite

```bash
pytest test_main.py -v
```

Ensure that `test_main.py` exists in the repository and that the test dependencies are installed.

## 📁 Project Structure

```text
fastapi-middleware-service/
├── main.py           # FastAPI app, middleware, and /ping endpoint
├── requirements.txt  # Python dependencies
├── test_main.py      # Automated tests
└── README.md         # Project documentation
```

This is the expected layout based on the documented setup. Add or remove files to reflect your actual repository.

## 🧰 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| UUID | Request ID generation |
| Custom middleware | Request context and response headers |
| Sliding-window algorithm | Per-client rate limiting |
| CORS policy | Origin-specific browser access |
| Pytest | Automated testing |
| Render | Cloud deployment |

## 🔒 Production Considerations

- Use a shared rate-limit store, such as Redis, when deploying multiple application workers or instances that must enforce a common limit.
- Set reasonable limits on the number and format of client identifiers.
- Avoid trusting client-supplied IDs for authentication; `X-Client-Id` should be treated as a rate-limit key, not proof of identity.
- Validate custom request IDs and consider generating a separate internal trace identifier when necessary.
- Configure middleware ordering carefully so CORS headers and request IDs are included on error responses and preflight responses.
- Use HTTPS for deployed endpoints.
- Add automated tests for rate-limit boundaries, CORS policies, request-ID propagation, and middleware error handling.

---

**Built with FastAPI for scoped CORS, request tracing, and per-client rate limiting.**
