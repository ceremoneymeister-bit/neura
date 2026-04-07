# Neura v2 Error Monitor — 2026-04-07 07:45
> Period: since 1 hour ago

## Summary
- Requests: 0
- Errors: 10
- Warnings: 45

## Errors by capsule

### unknown (10 errors)
```
Apr 07 07:22:34 sweet-coffee.ptr.network python3[1373967]: 2026-04-07 07:22:34,092 [neura.transport.telegram] INFO: [maxim_belousov] Session invalidated after error, will start fresh next time
```
```
Apr 07 07:22:34 sweet-coffee.ptr.network python3[1373967]: 2026-04-07 07:22:34,092 [neura.transport.telegram] WARNING: [maxim_belousov] Replacing error response with user-friendly message
```
```
fee.ptr.network python3[1410501]: 2026-04-07 07:23:37,465 [neura.core.capsule] ERROR: Failed to load capsule maxim_anastasia_velikaya.yaml: Environment variable ${ANASTASIA_VELIKAYA_BOT_TOKEN} not set
```
```
thon3[1410501]: 2026-04-07 07:24:37,942 [neura.core.proactive] INFO: 🔔 Proactive trigger fired: systematic-debugging [threshold: errors_today > 5 в journalctl/Docker] → запустить проактивную форензику
```
```
thon3[1412715]: 2026-04-07 07:26:32,019 [neura.core.proactive] INFO: 🔔 Proactive trigger fired: systematic-debugging [threshold: errors_today > 5 в journalctl/Docker] → запустить проактивную форензику
```

## Requests per capsule
