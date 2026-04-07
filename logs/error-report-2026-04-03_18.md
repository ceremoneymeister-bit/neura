# Neura v2 Error Monitor — 2026-04-03 18:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 7
- Warnings: 0

## Errors by capsule

### unknown (7 errors)
```
Apr 03 18:00:42 sweet-coffee.ptr.network python3[666974]: telegram.error.TimedOut: Timed out
```
```
r.network python3[706775]: 2026-04-03 18:02:36,240 [neura.core.proactive] INFO: 🔔 Proactive trigger fired: error-tracker [schedule: ежедневно 21:00] → агрегировать ошибки из journalctl + Docker + cron
```
```
error to ensure graceful shutdown. When polling for updates is restarted, updates may be fetched again. Please adjust timeouts via `ApplicationBuilder` or the parameter `get_updates_request` of `Bot`.
```
```
Apr 03 18:24:27 sweet-coffee.ptr.network python3[706775]: telegram.error.TimedOut: Timed out
```
```
r.network python3[713783]: 2026-04-03 18:25:32,479 [neura.core.proactive] INFO: 🔔 Proactive trigger fired: error-tracker [schedule: ежедневно 21:00] → агрегировать ошибки из journalctl + Docker + cron
```

## Requests per capsule
