# Neura v2 Error Monitor — 2026-04-04 20:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 15
- Warnings: 0

## Errors by capsule

### unknown (15 errors)
```
Apr 04 20:05:18 sweet-coffee.ptr.network python3[1018879]: 2026-04-04 20:05:18,027 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 04 20:05:18 sweet-coffee.ptr.network python3[1018879]: httpcore.ReadError
```
```
Apr 04 20:05:18 sweet-coffee.ptr.network python3[1018879]: httpx.ReadError
```
```
Apr 04 20:05:18 sweet-coffee.ptr.network python3[1018879]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 04 20:05:18 sweet-coffee.ptr.network python3[1018879]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
