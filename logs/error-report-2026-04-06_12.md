# Neura v2 Error Monitor — 2026-04-06 12:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 5
- Warnings: 3

## Errors by capsule

### unknown (5 errors)
```
Apr 06 12:31:17 sweet-coffee.ptr.network python3[1212153]: 2026-04-06 12:31:17,590 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 06 12:31:17 sweet-coffee.ptr.network python3[1212153]: httpcore.ReadError
```
```
Apr 06 12:31:17 sweet-coffee.ptr.network python3[1212153]: httpx.ReadError
```
```
Apr 06 12:31:17 sweet-coffee.ptr.network python3[1212153]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 12:31:17 sweet-coffee.ptr.network python3[1212153]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
