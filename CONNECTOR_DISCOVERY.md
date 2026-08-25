# Splunk Connector — Connector Discovery

**Дата discovery:** 2026-08-24
**Статус:** Ярус 1 (критический костяк) реализуется полностью в этом релизе. Ярус 2
(Enterprise Security Notable Events, HEC, полный CRUD индексов) — частично, отмечено
явно ниже. Ярус 3 (полная административная поверхность: развёртывания, кластеризация,
lookups) — сознательно отложен, задокументирован как будущий объём. Влад заявил объём
прямым поручением («максимальный функционал») по всей категории SIEM/SOAR — здесь это
трактуется как максимум, реалистично достижимый за один присест разработки, с честно
названными границами (см. §5), а не как обещание покрыть весь Splunk REST API.

---

## 1. Целевой сервис и источники

Splunk (Cisco) — исторический стандарт SIEM в крупнейших SOC. Источники:
`docs.splunk.com/Documentation/Splunk/latest/RESTREF`,
`dev.splunk.com/enterprise/reference`, `docs.splunk.com/Documentation/Splunk/latest/RESTUM`.

У Splunk **две разные API-поверхности**, которые нельзя смешивать:

| Поверхность | Порт (типично) | Назначение | Аутентификация |
|---|---|---|---|
| **REST API управления** | 8089 | Поиск (search jobs), saved searches, индексы, пользователи, роли, конфигурация | Splunk auth token (Bearer) или Basic (username/password), создаётся в Settings > Tokens |
| **HEC — HTTP Event Collector** | 8088 | ТОЛЬКО приём событий (ingest) в индекс | Отдельный HEC-токен, `Authorization: Splunk <hec_token>` |

## 2. Карта возможностей (Ярус 1 — что делаем сейчас)

| Домен | Возможность | Комментарий |
|---|---|---|
| Connection | connect (base_url + auth token или user/pass), disconnect, list_connections | Self-hosted — `base_url` обязателен, SSRF-валидация по `APP_SAFETY_CHECKLIST.md` |
| Search | create search job (SPL), get job status, get job results (paginated), cancel job | Асинхронная job-based модель — не синхронный запрос-ответ |
| Saved searches | list/get/create/update/delete, dispatch (запустить вручную) | Основной способ работы с алертами Splunk |
| Indexes | list/get indexes (размер, событий, retention) | Read — управление ёмкостью |
| Users | list/get/create/update/delete Splunk users | Административный CRUD |
| Roles | list roles | Read-only справочник для форм создания пользователя |
| HEC | send_event (если пользователь сохранил отдельный HEC-токен) | Отдельный credential, egress-путь для интеграции с другими приложениями Imperal |
| Audit / value-add | `audit_search_head` — агрегированный отчёт: индексы близкие к квоте, saved searches без alert-действия, давно не выполнявшиеся поиски | Tier-3-стиль отчёт, но включён в Ярус 1 как основная ценность для SOC-инженера |

## 3. Что НЕ делаем в этом релизе (явные границы)

- **Enterprise Security (Notable Events)** — отдельное приложение поверх Splunk,
  доступность зависит от того, установлен ли ES у клиента. Не реализуется в этом
  релизе (`unverified`/условно доступный слой) — зафиксировано как будущий Ярус 2.
- **Data model / pivot API, lookups CRUD, deployment server/forwarder management,
  clustering config** — административная поверхность далеко за пределами
  incident/alert-ориентированного use-case, отложена как Ярус 3.
- **KV Store** — отдельная NoSQL-подсистема Splunk, не относится к SIEM/SOAR
  сценарию напрямую, не реализуется.

## 4. Архитектурное решение по аутентификации

BYOK, self-hosted: `base_url` обязателен (проверяется SSRF-валидатором
`normalize_base_url`, запрещены приватные/loopback адреса, если явно не разрешено).
Основной auth — Splunk auth token (Bearer), альтернатива — username/password (сессионный
токен получается автоматически при коннекте и используется прозрачно). Отдельный,
опциональный HEC-токен хранится как второй secret (per-connection), т.к. это другая
поверхность API с другой авторизацией — тот же паттерн, что integration key у PagerDuty.
