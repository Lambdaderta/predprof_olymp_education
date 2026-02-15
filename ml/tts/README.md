# TTS Service

Сервис синтеза речи на основе Edge TTS. Предоставляет веб-интерфейс и REST API для преобразования текста в аудио в формате MP3.

## Запуск сервиса

### Требования
- Docker 20.10+
- Docker Compose 2.0+

### Инструкция
1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/tts-service.git
cd tts-service
```

2. Соберите и запустите контейнер:
```bash
docker compose up -d --build
```

3. Проверьте статус сервиса:
```bash
docker compose ps
```

4. Сервис будет доступен по адресу:
```
http://tts-service:8000
```

### Остановка сервиса
```bash
docker compose down
```

## API Reference

### POST /tts/text
Преобразует текст в аудио.

**Request:**
```json
{
  "text": "Текст для озвучки",
  "voice": "ru-RU-SvetlanaNeural",
  "rate": "+0%"
}
```

**Parameters:**
- `text` (string, required): Текст для синтеза речи
- `voice` (string, optional): Код голоса. По умолчанию: `ru-RU-SvetlanaNeural`
- `rate` (string, optional): Скорость речи в формате `+10%`, `-5%`. По умолчанию: `+0%`

**Response:**
- Content-Type: `audio/mpeg`
- Body: MP3 файл с синтезированной речью

### POST /tts/file
Преобразует текстовый файл в аудио.

**Request:**
```
Content-Type: multipart/form-data
```

**Form Parameters:**
- `file` (file, required): Текстовый файл (.txt, .md)
- `voice` (string, optional): Код голоса. По умолчанию: `ru-RU-SvetlanaNeural`
- `rate` (string, optional): Скорость речи. По умолчанию: `+0%`

**Response:**
- Content-Type: `audio/mpeg`
- Body: MP3 файл с синтезированной речью

### GET /voices
Возвращает список доступных голосов.

**Response:**
```json
{
  "voices": [
    "ru-RU-DmitryNeural",
    "ru-RU-SvetlanaNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "de-DE-KatjaNeural",
    "de-DE-ConradNeural"
  ]
}
```

### GET /health
Проверка состояния сервиса.

**Response:**
```json
{
  "status": "healthy",
  "service": "tts-api"
}
```

## Доступные голоса

- **Русские голоса:**
  - `ru-RU-DmitryNeural` (мужской)
  - `ru-RU-SvetlanaNeural` (женский)

- **Английские голоса:**
  - `en-US-JennyNeural` (женский)
  - `en-US-GuyNeural` (мужской)

- **Немецкие голоса:**
  - `de-DE-KatjaNeural` (женский)
  - `de-DE-ConradNeural` (мужской)

## Важные замечания

1. Сервис требует интернет-соединения для доступа к Microsoft Speech API.
2. Максимальная длина текста для синтеза - 3000 символов.
3. Для работы с русскими символами файлы должны быть в кодировке UTF-8.
4. В случае ошибок синтеза возвращается HTTP статус 500 с описанием ошибки в формате JSON.
5. Русские голоса английский озвучивают так себе, может когда то добавлю автоматическое разбиение на языки и склейку в общий много язычный файл, но пока мне это не надо.

# F5 TTS

Локальный TTS, прилагаю IPYNB файл, в котором прописан локальный запуск. 

В будущем напишу простой сервис для локального запуска F5 TTS, хотя это не сложно сделать нейронкой.