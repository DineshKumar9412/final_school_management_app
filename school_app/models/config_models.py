# models/config_models.py
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class AppConfig(Base):
    """
    Generic key/value configuration store.

    key_type controls how `value` (stored as TEXT) is interpreted:
      list   → JSON array  e.g.  '["8.00", "9.00", "10.00"]'
      dict   → JSON object e.g.  '{"theme": "dark"}'
      set    → JSON array  (unique items, returned as list)
      string → raw text
      bool   → "true" / "false"
    """
    __tablename__ = "app_config"

    id:         Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_name:   Mapped[str]           = mapped_column(String(100), unique=True, nullable=False)
    key_type:   Mapped[str]           = mapped_column(
                                          Enum("list", "dict", "string", "set", "bool"),
                                          nullable=False,
                                      )
    value:      Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]      = mapped_column(
                                          DateTime,
                                          server_default=func.current_timestamp(),
                                          nullable=False,
                                      )
    updated_at: Mapped[datetime]      = mapped_column(
                                          DateTime,
                                          server_default=func.current_timestamp(),
                                          onupdate=func.current_timestamp(),
                                          nullable=False,
                                      )
