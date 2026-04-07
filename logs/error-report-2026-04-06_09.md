# Neura v2 Error Monitor — 2026-04-06 09:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 28
- Warnings: 7

## Errors by capsule

### unknown (28 errors)
```
Apr 06 09:28:57 sweet-coffee.ptr.network python3[1154614]: 2026-04-06 09:28:57,079 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 06 09:28:57 sweet-coffee.ptr.network python3[1154614]: httpcore.ReadError
```
```
Apr 06 09:28:57 sweet-coffee.ptr.network python3[1154614]: httpx.ReadError
```
```
Apr 06 09:28:57 sweet-coffee.ptr.network python3[1154614]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 09:28:57 sweet-coffee.ptr.network python3[1154614]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
