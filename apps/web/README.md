# Веб-интерфейс ForestRobotTwin

`apps/web` содержит React + Vite приложение для выбора режима,
генерации сценария, запуска обучения и просмотра текущего состояния среды.

## Запуск

### Локально

```bash
cd apps/web
npm install
npm run dev
```

### Через Docker

Первый запуск или пересборка:

```bash
docker compose up --build client
```

Повторный запуск:

```bash
docker compose up client
```

## Подключение к backend-сервису

Фронтенд работает поверх WebSocket API сервера `apps/api`.
Текущие endpoint-адреса зашиты в `apps/web/src/App.jsx`.

Сейчас интерфейс умеет подключаться к маршрутам:

- `ws://127.0.0.1:8000/continuous/trail`
- `ws://127.0.0.1:8000/discrete/patrol`
- `ws://127.0.0.1:8000/discrete/reforestation`
- `ws://127.0.0.1:8000/threed/patrol`
- `ws://127.0.0.1:8000/threed/trail`

Описание протокола вынесено в `contracts/websocket_protocol.md`.

## Что делает интерфейс

- открывает WebSocket-соединение для выбранного режима;
- отправляет `generate`, `start`, `stop` и `reset`;
- отображает preview и live-состояние;
- показывает базовые метрики эпизодов и график награды;
- визуализирует сеточную карту, траекторию и положение объектов.

## Основные файлы

- `src/App.jsx` — текущее одностраничное приложение;
- `src/constants/colors.js` — тема и базовые стили;
- `package.json` — команды запуска и сборки.

## Замечание

README описывает текущее поведение интерфейса, но не является источником правды по контракту.
За форматом команд и состояний нужно смотреть в `contracts/websocket_protocol.md`.
