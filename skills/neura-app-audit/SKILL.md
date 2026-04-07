---
name: neura-app-audit
description: "Аудит branding Neura App — pre-deploy чеклист для branding.js и neura-ui.css"
version: 1.0.0
category: infrastructure
tags: [neura-app, audit, branding, deploy, checklist]
usage_count: 0
maturity: seed
last_used: null
proactive_enabled: true
proactive_trigger_1_type: event
proactive_trigger_1_condition: "перед деплоем Neura App"
proactive_trigger_1_action: "запустить полный аудит branding"
proactive_trigger_2_type: schedule
proactive_trigger_2_condition: "еженедельно понедельник"
proactive_trigger_2_action: "проверить neura-ui.css и branding.js"
learning_track_success: true
learning_track_corrections: true
learning_evolve_threshold: 5
learning_auto_update: [anti-patterns, triggers, changelog]
---

# Neura App Audit — Branding Pre-Deploy Checklist

## Триггеры
- «аудит Neura App», «проверь логин», «branding audit»
- «деплой branding», «обновить branding.js», «обновить neura-ui.css»
- Перед ЛЮБЫМ изменением в `/opt/neura-app/branding/`

## Pre-deploy чеклист

### 1. Валидация файлов
```bash
node -c /opt/neura-app/branding/branding.js  # Синтаксис JS
```
- [ ] CSS: нет незакрытых скобок
- [ ] Нет дублированных DOM ID (`getElementById` guard перед `createElement`)
- [ ] Нет `setInterval`/`setTimeout` без очистки → использовать `neuraSetInterval()` или `loginTimer()`

### 2. Дисциплина таймеров
- [ ] Глобальные интервалы → `neuraSetInterval()` (сохраняет ID в `__neura_intervals`)
- [ ] Login-страничные таймеры → `loginTimer(fn, ms, isInterval)` (сохраняет в `__loginTimers`)
- [ ] `cleanupLoginPage()` вызывает `clearLoginTimers()` ПЕРЕД удалением DOM
- [ ] Рекурсивный `setTimeout` проверяет существование DOM-элемента (early return)

### 3. CSS правила
- [ ] Нет дублей одного селектора (проверить: `button[type="submit"]`, `input[name=`, `img[src*="logo"]`)
- [ ] Dark mode: `.dark body.X` или `body.X.dark` (НЕ `body.X .dark Y`)
- [ ] Login-скоупд: `body.neura-login-page` префикс
- [ ] Анимации в `@keyframes` имеют ссылки в правилах (нет orphaned animations)

### 4. DOM-инъекции
- [ ] Каждый `createElement` → проверка `getElementById` перед ним
- [ ] Каждый созданный элемент удаляется в cleanup-функции
- [ ] `querySelectorAll` скоупится на ближайший контейнер, НЕ на `document`

### 5. Темы (dark/light)
- [ ] Только ОДНА кнопка toggle (LibreChat native `ThemeSelector`)
- [ ] Кастомный toggle НЕ создаётся (удалён из setupLoginPage)
- [ ] CSS для обоих режимов проверен

## Частые ошибки

### Memory Leaks
- Рекурсивный `setTimeout` в typing-демо без `clearLoginTimers()`
- `setInterval` для mic/auth/navigation/badge — всегда через `neuraSetInterval()`
- `MutationObserver` без `disconnect()` при навигации

### Дублирование
- setupLoginPage() + injectThemeToggle() — оба создавали toggle
- Два определения `button[type="submit"]` в CSS — второе перезаписывает первое
- `localizeLoginPage()` без скоупинга заменяла текст за пределами формы

### CSS Specificity
- `body.neura-login-page button[type="submit"]` > `button[type="submit"]`
- `!important` — минимально, лучше выше специфичность
- Dark mode: `.dark` на `<html>` (LibreChat) И на `<body>` (наш JS)

## Протокол тестирования

### Playwright скриншоты (6 штук)
```bash
for viewport in "375,812" "768,1024" "1440,900"; do
  for theme in "light" "dark"; do
    playwright screenshot \
      --wait-for-timeout 5000 \
      --viewport-size "$viewport" \
      "https://app.ceremoneymeister.ru/login?v=$(date +%s)&theme=$theme" \
      "/tmp/neura-audit/login-${viewport}-${theme}.png"
  done
done
```

### Ручная проверка
- [ ] Login: hero слева, форма справа (desktop)
- [ ] Login: hero сверху, форма снизу (mobile)
- [ ] Только 1 toggle (слева внизу, от LibreChat)
- [ ] Typing-демо анимируется, зацикленно
- [ ] Кнопка «Продолжить»: glow-анимация
- [ ] Dark mode: все элементы переключаются
- [ ] Навигация: /login → /chat → /login — нет дублей, нет JS-ошибок
- [ ] DevTools Performance: нет роста таймеров за 60с
- [ ] Mobile: нет горизонтального скролла

## Правила разработки branding.js

### ES5!
- `var`, `function` — НЕ `const`, `let`, `=>`
- НЕ `async/await`, НЕ template literals
- Тестировать в Safari iOS

### Таймеры
- НИКОГДА bare `setInterval()` на уровне модуля
- Login → `loginTimer()`, глобальные → `neuraSetInterval()`
- `cleanupLoginPage()` = первое что вызывается при уходе с /login

### DOM
- `getElementById` guard перед `createElement`
- Cleanup зеркалит creation
- Selectors скоупятся на контейнер

### CSS через JS
- `injectGlobalStyles()` pattern: проверка по ID стиль-элемента
- `body.neura-login-page` для login-specific

---

## Changelog

<!-- Сюда автоматически добавляются уроки после каждого использования скилла -->
