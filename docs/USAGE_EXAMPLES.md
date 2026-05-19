# Usage and API Examples

**Language:** English | [中文](USAGE_EXAMPLES.zh-CN.md)

These examples use public-safe placeholder data. Replace URLs, tokens, paths, and settings before running them in your own environment, and make sure you are allowed to process the target data.

## Example 1: Protected dispatch

Send a dispatch payload with your configured bearer token and a URL you are allowed to process.

## Example 2: Artifact lookup

Poll the job endpoint, then download generated artifacts from the artifact URL returned by the service.

## curl Examples

```bash
curl http://localhost:8090/health
curl -X POST http://localhost:8090/api/wechat/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-dispatch-token>" \
  -d '{"correlationId":"demo-001","source":"manual","commandText":"txt https://example.com/demo-video"}'
curl http://localhost:8090/api/jobs
```

Request bodies can change between versions; use local `/docs` or the source model definitions as the final reference.


## Local Validation Tips

- Start from `README.md` and bring the service up first.
- Call the health endpoint before running operations that write state or send notifications.
- Use synthetic or public demo data; do not paste private data into issues, screenshots, or commits.
- When using an AI assistant, provide this file, the deployment guide, and sanitized logs.
