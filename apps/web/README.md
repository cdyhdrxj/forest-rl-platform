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
Текущие endpoint-адреса собираются в `apps/web/src/constants/envs.js` из Vite-переменных:

- `VITE_API_PROTOCOL` - HTTP protocol, по умолчанию `http://`;
- `VITE_API_WS_PROTOCOL` - WebSocket protocol, по умолчанию `ws://`;
- `VITE_API_ADDRESS` - host backend, по умолчанию `127.0.0.1`;
- `VITE_API_PORT` - порт backend, по умолчанию `8000`.

В коде есть адреса для маршрутов:

- `ws://127.0.0.1:8000/continuous/trail`
- `ws://127.0.0.1:8000/continuous/coverage`
- `ws://127.0.0.1:8000/discrete/patrol`
- `ws://127.0.0.1:8000/discrete/reforestation`
- `ws://127.0.0.1:8000/threed/patrol`
- `ws://127.0.0.1:8000/threed/trail`

Какие маршруты видны в селекторе UI, задается в `TASKS_BY_ENV` того же файла. Сейчас 3D-среда показывает только задачу `Тропы`, поэтому `threed/patrol` доступен как backend/WebSocket route и запись в `WS_MAP`, но не выбирается вручную при создании нового эксперимента. Если добавляете или открываете пользователю новый route, обновляйте и карту endpoint'ов, и список задач для среды.

Описание протокола вынесено в `contracts/websocket_protocol.md`.

## Unity WebRTC stream

Компонент `src/components/WebRTCPlayer.jsx` отвечает только за видео/интерактивный stream Unity и не управляет lifecycle эксперимента. Он использует:

- `GET /webrtc/config` через `HTTP_MAP["WebrtcConfig"]`;
- `WS /ws` через `WS_MAP["WebrtcWs"]`.

В `envs.js` также есть `HTTP_MAP["WebrtcSignaling"]`, оставленный для старого HTTP polling signaling-клиента из `src/webrtc/module/signaling.js`. Текущий `WebRTCPlayer` использует `WebSocketSignaling`, поэтому backend endpoint `/webrtc/signaling` сейчас не нужен и не публикуется.

## Что делает интерфейс

- открывает WebSocket-соединение для выбранного режима;
- отправляет `generate`, `start`, `stop` и `reset`;
- отображает preview и live-состояние;
- показывает базовые метрики эпизодов и график награды;
- визуализирует сеточную карту, траекторию и положение объектов.

## Основные файлы

- `src/App.jsx` — текущее одностраничное приложение;
- `src/components/WebRTCPlayer.jsx` — Unity WebRTC video stream;
- `src/constants/envs.js` — route labels, endpoint maps и Vite-настройки backend;
- `src/constants/colors.js` — тема и базовые стили;
- `package.json` — команды запуска и сборки.

## Замечание

README описывает текущее поведение интерфейса, но не является источником правды по контракту.
За форматом команд и состояний нужно смотреть в `contracts/websocket_protocol.md`.
