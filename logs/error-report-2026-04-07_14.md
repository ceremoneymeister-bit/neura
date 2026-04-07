# Neura v2 Error Monitor — 2026-04-07 14:45
> Period: since 1 hour ago

## Summary
- Requests: 1
- Errors: 6
- Warnings: 3

## Errors by capsule

### unknown (6 errors)
```
Apr 07 14:33:53 sweet-coffee.ptr.network python3[1547798]: 2026-04-07 14:33:53,691 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 07 14:33:53 sweet-coffee.ptr.network python3[1547798]: httpcore.ReadError
```
```
Apr 07 14:33:53 sweet-coffee.ptr.network python3[1547798]: httpx.ReadError
```
```
Apr 07 14:33:53 sweet-coffee.ptr.network python3[1547798]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 07 14:33:53 sweet-coffee.ptr.network python3[1547798]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
- maxim_anastasia_velikaya: 1
