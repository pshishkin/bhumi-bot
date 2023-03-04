# bhumi-bot

# как запустить

docker compose up -d

положить в .env файл ваш токен тестового бота на котором будете тестить
TELEGRAM_TOKEN=...

sh ./scripts/launch.sh

# что нам нужно сделать

- имплементация через монгу для персистентного стораджа (можно использовать монгу из докер комоза)
- продумать модель данных для человека (его загруженные фото, оценки, ...)

поддержать следующие кейсы:
- загрузить фото, положить в объект пользователя
- нажать кнопку хочу оценить - получить последнее фото
  - получить там инлайн меню с вариантами (0-13 открыты, 1-13 заперфекчены), а затем оставить комментарий
  - после этого увидеть оценки других людей
- когда кто-то оценил мое фото, получить оценку
- когда кто-то оценил фото что я оценивал, тоже получить оценку

пример документа:
photo: {
    url
    timestamp
    author (telegram id)
    evaluations
}

а это говно оставляем в пикле:
user: {

}

на потом:
- сделать отдельную логику в отдельном классе для данных и буми самих (чтобы бот был только интерфейсом)
- добавить точность оценки к имени пользователя