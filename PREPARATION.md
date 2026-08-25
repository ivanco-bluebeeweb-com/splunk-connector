# Splunk Connector — Preparation

**Статус:** Фаза 1-2 (Discovery + архитектурные решения) завершены.
**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-24, v0.1
**Vikunja task:** #2494 (BBW Imperal Apps), `[App Development] Splunk Connector`.

**Почему сейчас:** первое приложение категории SIEM/SOAR в портфеле Imperal —
портфель уже покрывает ITSM (ServiceNow/Ivanti/BMC Helix/Jira SM/Freshservice) и
инцидент-менеджмент (PagerDuty), но не имеет коннектора к самому источнику
security-сигнала — логам и поисковой аналитике.

## 1. Паспорт приложения

**Название в Marketplace: «Splunk»**. app_id/папка: `splunk-connector`.

Коннектор к self-hosted/cloud Splunk через REST API управления (search jobs,
saved searches, indexes, users, roles) плюс опциональный HTTP Event Collector
для отправки событий. BYOK: пользователь подключает свой собственный Splunk-инстанс
через собственный auth token (или username/password). Imperal ничего не хостит.

## 2. Проблема в человеческих словах

Когда **SOC-инженер или security-аналитик** сталкивается с **необходимостью быстро
проверить, есть ли в логах признак инцидента, или запустить/проверить существующий
alert**, ему приходится **переключаться в отдельный Splunk Web UI, ждать загрузки
дашборда, вручную писать SPL-запрос**, из-за чего теряется время реагирования именно
в момент, когда оно критично.

## 3. Ключевые факты о Splunk API (см. `CONNECTOR_DISCOVERY.md`)

Две API-поверхности (REST управления на 8089, HEC на 8088), асинхронная job-based
модель поиска (dispatch → poll → results), self-hosted → SSRF-валидация обязательна.

## 4. Архитектурное решение — BYOK, self-hosted, два типа credentials

1. **Auth token / username+password** (обязательный, при `connect_splunk`) —
   покрывает весь REST API управления.
2. **HEC token** (опциональный, per-connection) — отдельный credential для
   `send_event`, не вводится при коннекте аккаунта, сохраняется отдельно через
   `save_hec_token`, аналогично PagerDuty's integration keys.

## 5. Объём релиза — Ярус 1 (см. `CONNECTOR_DISCOVERY.md` §2-3)

Connection (connect/disconnect/list/save_hec_token/list_hec_tokens/delete_hec_token),
Search (dispatch/get status/get results/cancel/list jobs), Saved searches
(list/get/create/update/delete/dispatch), Indexes (list/get), Users (list/get/create/
update/delete), Roles (list), HEC (send_event), value-add audit (audit_search_head).

## 6. Что НЕ делаем

Enterprise Security Notable Events, data model/pivot, lookups CRUD, deployment
server/forwarder/clustering config, KV Store — см. `CONNECTOR_DISCOVERY.md` §3.

## 7. UI (Фаза 3, см. `UI_INTERFACE_STANDARD.md`)

См. `IDEAL_ONBOARDING.md` + `UI_COMPONENT_PLAN.md` (написаны ДО `panels.py`, по
`ONBOARDING_FIRST_LAUNCH_STANDARD.md`). Единая кнопка "App settings" в сайдбаре
(последний элемент), форма подключения растянута на всю ширину сайдбара, поля с
label+placeholder, без карточек, инструкция только в модалке (не дублируется).
