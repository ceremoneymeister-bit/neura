# Neura v2 Error Monitor — 2026-04-05 11:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 25
- Warnings: 0

## Errors by capsule

### unknown (25 errors)
```
Apr 05 11:42:27 sweet-coffee.ptr.network python3[1051152]: 2026-04-05 11:42:27,059 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 05 11:42:27 sweet-coffee.ptr.network python3[1051152]: httpcore.ReadError
```
```
Apr 05 11:42:27 sweet-coffee.ptr.network python3[1051152]: httpx.ReadError
```
```
Apr 05 11:42:27 sweet-coffee.ptr.network python3[1051152]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 05 11:42:27 sweet-coffee.ptr.network python3[1051152]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
