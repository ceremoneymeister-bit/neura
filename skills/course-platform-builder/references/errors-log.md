# Лог ошибок: создание course-platform

## Ошибка 1: JSX в .js файле (CRITICAL — build fails)

**Когда:** Шаг 4 (Auth) — создание `useAuth.js`
**Симптом:** `vite build` падает с `Expression expected` на строке с `<AuthContext.Provider>`
**Причина:** Rollup/Vite не парсит JSX в файлах с расширением `.js`
**Исправление:** Переименовать `useAuth.js` → `useAuth.jsx`, обновить все 7 импортов
**Файлы затронуты:** App.jsx, main.jsx, LoginPage, RegisterPage, ProfilePage, DashboardPage, CabinetSidebar
**Время потрачено:** ~5 мин на grep + замену
**Как предотвратить:** При создании файлов — если есть `return (` с HTML-подобным синтаксисом → `.jsx`

## Ошибка 2: Несовместимые API-сигнатуры (CRITICAL — runtime errors)

**Когда:** Шаг 7 (Cabinet pages) — DashboardPage, CourseDetailPage
**Симптом:** `getCourseProgress(course.id)` → undefined/NaN, `getLastLesson()` без аргументов
**Причина:** Параллельные агенты не знали точные сигнатуры lib/progress.js
**Реальные сигнатуры:**
- `getCourseProgress(modules)` → `{total, completed, percent}`
- `getLastLesson(courseId, modules)` → lesson object
- `getLessonProgress(lessonId)` → `{completed, watchedSeconds}`
- `markLessonCompleted(lessonId)` — без третьего аргумента
**Файлы переписаны:** DashboardPage.jsx, CourseDetailPage.jsx, LessonPage.jsx
**Как предотвратить:** Создавать lib/ ПЕРВЫМИ, включать JSDoc в промпт для агентов

## Ошибка 3: Хардкод цветов Tailwind (MEDIUM — design system breaks)

**Когда:** Шаг 7-9 — все страницы от агентов
**Симптом:** Формы используют `bg-indigo-500`, `text-gray-900` вместо `bg-accent`, `text-text`
**Причина:** Агенты не знали про кастомный @theme, использовали стандартные Tailwind-классы
**Масштаб:** 6 файлов, ~50 замен
**Как предотвратить:** В промпте агентам: "ЗАПРЕЩЕНЫ gray-*, indigo-*, red-*. ТОЛЬКО: text-text, bg-accent, border-border"

## Ошибка 4: sessionStorage для токенов (MEDIUM — UX breaks)

**Когда:** Шаг 4 — auth.js копировал паттерн из Maxim dashboard
**Симптом:** Юзер закрывает вкладку → открывает снова → не авторизован (token lost), но user data есть (localStorage)
**Причина:** Maxim dashboard использовал sessionStorage (real API, короткие сессии). Для мок-авторизации нужен localStorage
**Исправление:** `sessionStorage` → `localStorage` для TOKEN_KEY
**Как предотвратить:** Для скелета ВСЕГДА localStorage. Для реального бэкенда — httpOnly cookies

## Ошибка 5: price как строка "2 990 ₽" (MINOR — runtime error)

**Когда:** Шаг 9 — PaymentPage
**Симптом:** `plan.price.toLocaleString('ru-RU')` → ошибка (string не имеет числового toLocaleString)
**Причина:** pricing.js хранит price как "2 990 ₽" (уже отформатированная строка)
**Плюс:** В alert было `${plan.price} ₽` → двойной символ рубля
**Как предотвратить:** Либо числа + форматирование, либо строки + не форматировать. Выбрать одно

## Ошибка 6: dangerouslySetInnerHTML (SECURITY)

**Когда:** Шаг 8 — LessonPage от агента
**Симптом:** `<div dangerouslySetInnerHTML={{ __html: lesson.content }} />` для текстового контента
**Причина:** Агент решил что content может быть HTML
**Риск:** XSS если контент придёт от пользователя
**Исправление:** Заменить на `<p className="whitespace-pre-line">{lesson.content}</p>`
**Как предотвратить:** В промпте: "НЕ использовать dangerouslySetInnerHTML"

## Ошибка 7: VideoPlayer onTimeUpdate не подключён (MINOR — feature gap)

**Когда:** Шаг 8 — LessonPage
**Симптом:** `updateWatchedSeconds` из progress.js нигде не вызывается
**Причина:** Агент создал VideoPlayer с `onTimeUpdate` prop, но LessonPage не передавал callback
**Исправление:** `<VideoPlayer src={lesson.videoUrl} onTimeUpdate={(s) => updateWatchedSeconds(lessonId, s)} />`

## Ошибка 8: Порт занят при перезапуске dev-сервера

**Когда:** При повторном `npx vite --port 5180`
**Симптом:** "Port 5180 is in use, trying another one..."
**Причина:** Предыдущий процесс не убит
**Как предотвратить:** `kill $(lsof -t -i:5180) 2>/dev/null; npx vite --port 5180`

## Общие паттерны ошибок

1. **Агенты + параллелизм** → несовместимые API. Решение: core (lib/, hooks/) создавать ДО агентов
2. **Copy-paste из тёмной темы** → инвертированные цвета. Решение: адаптировать @theme ПЕРВЫМ
3. **Mock vs Real** → разные паттерны хранения. Решение: выбрать стратегию ДО создания auth

## Статистика

- Всего ошибок: 8
- Critical (build fails): 2
- Medium (UX/design breaks): 2
- Minor (feature gaps): 3
- Security: 1
- Время на фиксы: ~25 мин
- Файлов затронуто фиксами: 12 из 38
