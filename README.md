# Запуск и начальная настройка проекта

### Клонирование репозитория и сборка

```bash
git clone https://github.com/Lambdaderta/predprof_olymp_education

# Скачайте модели через скрипт download.ipynb (просто запустить все) в predprof_olymp_education/ml/llm 
cd predprof_olymp_education/
docker-compose up -d --bulid
```

Переходите на http://localhost:3000, регестрируетесь
### После, для создания юзера с правами админа в консоли:

- docker-compose exec pg psql -U user -d aio_edu -c "UPDATE users SET role = 'admin' WHERE email = 'example@email.com';"

- По адресу http://localhost:8000/admin (можно перейти из графического интерфейса) находится админ панель, из которой можно управлять юзерами, задачами, просматривать некоторые статистики и тд. Загружать и выгружать задачи.