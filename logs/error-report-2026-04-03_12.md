# Neura v2 Error Monitor — 2026-04-03 12:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 4990
- Warnings: 0

## Errors by capsule

### unknown (4990 errors)
```
Apr 03 12:44:58 qfqcnqhoqr python3[50816]: FileNotFoundError: [Errno 2] No such file or directory: '/opt/neura-v2/-m'
```
```
Apr 03 12:44:58 qfqcnqhoqr python3[50816]: httpcore.ConnectError: [Errno -3] Temporary failure in name resolution
```
```
Apr 03 12:44:58 qfqcnqhoqr python3[50816]: httpx.ConnectError: [Errno -3] Temporary failure in name resolution
```
```
Apr 03 12:44:58 qfqcnqhoqr python3[50816]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 03 12:44:58 qfqcnqhoqr python3[50816]: telegram.error.NetworkError: httpx.ConnectError: [Errno -3] Temporary failure in name resolution
```

## Requests per capsule
