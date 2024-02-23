CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    bio TEXT,
    email TEXT,
    published_books TEXT,
    library_books TEXT
)


CREATE TABLE books (
    book_id SERIAL PRIMARY KEY,
    user_id INT,
    title TEXT,
    picture_url TEXT,
    num_saved INT DEFAULT 0,
    genre TEXT,
    tags TEXT,
    num_chapters INT,
    summary TEXT
)

CREATE TABLE chapters (
    chapter_id INT,
    book_id INT,
    content TEXT
)