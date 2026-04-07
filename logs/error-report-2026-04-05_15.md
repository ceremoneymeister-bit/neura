# Neura v2 Error Monitor — 2026-04-05 15:45
> Period: since 1 hour ago

## Summary
- Requests: 1
- Errors: 5
- Warnings: 0

## Errors by capsule

### unknown (5 errors)
```
Apr 05 14:49:26 sweet-coffee.ptr.network python3[1062760]: 2026-04-05 14:49:26,635 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 05 14:49:26 sweet-coffee.ptr.network python3[1062760]: httpcore.ReadError
```
```
Apr 05 14:49:26 sweet-coffee.ptr.network python3[1062760]: httpx.ReadError
```
```
Apr 05 14:49:26 sweet-coffee.ptr.network python3[1062760]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 05 14:49:26 sweet-coffee.ptr.network python3[1062760]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
- victoria_sel: 1
