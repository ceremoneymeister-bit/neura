# Neura v2 Error Monitor — 2026-04-04 14:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 10
- Warnings: 0

## Errors by capsule

### unknown (10 errors)
```
Apr 04 14:27:37 sweet-coffee.ptr.network python3[937165]: 2026-04-04 14:27:37,571 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 04 14:27:37 sweet-coffee.ptr.network python3[937165]: httpcore.ReadError
```
```
Apr 04 14:27:37 sweet-coffee.ptr.network python3[937165]: httpx.ReadError
```
```
Apr 04 14:27:37 sweet-coffee.ptr.network python3[937165]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 04 14:27:37 sweet-coffee.ptr.network python3[937165]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
