# Neura v2 Error Monitor — 2026-04-06 13:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 53
- Warnings: 9

## Errors by capsule

### unknown (53 errors)
```
Apr 06 13:30:07 sweet-coffee.ptr.network python3[1255949]: FileNotFoundError: [Errno 2] No such file or directory: '/opt/neura-v2/-m'
```
```
Apr 06 13:30:07 sweet-coffee.ptr.network python3[1255949]: httpcore.ReadError
```
```
Apr 06 13:30:07 sweet-coffee.ptr.network python3[1255949]: httpx.ReadError
```
```
Apr 06 13:30:07 sweet-coffee.ptr.network python3[1255949]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 13:30:07 sweet-coffee.ptr.network python3[1255949]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
