CREATE EXTENSION IF NOT EXISTS postgis;



-- Создание таблицы "Типы лекарств" (Таблица №3)
-- Здесь хранятся категории лекарственных средств.
CREATE TABLE medicine_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- SERIAL PRIMARY KEY создает автоинкрементный уникальный идентификатор.
-- UNIQUE в поле "name" гарантирует, что названия типов не будут повторяться.



-- Создание таблицы "Лекарства" (Таблица №1)
-- Основная таблица с информацией о лекарствах.
CREATE TABLE medicines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    type_id INTEGER NOT NULL,

    -- Связь с таблицей "Типы лекарств"
    CONSTRAINT fk_medicine_type
        FOREIGN KEY(type_id)
        REFERENCES medicine_types(id)
        ON DELETE RESTRICT -- Запрещает удаление типа, если на него ссылаются лекарства
);

-- FOREIGN KEY устанавливает связь между лекарством и его типом.


--— Создание таблицы "Аптеки" (Таблица №2) с использованием PostGIS
-- Содержит информацию об аптеках, включая их точное местоположение.
CREATE TABLE pharmacies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255), -- Текстовый адрес для отображения
    location GEOGRAPHY(Point, 4326) -- Географические координаты (долгота, широта)
);

-- Создание пространственного индекса для ускорения гео-запросов
-- (например, "найти все аптеки в радиусе 1 км")
CREATE INDEX idx_pharmacies_location ON pharmacies USING GIST (location);

--//Вместо простого хранения адреса в виде текста, мы добавляем поле "location"
-- типа GEOGRAPHY. Это позволяет выполнять быстрые и сложные пространственные запросы.
-- SRID 4326 — это стандартная система координат для GPS (WGS 84).


-- Создание таблицы "Ассортимент аптек" (Таблица №4)
-- Связующая таблица (многие-ко-многим) между аптеками и лекарствами.
CREATE TABLE pharmacy_assortment (
    pharmacy_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    cost NUMERIC(10, 2) NOT NULL CHECK (cost >= 0), -- Цена с точностью до 2 знаков после запятой
    quantity INTEGER NOT NULL CHECK (quantity >= 0), -- Количество товара на складе

    -- Составной первичный ключ: одна и та же пара (аптека, лекарство) не может повторяться
    PRIMARY KEY (pharmacy_id, medicine_id),

    -- Связь с таблицей "Аптеки"
    CONSTRAINT fk_pharmacy
        FOREIGN KEY(pharmacy_id)
        REFERENCES pharmacies(id)
        ON DELETE CASCADE, -- При удалении аптеки удаляются и все записи о её ассортименте

    -- Связь с таблицей "Лекарства"
    CONSTRAINT fk_medicine
        FOREIGN KEY(medicine_id)
        REFERENCES medicines(id)
        ON DELETE CASCADE -- При удалении лекарства удаляются все записи о нём в ассортиментах
);

-- ON DELETE CASCADE автоматически очищает связанные данные, поддерживая целостность базы данных.



---Примеры использования

---Вот как можно заполнить созданные таблицы данными:

-- ```sql
-- -- 1. Добавляем типы лекарств
-- INSERT INTO medicine_types (id, name) VALUES
-- (5, 'Обезболивающее'),
-- (6, 'Противовоспалительное');

-- -- 2. Добавляем лекарства
-- INSERT INTO medicines (name, description, image_url, type_id) VALUES
-- ('Аспирин', 'Противовоспалительное средство', '/images/aspirin.jpg', 6),
-- ('Парацетамол', 'Обезболивающее и жаропонижающее', '/images/paracetamol.jpg', 5);

-- -- 3. Добавляем аптеку с указанием координат
-- -- Для создания точки используется функция ST_MakePoint(долгота, широта)
-- INSERT INTO pharmacies (name, address, location) VALUES
-- ('Будь здоров!', 'г. Москва, ул Ленина, д. 10', ST_SetSRID(ST_MakePoint(37.6176, 55.7558), 4326));
-- -- Координаты (37.6176, 55.7558) соответствуют центру Москвы.

-- -- 4. Добавляем ассортимент в аптеку
-- INSERT INTO pharmacy_assortment (pharmacy_id, medicine_id, cost, quantity) VALUES
-- (1, 1, 150.50, 200), -- Аспирин в аптеке "Будь здоров!"
-- (1, 2, 80.00, 350);  -- Парацетамол в аптеке "Будь здоров!"