# Neura v2 Error Monitor — 2026-04-05 03:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 14
- Warnings: 2

## Errors by capsule

### unknown (14 errors)
```
Apr 05 03:27:24 sweet-coffee.ptr.network python3[1018879]: telegram.error.Conflict: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
```
```
 error chunk: Failed to authenticate. API Error: 401 {"type":"error","error":{"type":"authentication_error","message":"Invalid authentication credentials"},"request_id":"req_011CZjvPtvQLcQX8kc9FcybH"}
```
```
Apr 05 03:33:49 sweet-coffee.ptr.network python3[1018879]: 2026-04-05 03:33:49,437 [neura.transport.telegram] WARNING: [maxim_belousov] Replacing error response with user-friendly message
```
```
 401 {"type":"error","error":{"type":"authentication_error","message":"OAuth token has expired. Please obtain a new token or refresh your existing token."},"request_id":"req_011CZjvnsPXDXwdhr9L4VR3k"}
```
```
Apr 05 03:39:01 sweet-coffee.ptr.network python3[1018879]: 2026-04-05 03:39:01,168 [neura.transport.telegram] WARNING: [maxim_belousov] Replacing error response with user-friendly message
```

## Requests per capsule
