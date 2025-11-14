# MERL-T API - Postman Collection

This folder contains the **Postman Collection** and **Environment** for the MERL-T API, automatically generated from the OpenAPI 3.1.0 schema.

---

## Files

- **`MERL-T_API.postman_collection.json`** - Postman Collection v2.1 with all API endpoints organized by tag
- **`MERL-T_API.postman_environment.json`** - Environment variables for different deployment environments

---

## Quick Start

### 1. Import into Postman

1. Open **Postman**
2. Click **Import** button (top-left)
3. Drag and drop both JSON files or click **Select Files**:
   - `MERL-T_API.postman_collection.json`
   - `MERL-T_API.postman_environment.json`
4. Click **Import**

### 2. Configure Environment

1. Select **"MERL-T API Environment"** from the environment dropdown (top-right)
2. Click the **eye icon** → **Edit**
3. Update the variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `base_url` | API base URL | `http://localhost:8000` |
| `api_key` | Your API key | `your-api-key-here` |
| `dev_url` | Development server | `http://localhost:8000` |
| `staging_url` | Staging environment | `https://staging-api.merl-t.alis.ai` |
| `prod_url` | Production environment | `https://api.merl-t.alis.ai` |

4. Save the environment

### 3. Start Testing

1. Ensure the API server is running:
   ```bash
   cd backend/orchestration
   uvicorn api.main:app --reload
   ```

2. Select a request from the collection
3. Click **Send**
4. View the response

---

## Collection Structure

The collection is organized by **OpenAPI tags**:

```
MERL-T API/
├── Query Execution/
│   ├── POST /query/execute - Execute Legal Query
│   ├── GET /query/status/{trace_id} - Get Query Status
│   ├── GET /query/history/{user_id} - Get Query History
│   └── GET /query/retrieve/{trace_id} - Retrieve Query Details
├── Feedback/
│   ├── POST /feedback/user - Submit User Feedback
│   ├── POST /feedback/rlcf - Submit RLCF Expert Feedback
│   ├── POST /feedback/ner - Submit NER Correction
│   └── GET /feedback/stats - Get Feedback Statistics
├── Statistics & Analytics/
│   ├── GET /stats/pipeline - Get Pipeline Statistics
│   └── GET /stats/feedback - Get Feedback Statistics
└── System/
    ├── GET / - API Root
    └── GET /health - Health Check
```

---

## Authentication

All requests (except `/` and `/health`) use **API Key authentication**:

- **Header Name**: `X-API-Key`
- **Header Value**: `{{api_key}}` (from environment)

The collection is configured with **collection-level authentication**, so all requests automatically include the API key header.

---

## Environment Variables

### Switching Environments

To switch between development, staging, and production:

1. Edit the environment
2. Change `base_url` to one of:
   - `{{dev_url}}` - Local development
   - `{{staging_url}}` - Staging environment
   - `{{prod_url}}` - Production environment
3. Update `api_key` to the corresponding environment's key

### Example

```json
{
  "key": "base_url",
  "value": "{{prod_url}}",
  "type": "default",
  "enabled": true
}
```

---

## Regenerating the Collection

The collection was generated from the OpenAPI schema using `scripts/generate_postman_collection.py`.

### Requirements

- Python 3.8+
- FastAPI and dependencies installed

### Generate Full Collection

To regenerate the collection with **all endpoints** (requires running environment):

```bash
# Ensure FastAPI is installed
pip install -r requirements.txt

# Run generation script
python scripts/generate_postman_collection.py
```

This will:
1. Load the complete OpenAPI schema from the FastAPI app
2. Convert it to Postman Collection v2.1 format
3. Include all request bodies, examples, and response schemas
4. Save to `postman/` folder

### Generate Mock Collection

If FastAPI is not available, the script will generate a **mock collection** with a simplified schema for testing purposes.

---

## Request Examples

All requests include **example payloads** from the OpenAPI schema.

### Example: Execute Query

**Request Body**:
```json
{
  "query": "È valido un contratto firmato da un sedicenne?",
  "context": {
    "temporal_reference": "latest",
    "jurisdiction": "nazionale",
    "user_role": "cittadino"
  },
  "options": {
    "max_iterations": 3,
    "return_trace": true
  }
}
```

**Headers**:
```
X-API-Key: {{api_key}}
Content-Type: application/json
```

**URL**:
```
{{base_url}}/query/execute
```

---

## Rate Limiting

All responses include **rate limit headers**:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1699999999
X-RateLimit-Used: 1
```

Monitor these headers in Postman's response viewer to track your API usage.

---

## Troubleshooting

### Issue: "Missing API key" error

**Solution**: Ensure the environment is selected and `api_key` variable is set.

### Issue: "Connection refused"

**Solution**: Verify the API server is running:
```bash
curl http://localhost:8000/health
```

### Issue: Requests showing incorrect URL

**Solution**:
1. Check `base_url` in environment variables
2. Ensure no trailing slash in `base_url`
3. Reload the environment

### Issue: Collection has only 1 endpoint

**Cause**: Generated with mock schema (FastAPI not available)

**Solution**: Install FastAPI and regenerate:
```bash
pip install fastapi uvicorn
python scripts/generate_postman_collection.py
```

---

## Advanced Features

### Pre-request Scripts

Add pre-request scripts to dynamically generate values:

```javascript
// Generate unique session_id
pm.environment.set("session_id", "session_" + Date.now());
```

### Tests

Add tests to validate responses:

```javascript
// Test: Response is 200 OK
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Test: Response contains trace_id
pm.test("Response has trace_id", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('trace_id');
});

// Test: Confidence is above threshold
pm.test("Confidence > 0.8", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.answer.confidence).to.be.above(0.8);
});
```

### Collection Runner

Run the entire collection automatically:

1. Click **Collections** → **MERL-T API**
2. Click **Run**
3. Select environment and click **Run MERL-T API**

This will execute all requests sequentially and report results.

---

## Alternative Import Methods

### Import from URL

You can also import the collection from a URL:

```bash
# Serve the collection file locally
python -m http.server 8080

# Then import in Postman:
# Import → Link → http://localhost:8080/postman/MERL-T_API.postman_collection.json
```

### Import from Git Repository

If the collection is committed to Git:

```
Import → Repository → Enter Git URL
```

---

## Documentation

For more information:

- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Authentication Guide**: [docs/api/AUTHENTICATION.md](../docs/api/AUTHENTICATION.md)
- **Rate Limiting Guide**: [docs/api/RATE_LIMITING.md](../docs/api/RATE_LIMITING.md)
- **API Examples**: [docs/api/API_EXAMPLES.md](../docs/api/API_EXAMPLES.md)

---

## Support

For issues with the Postman collection:

- **GitHub Issues**: https://github.com/ALIS-ai/MERL-T/issues
- **Email**: support@alis.ai
- **Discord**: https://discord.gg/alis-ai

---

**Last Updated**: November 14, 2025
**Collection Version**: 0.2.0
**Postman Version**: v2.1.0
