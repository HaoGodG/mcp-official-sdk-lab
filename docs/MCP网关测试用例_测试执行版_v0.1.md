# MCP 网关测试用例（测试执行版 v0.1）

> 适用对象：测试人员  
> 目标：验证 MCP 网关在正常访问、协议不兼容、鉴权失败、限流和异常场景下的行为是否符合预期。  
> 说明：异常场景中，“请求失败”本身可能就是正确结果，最终以“实际结果是否符合预期”为准。

## 一、测试用例

| 编号 | 测试场景 | 操作方式 | 预期结果 | 监控 / 日志检查 | 当前状态 |
|---|---|---|---|---|---|
| TC-001 | 2025-03-26 客户端访问 2025-03-26 服务 | 启动对应测试程序，执行工具列表查询和测试工具调用 | 请求成功，能够获取工具列表并正常调用工具 | 请求数、成功数增加；日志无协议错误 | 已通过 |
| TC-002 | 2025-06-18 客户端访问 2025-06-18 服务 | 启动对应测试程序，执行工具列表查询和测试工具调用 | 请求成功 | 请求数、成功数增加；协议版本正确 | 已通过 |
| TC-003 | 2025-11-25 客户端访问 2025-11-25 服务 | 启动对应测试程序，执行工具列表查询和测试工具调用 | 请求成功 | 请求数、成功数增加；协议版本正确 | 已通过 |
| TC-004 | 2026-07-28 客户端访问 2026-07-28 服务 | 启动对应测试程序，执行服务发现和测试工具调用 | 请求成功 | 请求数、成功数增加；协议版本正确 | 已通过 |
| TC-005 | 2025-03-26 客户端通过 SSE 访问同版本服务 | 启动 SSE 测试程序并执行工具调用 | 请求成功，SSE 会话可正常建立和释放 | Legacy SSE 连接数、Session 创建/删除正常 | 已通过 |
| TC-006 | 2025-06-18 客户端通过 SSE 访问同版本服务 | 同上 | 请求成功 | Legacy SSE 指标正常 | 已通过 |
| TC-007 | 2025-11-25 客户端通过 SSE 访问同版本服务 | 同上 | 请求成功 | Legacy SSE 指标正常 | 已通过 |
| TC-008 | 2026-07-28 客户端使用 SSE | 启动 2026 SSE 测试程序 | 请求失败，系统明确拒绝不支持的协议/传输组合 | 失败原因应为协议或传输不兼容 | 已通过 |
| TC-009 | 2025 客户端访问 2026 服务 | 启动 2025 客户端，但目标选择 2026 服务 | 请求失败，明确提示协议版本不匹配 | 请求经过网关并到达目标服务，最终协议失败 | 已通过 |
| TC-010 | 2026 客户端访问 2025 服务 | 启动 2026 客户端，但目标选择 2025 服务 | 请求最终失败，不能误判为 2026 调用成功 | 可看到服务发现失败 / 版本降级尝试 / 最终版本不符 | 已通过 |
| TC-011 | HTTP 客户端访问 SSE 服务 | 使用 HTTP 模式访问 SSE 地址 | 请求失败 | 失败原因应为传输方式不匹配 | 已通过 |
| TC-012 | SSE 客户端访问 HTTP 服务 | 使用 SSE 模式访问 HTTP 地址 | 请求失败 | 失败原因应为传输方式不匹配 | 已通过 |
| TC-013 | 正常申请访问凭证 | 使用正确测试账号申请 Token | 成功返回访问凭证 | Token 签发成功日志；tokenApply success 指标增加 | 已通过 |
| TC-014 | 未携带访问凭证访问服务 | 直接发起 MCP 请求，不带 Token | 网关直接拒绝，请求不能到后端服务 | 网关鉴权失败；后端服务无对应请求 | 已通过 |
| TC-015 | 使用被篡改的访问凭证 | 修改 Token 后访问服务 | 网关直接拒绝 | JWT 验签失败；后端服务无对应请求 | 已通过 |
| TC-016 | 使用错误账号凭证申请 Token | 使用错误 clientSecret 调用 tokenApply | 返回 401 | tokenApply invalid_credentials 指标增加 | 已通过 |
| TC-017 | 10 分钟持续压测（正常 2025） | 每秒随机 1~5 个案例，持续 10 分钟 | 服务保持可用；记录成功率、延迟、429、CPU/JVM | Grafana 中查看吞吐、P95/P99、CPU、内存、429 | 已执行 |
| TC-018 | 10 分钟持续压测（正常 2026） | 每秒随机 1~5 个案例，持续 10 分钟 | 服务保持可用；记录成功率、延迟、429、CPU/JVM | 同上 | 已执行 |
| TC-019 | 10 分钟持续异常压测（跨版本） | 2025→2026、2026→2025，每秒随机 1~5 个案例，持续 10 分钟 | 请求应持续按预期失败，不应误调用成功 | 重点看协议错误、429、CPU/JVM | 已执行 |
| TC-020 | 用户 QPS 超限 | 同一用户瞬时大量请求 | 超过用户 QPS 限制后返回限流错误 | 错误码 OPEN090002；dimension=user | 已验证 |
| TC-021 | 用户并发超限 | 同一用户同时保持大量在途请求 | 超过并发上限后返回网关繁忙 | 错误码 OPEN090005；dimension=concurrency | 已验证 |
| TC-022 | 使用过期 Token | 使用已过期访问凭证请求服务 | 网关拒绝，请求不到后端 | 鉴权失败日志 | 待执行 |
| TC-023 | 无服务权限访问 | 使用有效 Token 访问未授权服务 | 网关拒绝，请求不到后端 | 权限拒绝日志 | 待执行 |
| TC-024 | 请求不存在的服务地址 | 请求不存在的 Gateway 路由 | 请求失败，返回明确错误 | route=unknown 或未匹配路由日志 | 待执行 |
| TC-025 | 后端服务不可达 | 将测试路由指向不可访问的服务 | 网关返回上游连接失败 | upstream failed / connection 日志 | 待执行 |
| TC-026 | 后端服务响应超时 | 测试服务故意延迟超过超时时间 | 网关返回超时 | timeout 指标和日志增加 | 待执行 |
| TC-027 | 熔断测试 | 连续制造上游失败直到达到阈值 | 熔断器打开，后续请求快速失败；恢复后进入半开并最终关闭 | Circuit Breaker 状态变化 | 待执行 |
| TC-028 | tokenApply 高频调用 | 高频重复申请 Token | 超过 tokenApply 独立限额后返回 429 | dimension=token-apply | 待执行 |

## 二、测试老师如何执行

测试老师不需要理解 MCP 协议细节，只需要：

1. 按测试用例编号启动对应测试程序。
2. 等待程序完成。
3. 对照“预期结果”判断实际表现。
4. 在 Grafana 的 **MCP Gateway 监控** 页面确认对应请求、成功、失败和资源指标。
5. 如测试失败，将测试时间、用例编号和错误提示提供给开发人员排查。

异常用例请特别注意：

> 请求被拒绝或调用失败，不代表测试失败。  
> 只要“实际结果”和“预期结果”一致，测试结论就是通过。

## 三、科技人员执行方式

以下内容主要供开发 / 科技人员复现问题，测试老师无需关注。

### 1. 2025 正常调用

```bash
python -m client.main \
  --protocol 2025-11-25 \
  --transport streamable-http \
  --url http://127.0.0.1:8080/py/http/2025-11-25 \
  --auth-profile 2025 \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

### 2. 2026 正常调用

```bash
python -m client.main \
  --protocol 2026-07-28 \
  --transport streamable-http \
  --url http://127.0.0.1:8080/py/http/2026-07-28 \
  --auth-profile 2026 \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

### 3. 2025 客户端访问 2026 服务

```bash
python -m client.main \
  --protocol 2025-11-25 \
  --transport streamable-http \
  --url http://127.0.0.1:8080/py/http/2026-07-28 \
  --auth-profile 2025 \
  --action list
```

### 4. SSE 调用

```bash
python -m client.main \
  --protocol 2025-11-25 \
  --transport sse \
  --url http://127.0.0.1:8080/py/sse/2025-11-25/sse \
  --auth-profile 2025 \
  --action call \
  --tool get_protocol_info \
  --args '{}'
```

### 5. 无 Token 调用

```bash
python -m client.main \
  --protocol 2025-11-25 \
  --transport streamable-http \
  --url http://127.0.0.1:8080/py/http/2025-11-25 \
  --auth-profile none \
  --action list
```

## 四、日志打印建议

每个案例至少打印以下信息：

```text
CASE=TC-009
CLIENT_PROTOCOL=2025-11-25
TARGET=/py/http/2026-07-28
EXPECTED=FAIL
ACTUAL=FAIL
HTTP_STATUS=200
RESULT=PASS
DURATION_MS=37
```

正常案例示例：

```text
CASE=TC-003
CLIENT_PROTOCOL=2025-11-25
TARGET=/py/http/2025-11-25
SERVER_PROTOCOL=2025-11-25
ACTION=tools/call
EXPECTED=SUCCESS
ACTUAL=SUCCESS
HTTP_STATUS=200
RESULT=PASS
DURATION_MS=74
```

限流日志需要明确区分原因：

```text
HTTP=429
ERROR_CODE=OPEN090002
LIMIT_TYPE=user_qps
userId=py-client-2026
capacity=100
refill=20
```

或者：

```text
HTTP=429
ERROR_CODE=OPEN090005
LIMIT_TYPE=concurrency
userId=py-client-2026
limit=100
```

## 五、Gateway 日志建议保留字段

```text
requestId
userId
mcpServerId
method
tool
protocolVersion
target/upstream
HTTP status
Gateway error code
duration
```

示例：

```text
requestId=xxx
userId=py-client-2025
mcpServerId=py-http-2026-07-28
method=initialize
protocolVersion=2025-11-25
upstream=http://127.0.0.1:8104/mcp
status=200
mcpError=-32022
```

## 六、监控查看

Grafana 中使用：

**MCP Gateway 监控**

重点关注：

- 请求总量
- 成功 / 失败数量
- P95 / P99 延迟
- QPS 限流次数
- 并发超限次数
- Circuit Breaker 状态
- JVM 内存
- CPU
- 上游连接池
- Legacy SSE Session
- protocol_version
- mcp_transport
