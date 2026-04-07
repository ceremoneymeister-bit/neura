# Neura v2 Error Monitor — 2026-04-07 11:45
> Period: since 1 hour ago

## Summary
- Requests: 2
- Errors: 16
- Warnings: 10

## Errors by capsule

### unknown (16 errors)
```
Apr 07 11:25:32 sweet-coffee.ptr.network python3[1495598]: 2026-04-07 11:25:32,400 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 07 11:25:32 sweet-coffee.ptr.network python3[1495598]: httpcore.ReadError
```
```
Apr 07 11:25:32 sweet-coffee.ptr.network python3[1495598]: httpx.ReadError
```
```
Apr 07 11:25:32 sweet-coffee.ptr.network python3[1495598]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 07 11:25:32 sweet-coffee.ptr.network python3[1495598]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
- oksana_ksyfleur: 2
