# Neura v2 Error Monitor — 2026-04-03 11:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 976
- Warnings: 0

## Errors by capsule

### unknown (976 errors)
```
Apr 03 11:44:57 qfqcnqhoqr python3[1871917]: FileNotFoundError: [Errno 2] No such file or directory: '/opt/neura-v2/-m'
```
```
Apr 03 11:44:57 qfqcnqhoqr python3[1871917]: httpcore.ConnectError: [Errno -3] Temporary failure in name resolution
```
```
Apr 03 11:44:57 qfqcnqhoqr python3[1871917]: httpx.ConnectError: [Errno -3] Temporary failure in name resolution
```
```
Apr 03 11:44:57 qfqcnqhoqr python3[1871917]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 03 11:44:57 qfqcnqhoqr python3[1871917]: telegram.error.NetworkError: httpx.ConnectError: [Errno -3] Temporary failure in name resolution
```

## Requests per capsule
