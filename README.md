# Parma DAMA bot

## Развёртывание

### Пример .env

```bash
    DB_HOST=<server_ip>
    DB_PORT=5000
    DB_NAME=parma
    DB_USER=VkRjkM
    DB_PASSWORD=NQjWQn
    CONTAINER_NAME=dama
    TELEGRAM_TOKEN=<TG_TOKEN>
    LOG_LEVEL=INFO
    DROP_DB_ON_STARTUP=False # Очищает pg при старте если True
    REDIS_USER=ahrsg32mFdsG
    REDIS_USER_PASSWORD=dgoGHfghh32gdfG
    REDIS_HOST=<server_ip>
    REDIS_PORT=6380
    REDIS_EXPIRE_TIME=604800
    MINIO_ROOT_USER=hts234gDGh
    MINIO_ROOT_PASSWORD=pwdasd432dGfdfgfghsdf
    MINIO_HOST=<server_ip>
    MINIO_PORT=9000
    RETRIES_AI_ASK=3 # Количество повторных попыток обратиться к II API
    COMPOSE_BAKE=true
    SECURE=True # Если используется https для minio
    ADMIN_PASSWORD=xaZ139*BZhh # Сделать посложнее
```

```bash
   docker-compose up -d
```

## Локальная разработка

1) Скачиваем poetry с сайта <https://python-poetry.org/docs/>

2) Создаём env

```bash
    DB_HOST=localhost
    DB_PORT=5000
    DB_NAME=parma
    DB_USER=VkRjkM
    DB_PASSWORD=NQjWQn
    CONTAINER_NAME=dama
    TELEGRAM_TOKEN=<TG_TOKEN>
    LOG_LEVEL=INFO
    DROP_DB_ON_STARTUP=True
    REDIS_USER=ahrsg32mFdsG
    REDIS_USER_PASSWORD=dgoGHfghh32gdfG
    REDIS_HOST=localhost
    REDIS_PORT=6380
    REDIS_EXPIRE_TIME=604800
    MINIO_ROOT_USER=hts234gDGh
    MINIO_ROOT_PASSWORD=pwdasd432dGfdfgfghsdf
    MINIO_HOST=localhost
    MINIO_PORT=9000
    RETRIES_AI_ASK=3 
    COMPOSE_BAKE=true
    SECURE=False
    ADMIN_PASSWORD=PASSWORD
```

3) Запускаем контейнеры

```bash
    docker-compose up -d -f docker-compose.development.yml
```

4) Устанавливаем зависимости

```bash
    poetry install
```

5) Запуск

```bash
    poetry run python main.py
```
