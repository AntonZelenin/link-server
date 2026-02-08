from datetime import timezone, datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import mapped_column, Mapped

from mess_user import helpers
from mess_user.models import Base

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 150
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64


class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=helpers.uuid)
    username: Mapped[str] = mapped_column(String(USERNAME_MAX_LENGTH), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String(32), default=datetime.now(timezone.utc).isoformat())
