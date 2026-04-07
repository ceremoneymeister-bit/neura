# Neura v2 Error Monitor — 2026-04-06 21:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 35
- Warnings: 0

## Errors by capsule

### unknown (35 errors)
```
Apr 06 21:42:03 sweet-coffee.ptr.network python3[1319440]: 2026-04-06 21:42:03,235 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 06 21:42:03 sweet-coffee.ptr.network python3[1319440]: httpcore.ReadError
```
```
Apr 06 21:42:03 sweet-coffee.ptr.network python3[1319440]: httpx.ReadError
```
```
Apr 06 21:42:03 sweet-coffee.ptr.network python3[1319440]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 21:42:03 sweet-coffee.ptr.network python3[1319440]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
