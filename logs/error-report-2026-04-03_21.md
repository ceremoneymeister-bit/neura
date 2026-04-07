# Neura v2 Error Monitor — 2026-04-03 21:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 5
- Warnings: 0

## Errors by capsule

### unknown (5 errors)
```
Apr 03 20:47:25 sweet-coffee.ptr.network python3[713783]: 2026-04-03 20:47:25,065 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 03 20:47:25 sweet-coffee.ptr.network python3[713783]: httpcore.ReadError
```
```
Apr 03 20:47:25 sweet-coffee.ptr.network python3[713783]: httpx.ReadError
```
```
Apr 03 20:47:25 sweet-coffee.ptr.network python3[713783]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 03 20:47:25 sweet-coffee.ptr.network python3[713783]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
