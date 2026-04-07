# Neura v2 Error Monitor — 2026-04-04 21:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 25
- Warnings: 0

## Errors by capsule

### unknown (25 errors)
```
Apr 04 21:44:16 sweet-coffee.ptr.network python3[1018879]: 2026-04-04 21:44:16,668 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 04 21:44:16 sweet-coffee.ptr.network python3[1018879]: httpcore.ReadError
```
```
Apr 04 21:44:16 sweet-coffee.ptr.network python3[1018879]: httpx.ReadError
```
```
Apr 04 21:44:16 sweet-coffee.ptr.network python3[1018879]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 04 21:44:16 sweet-coffee.ptr.network python3[1018879]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
