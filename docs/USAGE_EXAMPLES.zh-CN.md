# 使用和 API 示例

**语言：** [English](USAGE_EXAMPLES.md) | 中文

这些示例使用公开安全的占位数据。复制到自己的环境前，请替换 URL、token、路径和配置，并确认你有权处理对应数据。

## 示例 1：受保护的 dispatch

使用你配置的 bearer token 发送 dispatch payload，目标 URL 必须是你有权处理的媒体。

## 示例 2：产物查询

轮询任务接口，然后通过服务返回的 artifact URL 下载生成文件。

## curl 示例

```bash
curl http://localhost:8090/health
curl -X POST http://localhost:8090/api/wechat/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-dispatch-token>" \
  -d '{"correlationId":"demo-001","source":"manual","commandText":"txt https://example.com/demo-video"}'
curl http://localhost:8090/api/jobs
```

接口请求体会随版本变化；以本地 `/docs` 或源码里的模型定义为准。


## 本地验证建议

- 先按 `README.zh-CN.md` 启动项目。
- 先调用健康检查，再执行会写入状态或发通知的操作。
- 使用合成数据或公开演示数据，不要把私人数据写进 issue、截图或提交。
- 如果让 AI assistant 帮忙，把本文件、部署文档和已去敏日志一起提供给它。
