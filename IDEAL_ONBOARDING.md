# Splunk Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: SOC-инженер
или security-аналитик, администрирующий собственный self-hosted/cloud Splunk.

## 1. Credential type
Base URL (обязателен, self-hosted) + auth token (Bearer) ИЛИ username/password
(сессионный токен получается автоматически). Опциональный HEC token отдельно.

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой "Settings > Tokens > New Token" +
   объяснением, что base_url — это адрес management-порта (обычно `:8089`), а не
   Splunk Web (`:8000`) — частая ошибка новых пользователей.
2. **Форма** — base_url (Input, placeholder "https://splunk.mycompany.com:8089"),
   auth_token (Password) ИЛИ username+password (переключатель режима), с пояснением
   "используйте auth token, если он у вас есть — это проще и безопаснее пароля".
3. **После успеха** — сразу `audit_search_head` — сколько saved searches без alert
   action, какие индексы близки к retention/размерной квоте — actionable для
   security-аналитика с первой секунды.
4. **Search-first UX** — центр экрана сразу предлагает поле для SPL-запроса
   (не список настроек), т.к. основная ценность — быстрый поиск по логам.
5. **Ошибка "wrong port"** — если `base_url` указывает на порт 8000 (Splunk Web, не
   REST API) — конкретное сообщение "Похоже, это порт Splunk Web, а не REST API
   (обычно :8089)", а не общее "не удалось подключиться".

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
