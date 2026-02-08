from sqlalchemy import Text, String, Integer
from sqlalchemy.orm import mapped_column, Mapped

from mess_auth.models import Base


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32))
    token: Mapped[str] = mapped_column(Text)
