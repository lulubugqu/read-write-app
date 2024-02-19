CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    pass VARCHAR(50),
    pfp_url TEXT,
    bio TEXT,
    email TEXT,
    birthday DATE,
    published_books TEXT,
    library_books TEXT
)

CREATE TABLE books (
    book_id SERIAL PRIMARY KEY,
    user_id INT,
    title TEXT,
    picture_url TEXT,
    summary TEXT,
    num_likes INT,
    num_saved INT,
    genres TEXT,
    tags TEXT,
    num_chapters INT,
    chapter_ids TEXT
)

CREATE TABLE chapters (
    chapter_id SERIAL PRIMARY KEY,
    book_id INT,
    content TEXT
)

