# Neura v2 Error Monitor — 2026-04-04 08:45
> Period: since 1 hour ago

## Summary
- Requests: 1
- Errors: 10
- Warnings: 12

## Errors by capsule

### unknown (10 errors)
```
Apr 04 08:15:59 sweet-coffee.ptr.network python3[887512]: 2026-04-04 08:15:59,404 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 04 08:15:59 sweet-coffee.ptr.network python3[887512]: httpcore.ReadError
```
```
Apr 04 08:15:59 sweet-coffee.ptr.network python3[887512]: httpx.ReadError
```
```
Apr 04 08:15:59 sweet-coffee.ptr.network python3[887512]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 04 08:15:59 sweet-coffee.ptr.network python3[887512]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
- dmitry_test: 1
