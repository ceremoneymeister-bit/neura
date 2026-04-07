# Neura v2 Error Monitor — 2026-04-05 10:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 5
- Warnings: 0

## Errors by capsule

### unknown (5 errors)
```
Apr 05 09:45:20 sweet-coffee.ptr.network python3[1051152]: 2026-04-05 09:45:20,631 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 05 09:45:20 sweet-coffee.ptr.network python3[1051152]: httpcore.ReadError
```
```
Apr 05 09:45:20 sweet-coffee.ptr.network python3[1051152]: httpx.ReadError
```
```
Apr 05 09:45:20 sweet-coffee.ptr.network python3[1051152]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 05 09:45:20 sweet-coffee.ptr.network python3[1051152]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
