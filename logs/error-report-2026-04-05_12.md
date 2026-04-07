# Neura v2 Error Monitor — 2026-04-05 12:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 10
- Warnings: 0

## Errors by capsule

### unknown (10 errors)
```
Apr 05 12:33:25 sweet-coffee.ptr.network python3[1051152]: 2026-04-05 12:33:25,395 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 05 12:33:25 sweet-coffee.ptr.network python3[1051152]: httpcore.ReadError
```
```
Apr 05 12:33:25 sweet-coffee.ptr.network python3[1051152]: httpx.ReadError
```
```
Apr 05 12:33:25 sweet-coffee.ptr.network python3[1051152]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 05 12:33:25 sweet-coffee.ptr.network python3[1051152]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
