# Pricing History — Splunk Connector

Обязательный журнал: каждое выставление или изменение цен на функции этого
приложения фиксируется здесь — что изменилось, почему, и на основании
чего. Не переписывать прошлые записи — только дописывать новые сверху.

---

## 2026-08-25 — первичное выставление цен

**Модель:** `per_action`, `revenue_split_dev=95` (partner-тир), 20 функций,
канонический метод: `update_pricing` с `pricing_config` как настоящим
вложенным JSON-объектом (`{"tool_prices": {...}, "free_tools": [...],
"monthly_price": 0}`), НЕ как экранированная строка — согласно
`PRICING_POLICY.md` §3.

**Разбивка** (см. `tool-prices.json`, перенесено без изменений):
- 0 — `connect_splunk`, `list_connections`, `disconnect_splunk`,
  `save_hec_token`, `list_hec_tokens`, `delete_hec_token` (подключение и
  управление секретами всегда бесплатны — стандарт по всему портфелю).
- 4 — `get_search_status`, `cancel_search` (лёгкий статус-опрос).
- 8 — `get_search_results`, `list_saved_searches`, `list_indexes`,
  `list_users`, `list_roles` (стандартное чтение/листинг).
- 12 — `dispatch_search`, `dispatch_saved_search`, `send_event`
  (реальный запуск поиска/отправка события в чужую инфраструктуру).
- 16 — `create_saved_search`, `update_saved_search`, `delete_saved_search`
  (CRUD над сохранённым поиском/алертом).
- 40 — `audit_search_head` (тяжёлый агрегирующий отчёт по всему search
  head — несколько внутренних запросов).

**Подтверждение применения:** `developer__update_pricing` вернул успешный
`manifest_json` с `pricing_model=per_action`, ошибок не было. Cледующий
шаг перед объявлением цены реально применённой — визуальная проверка в
панели (см. `Asana Connector/PRICING_HISTORY.md` про "нет ошибки ≠ цена
применилась"); Влад может проверить в Marketplace-карточке приложения.
