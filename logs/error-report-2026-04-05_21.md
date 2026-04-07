# Neura v2 Error Monitor — 2026-04-05 21:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 35
- Warnings: 0

## Errors by capsule

### unknown (35 errors)
```
Apr 05 21:44:25 sweet-coffee.ptr.network python3[1062760]: 2026-04-05 21:44:25,119 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 05 21:44:25 sweet-coffee.ptr.network python3[1062760]: httpcore.ReadError
```
```
Apr 05 21:44:25 sweet-coffee.ptr.network python3[1062760]: httpx.ReadError
```
```
Apr 05 21:44:25 sweet-coffee.ptr.network python3[1062760]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 05 21:44:25 sweet-coffee.ptr.network python3[1062760]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
