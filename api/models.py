from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mobile: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="Associate", nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, default=742, nullable=False)
    credit_label: Mapped[str] = mapped_column(String(30), default="Good", nullable=False)
    credit_last_updated: Mapped[str] = mapped_column(String(30), default="20 May 2025", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pan_number: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True)
    aadhaar_number: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(10), nullable=True)
    permanent_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    same_as_permanent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    selfie_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class OtpSession(Base):
    __tablename__ = "otp_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mobile: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(160), nullable=False)
    features: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
