# Splunk Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`.
Основано на `IDEAL_ONBOARDING.md` этого приложения.

## 0. Разница с идеалом
Идеал предлагает live-tail лога и autocomplete SPL-полей по индексу — сегодняшний
`ui.TextArea`/`ui.DataTable` не поддерживают ни то, ни другое: DataTable статичен на
момент рендера (нет live push), autocomplete на произвольном инпуте не входит в
словарь примитивов. Компромисс: `ui.Button`("Обновить") рядом с результатами поиска
вместо live-tail; обычный `ui.TextArea` с placeholder-примерами SPL вместо autocomplete.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(align="start") + `ui.Text`(instance label) + `ui.Divider` + navigation `ui.ListItem`(Search/Saved Searches/Indexes/Users) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Connect form (sidebar, до подключения) | `ui.Form`(full_width) + `ui.Input`(label="Base URL", placeholder="https://splunk.mycompany.com:8089") + `ui.Select`(label="Способ входа", options=[token, user/pass]) + `ui.Password`(label="Auth token" или "Пароль") + `ui.Button`("Подключить") | Один растянутый на всю ширину сайдбара контейнер формы, поля с лейблами, плейсхолдер контекстный. |
| Search (center, `center_overlay=True`) | `ui.TextArea`(param_name="spl_query", placeholder="index=security sourcetype=auth | stats count by user") + `ui.Button`("Выполнить поиск") + `ui.DataTable`(результаты, колонки динамически из полей события) + `ui.Progress`(пока job не done) | `TextArea` — свободный ввод SPL, `DataTable` — табличные результаты, `Progress` — отражает асинхронность job. |
| Saved Searches | `ui.DataTable`(name, cron_schedule, has_alert_action Badge, last_run) + Row actions (Button "Запустить сейчас") | Список алертов/сохранённых поисков с быстрым запуском. |
| Search Detail (после dispatch) | `ui.Stats`(scan_count/event_count/duration) + `ui.DataTable`(результаты) | Итоговые метрики поиска сверху таблицы. |
| Indexes | `ui.DataTable`(name, current_size, max_size, Badge при близости к квоте) | Обзор состояния хранилища. |
| Health/Audit | `ui.Stats`(saved searches без alert action, индексы у квоты) | `audit_search_head` value-add с первого экрана. |
| App settings (center, отдельный screen) | `ui.Stack` + список подключений с Disconnect + секция HEC token (Password + Button "Сохранить") | Disconnect и HEC-секрет — только здесь, не в сайдбаре. |

## 2. User flow
1. Не подключено → sidebar показывает форму (Input+Select+Password+Button), центр —
   `ui.Empty`("Подключите Splunk, чтобы начать поиск", cta="Подключить").
2. `connect_splunk` успех → `refresh_panels` обновляет сайдбар (список инстансов) и
   центр (сразу `audit_search_head` в виде Stats).
3. Sidebar навигация → клик на "Search" → центр меняется на Search-экран.
4. Ввод SPL → "Выполнить поиск" → Progress, пока job не завершится → DataTable.
5. "App settings" (низ сайдбара) → центр показывает управление подключением/HEC.

## 3. Что переиспользуем из PagerDuty Connector
Тот же паттерн: `panels.py` (sidebar + основной центр, `center_overlay=True`),
`panels_settings.py` (App settings screen), один `_settings_button()` внизу сайдбара,
`_load_connections()` в `handlers_connection.py`, JSON-array-в-secret хранение
множественных подключений/HEC-токенов.
