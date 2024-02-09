CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    pass VARCHAR(50),
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
    summary TEXT,
    num_likes INT,
    num_saved INT,
    genres TEXT,
    tags TEXT,
    num_chapters INT,
    content TEXT
)

