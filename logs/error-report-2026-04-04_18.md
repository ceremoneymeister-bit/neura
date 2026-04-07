# Neura v2 Error Monitor — 2026-04-04 18:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 61
- Warnings: 0

## Errors by capsule

### unknown (61 errors)
```
Apr 04 18:29:58 sweet-coffee.ptr.network python3[1010915]: telegram.error.TimedOut: Timed out
```
```
Apr 04 18:29:58 sweet-coffee.ptr.network python3[1010915]: Error in sys.excepthook:
```
```
Apr 04 18:29:58 sweet-coffee.ptr.network python3[1010915]: FileNotFoundError: [Errno 2] No such file or directory: '/opt/neura-v2/-m'
```
```
Apr 04 18:29:58 sweet-coffee.ptr.network python3[1010915]: telegram.error.TimedOut: Timed out
```
```
.network python3[1010939]: 2026-04-04 18:31:10,364 [neura.core.proactive] INFO: 🔔 Proactive trigger fired: error-tracker [schedule: ежедневно 21:00] → агрегировать ошибки из journalctl + Docker + cron
```

## Requests per capsule
