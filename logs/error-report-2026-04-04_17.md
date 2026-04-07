# Neura v2 Error Monitor — 2026-04-04 17:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 23
- Warnings: 40

## Errors by capsule

### unknown (23 errors)
```
Apr 04 17:41:52 sweet-coffee.ptr.network python3[998010]:     raise exceptions.IncompleteReadError(incomplete, n)
```
```
Apr 04 17:41:52 sweet-coffee.ptr.network python3[998010]: asyncio.exceptions.IncompleteReadError: 0 bytes read on a total of 2 expected bytes
```
```
Apr 04 17:41:52 sweet-coffee.ptr.network python3[998010]: websockets.exceptions.ConnectionClosedError: no close frame received or sent
```
```
Apr 04 17:41:52 sweet-coffee.ptr.network python3[998010]:   File "/usr/local/lib/python3.12/dist-packages/starlette/middleware/errors.py", line 151, in __call__
```
```
Apr 04 17:41:52 sweet-coffee.ptr.network python3[998010]:     await websocket.send_json({"type": "error", "content": "Conversation not found"})
```

## Requests per capsule
