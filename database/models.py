from typing import List, Dict, Optional
import datetime
import pprint

from sqlalchemy import Column, BIGINT, String, Boolean, DateTime, func, Integer, ForeignKey, event, Enum, JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, backref


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TgUser(Base):
    __tablename__ = "tg_user"

    created: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    id: Mapped[int] = Column(BIGINT, primary_key=True, nullable=False)
    username: Mapped[str] = Column(String(32))
    notify_with_sound: Mapped[bool] = Column(Boolean, nullable=False, server_default="1")
    is_deactivated: Mapped[bool] = Column(Boolean, nullable=False, server_default="0")

    def __repr__(self):
        return f"<TgUser: id={self.id}, username={self.username}>"


class MailSession(Base):
    __tablename__ = "mail_session"

    created: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    id: Mapped[int] = Column(Integer, primary_key=True, nullable=False)
    tg_user_id: Mapped[int] = Column(BIGINT, ForeignKey("tg_user.id", ondelete="CASCADE"), nullable=False)
    login: Mapped[str] = Column(String(20), nullable=False)
    password: Mapped[str] = Column(String(20), nullable=False)
    url_id: Mapped[str] = Column(String(30), nullable=False)
    email: Mapped[str] = Column(String(40), nullable=False)
    full_name: Mapped[str] = Column(String(50), nullable=False)
    cookie_session: Mapped[Optional[str]] = Column(String(20))
    update_session_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    last_mail_datetime: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    last_check: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())

    tg_user: Mapped[TgUser] = relationship("TgUser", uselist=False, lazy="selectin")

    def __repr__(self):
        return f"<MailSession: {pprint.pformat(vars(self))}>"
