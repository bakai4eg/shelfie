"""ORM-модели, сгруппированные по подсистемам.

Правило: модель живёт в файле своей подсистемы, все модели импортируются
здесь, чтобы Alembic видел полную метадату (`Base.metadata`).

Файлы:
    user.py        — users, sessions                    (T1.1, готово)

Планируемые файлы:
    catalog.py     — catalog_items                      (T2.1)
    library.py     — user_items                         (T2.4)
    list.py        — lists, list_items                  (T3.2)
    social.py      — reviews, comments, likes, follows,
                     activity_events                    (T4.3, T4.4, T5.3, T5.4)
    moderation.py  — reports, audit_log                 (T4.1, T4.2)
"""

from app.models.user import Session, User

__all__ = ["Session", "User"]

