from sqlalchemy import String
from sqlalchemy.orm import mapped_column, Mapped

from mess_auth.models import Base


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(72), nullable=False)
