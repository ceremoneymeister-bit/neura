# Neura v2 Error Monitor — 2026-04-06 20:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 34
- Warnings: 40

## Errors by capsule

### unknown (34 errors)
```
Apr 06 20:30:41 sweet-coffee.ptr.network python3[1319440]: 2026-04-06 20:30:41,551 [telegram.ext.Updater] ERROR: Exception happened while polling for updates.
```
```
Apr 06 20:30:41 sweet-coffee.ptr.network python3[1319440]: httpcore.ReadError
```
```
Apr 06 20:30:41 sweet-coffee.ptr.network python3[1319440]: httpx.ReadError
```
```
Apr 06 20:30:41 sweet-coffee.ptr.network python3[1319440]:     raise NetworkError(f"httpx.{err.__class__.__name__}: {err}") from err
```
```
Apr 06 20:30:41 sweet-coffee.ptr.network python3[1319440]: telegram.error.NetworkError: httpx.ReadError:
```

## Requests per capsule
