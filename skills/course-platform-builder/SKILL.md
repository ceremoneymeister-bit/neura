---
name: course-platform-builder
description: Создание обучающей платформы ('свой GetCourse') под ключ. Используй при запросах: обучающая платформа, курсы, LMS, онлайн-школа, 'сделай как GetCourse', платформа для уроков.
version: 2.0.0
author: Дмитрий Ростовцев
created: 2026-03-17
updated: 2026-04-01
category: development
tags: [lms, course-platform, react, education, getcourse-alternative]
risk: safe
usage_count: 1
last_used: 2026-04-01
maturity: seed
---

# course-platform-builder

## Purpose

Быстрое создание кастомизируемой обучающей платформы (аналог GetCourse/Teachable) на собственном хостинге. Шаблон клонируется из `projects/course-platform/`, кастомизируется под клиента за 1 сессию.

## When to Use

- Клиент просит "обучающую платформу" / "онлайн-школу" / "платформу для курсов"
- Нужна альтернатива GetCourse/Teachable на собственном хостинге
- Запрос "сделай как GetCourse, но своё"
- Любой проект с видеоуроками, модулями, прогрессом

## Стек (фиксированный)

- React 19.2 + Vite 7.3 + Tailwind CSS 4.1 + Framer Motion 12
- react-router-dom v7 (SPA)
- Lucide React (иконки)
- Деплой: FTP на REG.ru
- **Ноль дополнительных зависимостей**

## Proactive Excellence — ОБЯЗАТЕЛЬНО на каждом шаге

Каждая фаза = не минимум, а инвестиция. Мы НЕ делаем "рабочий прототип" — мы делаем продукт, который продаёт.

### Принципы проактивности

1. **Anticipate** — на каждом шаге спрашивай себя: "что ещё нужно, о чём не попросили?"
2. **Elevate** — не стоковые фразы, а конкретные под нишу. Не generic карточки, а wow-секции
3. **Verify** — скриншоты 390/430/1440 после КАЖДОГО визуального изменения. Читать через Read tool
4. **Audit** — после сборки автоматически: landing-audit (контраст, SEO, copy), не ждать пока попросят
5. **Iterate** — показал → получил фидбэк → улучшил. Не "готово, принимай"

### Чеклист проактивности (перед каждой отдачей результата)

| # | Проверка | Как |
|---|---------|-----|
| 1 | **Copy quality** — заголовки по 4U? Feature→Benefit→Outcome? | Прогнать headline-lab мысленно |
| 2 | **CTA stress** — CTA соответствует температуре трафика? | CTA Stress Matrix (НЕЧ20) |
| 3 | **Psychology triggers** — есть social proof, authority, risk reversal? | marketing-psychology PLFS |
| 4 | **Consistency** — FAQ↔Pricing↔Hero↔CTA используют одни термины? | Grep по хардкоду названий |
| 5 | **Visual** — контраст ≥4.5:1, hover states, mobile OK? | Playwright screenshots |
| 6 | **Data integrity** — нет placeholder данных, дублей, негативных отзывов? | Grep example.ru, дубли фраз |
| 7 | **Product ladder** — есть ≥3 уровня, lead magnet → tripwire → main? | product-ladder скилл |
| 8 | **Wow-момент** — есть хотя бы 1 интерактивный/неожиданный элемент? | UX принцип "Восторг" |
| 9 | **About author** — автор представлен, есть доверие? | Секция с фото + регалии |
| 10 | **Numbers** — конкретные цифры (уроки, часы, ученики, опыт)? | Минимум 3 числа на странице |

### Автоматические действия после Фазы 4

- `npm run build` OK → **автоматически** запустить мини-аудит: контраст text-muted, placeholder grep, FAQ consistency
- Обнаружил проблему → **исправить сразу**, не спрашивая
- Всё чисто → предложить 2-3 улучшения из чеклиста выше (не навязывать, а показать возможности)

---

## Workflow: создание платформы

### Фаза 1: Сбор требований (5 мин)

Спросить у клиента / Дмитрия:

1. **Название платформы** → `config.js → SITE.name`
2. **Акцентный цвет** → `config.js → SITE.accent` + `index.css → --color-accent`
3. **Контакты** → telegram, email
4. **Структура курса** → сколько модулей, уроков, тип контента
5. **Тарифы** → сколько планов, цены, что включено
6. **Домен** → для деплоя
7. **Тема** → светлая (по умолчанию) или тёмная

### Фаза 2: Клонирование шаблона (1 мин)

```bash
cp -r projects/course-platform/ projects/Producing/{Client}/platform/
cd projects/Producing/{Client}/platform/
npm install
```

### Фаза 3: Кастомизация (10-20 мин)

Файлы для изменения (в порядке приоритета):

| # | Файл | Что менять |
|---|------|-----------|
| 1 | `src/config.js` | name, subtitle, author, accent, telegram, email, domain |
| 2 | `src/index.css` | --color-accent, --color-accent-light в @theme |
| 3 | `src/data/courses.js` | Реальная структура курса клиента |
| 4 | `src/data/pricing.js` | Тарифы с реальными ценами |
| 5 | `src/data/testimonials.js` | Реальные отзывы (или удалить секцию) |
| 6 | `public/favicon.svg` | Логотип клиента |
| 7 | Landing-секции | Тексты Hero, Problems, ForWhom под нишу клиента |

### Фаза 4: Верификация (5 мин)

**Обязательный чеклист:**

- [ ] `npm run dev` — все страницы открываются
- [ ] `/` → лендинг с правильным брендингом
- [ ] `/login` → ввод любых данных → редирект в `/cabinet`
- [ ] Прямой переход `/cabinet` без авторизации → `/login`
- [ ] `/cabinet/courses` → клик по курсу → модули → урок → видеоплеер
- [ ] "Отметить как пройденный" → обновить страницу → прогресс сохранён
- [ ] Hamburger-меню на мобильном
- [ ] `npm run build` → без ошибок
- [ ] `.htaccess` в `dist/`

### Фаза 5: Деплой (2 мин)

```bash
npm run build
python3 scripts/ftp-deploy.py --source dist/ --target /public_html/
```

## Архитектура

### Маршруты

| Путь | Страница | Auth |
|------|----------|------|
| `/` | LandingPage (8 секций) | Нет |
| `/login` | LoginPage | Нет |
| `/register` | RegisterPage | Нет |
| `/payment` | PaymentPage | Нет |
| `/cabinet` | DashboardPage | Да |
| `/cabinet/courses` | CourseCatalogPage | Да |
| `/cabinet/courses/:id` | CourseDetailPage | Да |
| `/cabinet/courses/:id/lessons/:lid` | LessonPage (fullscreen) | Да |
| `/cabinet/profile` | ProfilePage | Да |
| `/admin` | AdminPage | Да |
| `*` | NotFoundPage | Нет |

### Ключевые паттерны

**ProtectedRoute** — проверяет `localStorage.getItem('auth_token')`:
```jsx
function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAuth()
  if (!isLoggedIn) return <Navigate to="/login" replace />
  return children
}
```

**CabinetLayout** — сайдбар + `<Outlet/>` для вложенных маршрутов. LessonPage ВНЕ layout (fullscreen).

**Прогресс** — `localStorage` ключ `course_progress`, JSON `{lessonId: {completed, watchedSeconds}}`.

**Единая точка кастомизации** — `config.js` → используется в навбарах, footer, hero.

### Структура файлов (38 файлов)

```
src/
├── main.jsx, App.jsx, index.css, config.js
├── data/ (courses, pricing, testimonials)
├── lib/ (auth, progress)
├── hooks/ (useAuth.jsx, useToast.jsx)
├── components/
│   ├── ui/ (Button, Card, Badge, Modal, FadeIn, VideoPlayer, Toast, ScrollToTop)
│   ├── layout/ (PublicNavbar, CabinetLayout, CabinetSidebar, Footer)
│   ├── landing/ (Hero, Problems, ForWhom, Program, Testimonials, Pricing, FAQ, CTA)
│   └── cabinet/ (CourseCard, ModuleAccordion, LessonCard, ProgressBar)
└── pages/ (10 страниц + NotFoundPage)
```

## Ошибки из опыта (ИЗБЕГАТЬ!)

### 1. JSX в .js файлах
**Проблема:** `useAuth.js` содержал JSX (`<AuthContext.Provider>`), но расширение `.js`. Vite/Rollup не может парсить JSX в .js файлах.
**Решение:** Файлы с JSX → расширение `.jsx`. Проверять ВСЕ файлы с JSX после создания.
**Правило:** Если файл содержит `<` HTML-подобный синтаксис → `.jsx`

### 2. Хардкод цветов вместо тем-токенов
**Проблема:** Агенты генерировали `bg-indigo-500`, `text-gray-900` вместо `bg-accent`, `text-text`. При смене акцентного цвета — формы не меняются.
**Решение:** В промптах для агентов ЯВНО указывать: "Используй ТОЛЬКО тем-токены: text-text, text-text-muted, bg-accent, bg-surface, border-border. НЕ используй gray-*, indigo-*, red-* и другие прямые цвета Tailwind."
**Правило:** Грепнуть после создания: `grep -r "gray-\|indigo-\|red-\|green-\|blue-\|amber-" src/pages/`

### 3. Рассогласование API между lib/ и компонентами
**Проблема:** `getCourseProgress(course.id)` в компоненте, но функция принимает `(modules)`. `getLessonProgress(courseId, lessonId)` но функция принимает только `(lessonId)`.
**Решение:** Создавать lib/ файлы ПЕРВЫМИ, затем передавать точные сигнатуры в промпты для агентов.
**Правило:** Всегда прочитать lib/ перед созданием компонентов. Включить JSDoc-сигнатуры в промпт.

### 4. sessionStorage vs localStorage для токенов
**Проблема:** Токен в sessionStorage пропадал при закрытии вкладки, юзер-данные в localStorage оставались → несогласованное состояние.
**Решение:** Использовать localStorage для обоих (token + user). Для реального бэкенда — httpOnly cookies.

### 5. Пропуск стоимости в виде строки
**Проблема:** `plan.price = "2 990 ₽"` (строка с символом ₽). Код делал `plan.price.toLocaleString()` — ломался.
**Решение:** Цены хранить как числа, форматировать при рендере. Или хранить как строку и НЕ форматировать.

### 6. dangerouslySetInnerHTML для контента уроков
**Проблема:** Агент использовал `dangerouslySetInnerHTML` для рендера текстового контента — XSS-уязвимость.
**Решение:** Обычный текстовый рендер: `<p>{lesson.content}</p>` или `whitespace-pre-line`.

### 7. Параллельные агенты и конфликты
**Проблема:** 3 агента создавали файлы параллельно → разные стили, несовместимые API-вызовы.
**Решение:** Создавать core (config, data, lib, hooks) в основном потоке ПЕРВЫМ. Агентам давать чёткие контракты (сигнатуры функций, доступные CSS-классы).

### 8. FAQ↔Pricing рассогласование (01.04.2026)
**Проблема:** FAQ называл тарифы "Базовый/Стандарт/Премиум", а Pricing — "Открытая тренировка/Полный доступ/С наставником". Пользователь видит разные названия.
**Решение:** Единый источник данных для названий тарифов. FAQ.jsx должен импортировать из `data/pricing.js`, а не хардкодить.
**Правило:** После создания Pricing — грепнуть по всем файлам на хардкод названий тарифов.

### 9. Негативные и дублирующие отзывы
**Проблема:** Отзыв "всё болит" без позитивного resolution пугает покупателя. Два отзыва содержали одну фразу — дублирование.
**Решение:** Каждый отзыв = проблема → решение → результат. Грепнуть на дубли фраз.

### 10. Config placeholder в проде
**Проблема:** `config.js` содержал `info@example.ru`, `t.me/channel` — рендерилось в footer.
**Решение:** Плейсхолдеры = build-time ошибка. Добавить проверку в pre-build.

## Чеклист для агентов (копировать в промпт)

```
ПРАВИЛА ДЛЯ ГЕНЕРАЦИИ КОМПОНЕНТОВ:
- Расширение: .jsx для файлов с JSX, .js для чистого JS
- Цвета: ТОЛЬКО тем-токены (text-text, bg-accent, border-border и т.д.)
- ЗАПРЕЩЕНЫ: gray-*, indigo-*, red-*, green-*, blue-*, amber-* из Tailwind
- CSS-классы: использовать .card, .btn, .btn-primary, .btn-ghost, .input, .nav-link
- Импорты: useAuth из '../hooks/useAuth.jsx' (НЕ .js)
- Auth API: login(email, password), register(name, email, password), logout()
- Progress API: getCourseProgress(modules) → {total, completed, percent}
  getLessonProgress(lessonId) → {completed, watchedSeconds}
  markLessonCompleted(lessonId)
  getLastLesson(courseId, modules) → lesson object
- Courses API: getCourse(courseId), getLesson(courseId, lessonId),
  getAllLessons(courseId), getAdjacentLessons(courseId, lessonId)
- Роутер: Link from 'react-router-dom', useParams, useNavigate
- Анимации: FadeIn from '../components/ui/FadeIn.jsx' (delay prop)
- Иконки: из 'lucide-react'
```

### 8. Лого дублируется в Hero и Navbar
**Проблема:** Логотип показывается и в навбаре и в hero-заголовке → визуальный мусор, особенно на мобиле.
**Решение:** Если hero содержит заголовок-лого (градиентный текст или изображение) → навбар скрывает лого до скролла: `className={scrolled ? 'opacity-100' : 'opacity-0 pointer-events-none'}`.
**Правило:** Лого в навбаре появляется ТОЛЬКО при скролле (когда hero уходит за пределы экрана).

### 9. Hero с фоновым изображением — мобильная адаптация
**Проблема:** background-image на мобиле показывает не ту часть изображения (горшок вместо человека). Или изображение уменьшается/обрезается.
**Решение:** РАЗДЕЛЬНЫЕ background для mobile и desktop:
```jsx
{/* Desktop */}
<div className="hidden sm:block absolute inset-0" style={{
  backgroundImage: 'url(...)', backgroundSize: 'auto 100%', backgroundPosition: 'right center'
}} />
{/* Mobile — другой position */}
<div className="sm:hidden absolute inset-0" style={{
  backgroundImage: 'url(...)', backgroundSize: 'auto 100%', backgroundPosition: '58% center'
}} />
```
**Правило:** НИКОГДА `background-size: cover/contain` для hero с человеком на мобиле. Всегда `auto 100%` + точный position. Проверять Playwright-скриншотами на 390px и 430px.

### 10. Заголовок обрезается — leading и overflow
**Проблема:** `leading-[0.85]` обрезает нижние элементы букв (descenders). CSS gradient text особенно чувствителен.
**Решение:** Минимум `leading-[1]` для gradient text. Без `overflow-hidden` на контейнере заголовка.

### 11. Не уменьшать фоновое изображение клиента
**Проблема:** Клиент создал изображение специально под hero (1920×1080). Агент уменьшил его до 70% высоты → "обрубленное".
**Решение:** Если клиент дал hero-изображение → `background-size: auto 100%` (полная высота ВСЕГДА). Сдвигать через position, НЕ уменьшать через size.

### 12. CSS gradient text вместо логотипа-картинки
**Проблема:** PNG-логотип не масштабируется, размывается при увеличении.
**Решение:** Воспроизвести логотип CSS-градиентом:
```jsx
<span style={{
  background: 'linear-gradient(180deg, #F0C060 0%, #E4AB70 40%, #E17912 100%)',
  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
}}>ЗАГОЛОВОК</span>
```
**Правило:** Если лого — это стилизованный текст → CSS gradient. Если лого — иконка/графика → PNG/SVG.

### 13. Marquee/бегущая строка для категорий
**Паттерн:** Дублировать массив 3 раза, `translateX(-33.333%)` за 20s:
```jsx
const marqueeItems = [...items, ...items, ...items]
// animation: marquee 20s linear infinite
// @keyframes marquee { 0% { translateX(0) } 100% { translateX(-33.333%) } }
```

### 14. ОБЯЗАТЕЛЬНО: Playwright-скриншоты перед отдачей
**Правило:** После КАЖДОГО визуального изменения — скриншоты 390px + 430px + 1440px. Прочитать через Read tool. Проверить что всё ОК. Только потом показывать Дмитрию.

## Будущие фазы (бэклог)

| Фаза | Что | Зависимости |
|------|-----|-------------|
| Backend | Express + SQLite, JWT, реальная авторизация | Сервер |
| Payments | ЮKassa/Robokassa webhook | Backend |
| Video | FFmpeg → HLS + nginx + hls.js | Сервер, ffmpeg |
| Notifications | Telegram бот (регистрация, оплата) | Bot token |
| Analytics | Реальные данные в AdminPage | Backend |
| Certificates | PDF-генерация по завершении курса | Backend |
| Search | Поиск по курсам/урокам | — |
| A11y | ARIA-labels, keyboard nav, contrast | — |

## References

Детальная документация в `references/`:
- `architecture.md` — подробная архитектура и data flow
- `errors-log.md` — полный лог ошибок с контекстом
- `customization-checklist.md` — чеклист кастомизации под клиента
