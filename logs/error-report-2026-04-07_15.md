# Neura v2 Error Monitor — 2026-04-07 15:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 13
- Warnings: 0

## Errors by capsule

### unknown (13 errors)
```
Apr 07 15:35:36 sweet-coffee.ptr.network python3[1547798]: 2026-04-07 15:35:36,243 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 07 15:35:36 sweet-coffee.ptr.network python3[1547798]: httpcore.ReadError
```
```
Apr 07 15:35:36 sweet-coffee.ptr.network python3[1547798]: httpx.ReadError
```
```
Apr 07 15:35:36 sweet-coffee.ptr.network python3[1547798]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 07 15:35:36 sweet-coffee.ptr.network python3[1547798]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
