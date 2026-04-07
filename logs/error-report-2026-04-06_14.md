# Neura v2 Error Monitor — 2026-04-06 14:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 68
- Warnings: 9

## Errors by capsule

### unknown (68 errors)
```
Apr 06 14:31:29 sweet-coffee.ptr.network python3[1280102]: 2026-04-06 14:31:29,371 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 06 14:31:29 sweet-coffee.ptr.network python3[1280102]: httpcore.ReadError
```
```
Apr 06 14:31:29 sweet-coffee.ptr.network python3[1280102]: httpx.ReadError
```
```
Apr 06 14:31:29 sweet-coffee.ptr.network python3[1280102]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 14:31:29 sweet-coffee.ptr.network python3[1280102]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
