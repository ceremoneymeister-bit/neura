# Neura v2 Error Monitor — 2026-04-07 12:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 36
- Warnings: 12

## Errors by capsule

### unknown (36 errors)
```
Apr 07 12:31:13 sweet-coffee.ptr.network python3[1509811]: telegram.error.TimedOut: Timed out
```
```
Apr 07 12:31:13 sweet-coffee.ptr.network python3[1509811]: Error in sys.excepthook:
```
```
Apr 07 12:31:13 sweet-coffee.ptr.network python3[1509811]: FileNotFoundError: [Errno 2] No such file or directory: '/opt/neura-v2/-m'
```
```
Apr 07 12:31:13 sweet-coffee.ptr.network python3[1509811]: telegram.error.TimedOut: Timed out
```
```
thon3[1509949]: 2026-04-07 12:32:26,698 [neura.core.proactive] INFO: 🔔 Proactive trigger fired: systematic-debugging [threshold: errors_today > 5 в journalctl/Docker] → запустить проактивную форензику
```

## Requests per capsule
