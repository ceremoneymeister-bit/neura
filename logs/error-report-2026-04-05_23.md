# Neura v2 Error Monitor — 2026-04-05 23:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 15
- Warnings: 0

## Errors by capsule

### unknown (15 errors)
```
Apr 05 23:05:20 sweet-coffee.ptr.network python3[1062760]: 2026-04-05 23:05:20,063 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 05 23:05:20 sweet-coffee.ptr.network python3[1062760]: httpcore.ReadError
```
```
Apr 05 23:05:20 sweet-coffee.ptr.network python3[1062760]: httpx.ReadError
```
```
Apr 05 23:05:20 sweet-coffee.ptr.network python3[1062760]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 05 23:05:20 sweet-coffee.ptr.network python3[1062760]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
