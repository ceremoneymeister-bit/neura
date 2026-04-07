# Neura v2 Error Monitor — 2026-04-07 05:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 11
- Warnings: 68

## Errors by capsule

### unknown (11 errors)
```
Apr 07 05:41:28 sweet-coffee.ptr.network python3[1367755]: 2026-04-07 05:41:28,663 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 07 05:41:28 sweet-coffee.ptr.network python3[1367755]: httpcore.ReadError
```
```
Apr 07 05:41:28 sweet-coffee.ptr.network python3[1367755]: httpx.ReadError
```
```
Apr 07 05:41:28 sweet-coffee.ptr.network python3[1367755]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 07 05:41:28 sweet-coffee.ptr.network python3[1367755]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
