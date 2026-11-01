"""Small demo catalog of real, published books with verified authors."""

from pydantic import BaseModel


class Book(BaseModel):
    id: str
    title: str
    author: str
    subject: str


CATALOG: tuple[Book, ...] = (
    Book(id="LIB-101", title="The Pragmatic Programmer, 20th Anniversary Edition", author="David Thomas and Andrew Hunt", subject="software engineering"),
    Book(id="LIB-102", title="Python Crash Course, 3rd Edition", author="Eric Matthes", subject="Python programming"),
    Book(id="LIB-103", title="Designing Data-Intensive Applications", author="Martin Kleppmann", subject="data systems"),
    Book(id="LIB-104", title="Artificial Intelligence: A Modern Approach", author="Stuart Russell and Peter Norvig", subject="artificial intelligence"),
    Book(id="LIB-105", title="Clean Code: A Handbook of Agile Software Craftsmanship", author="Robert C. Martin", subject="software engineering"),
    Book(id="LIB-106", title="Learning Python, 6th Edition", author="Mark Lutz", subject="Python programming"),
)
