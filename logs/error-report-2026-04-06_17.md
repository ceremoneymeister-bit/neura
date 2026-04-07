# Neura v2 Error Monitor — 2026-04-06 17:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 10
- Warnings: 0

## Errors by capsule

### unknown (10 errors)
```
Apr 06 17:22:17 sweet-coffee.ptr.network python3[1280102]: 2026-04-06 17:22:17,823 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 06 17:22:17 sweet-coffee.ptr.network python3[1280102]: httpcore.ReadError
```
```
Apr 06 17:22:17 sweet-coffee.ptr.network python3[1280102]: httpx.ReadError
```
```
Apr 06 17:22:17 sweet-coffee.ptr.network python3[1280102]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 17:22:17 sweet-coffee.ptr.network python3[1280102]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
