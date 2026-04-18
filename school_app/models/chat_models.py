# models/chat_models.py
from sqlalchemy import BigInteger, Boolean, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime
from typing import Optional


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id:          Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sender_id:   Mapped[int]           = mapped_column(BigInteger, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    receiver_id: Mapped[int]           = mapped_column(BigInteger, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    message:     Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    is_read:     Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    created_at:  Mapped[datetime]      = mapped_column(server_default=func.current_timestamp(), nullable=False)

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} from={self.sender_id} to={self.receiver_id}>"
