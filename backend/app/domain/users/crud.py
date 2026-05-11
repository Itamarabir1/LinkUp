from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from geoalchemy2.functions import ST_GeomFromText
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Model and schemas
from app.domain.users.model import User
from app.domain.users.schema import UserCreate, UserUpdate


class CRUDUser:
    """
    Async CRUD for User (SQLAlchemy 2.0), DDD-style service boundary.

    Transaction ownership: all write methods use db.flush() only.
    Callers are responsible for db.commit().
    expire_on_commit=False means no db.refresh() needed after commit.
    """

    async def get_by_id(self, db: AsyncSession, id: UUID | str) -> User | None:
        """Get user by ID (UUID)."""
        uid = UUID(str(id)) if isinstance(id, str) else id
        result = await db.execute(select(User).filter(User.user_id == uid))
        return result.scalars().first()

    async def get(self, db: AsyncSession, *, id: UUID | str) -> User | None:
        """get(db, id=...) alias for NotificationHandler; id may be UUID or str."""
        return await self.get_by_id(db, id)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Get user by email (case-insensitive)."""
        result = await db.execute(select(User).filter(func.lower(User.email) == func.lower(email)))
        return result.scalars().first()

    async def get_by_phone(self, db: AsyncSession, phone: str) -> User | None:
        """Get user by phone number."""
        result = await db.execute(select(User).filter(User.phone_number == phone))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate, hashed_password: str) -> User:
        db_obj = User(
            full_name=obj_in.full_name,
            phone_number=obj_in.phone_number,
            email=obj_in.email,
            fcm_token=obj_in.fcm_token,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
        )
        db.add(db_obj)
        # No commit here — caller owns the transaction.
        # flush() assigns DB-generated user_id without committing.
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: UserUpdate | dict[str, Any],
    ) -> User:
        """
        Partial update: only fields present in the request (model_dump exclude_unset).
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # exclude_unset=True avoids overwriting omitted JSON fields
            update_data = obj_in.model_dump(exclude_unset=True)

        # Fields not allowed through this generic update
        protected_fields = ["user_id", "created_at", "hashed_password"]

        for field, value in update_data.items():
            if hasattr(db_obj, field) and field not in protected_fields:
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_location(self, db: AsyncSession, *, user_id: UUID | str, lat: float, lon: float) -> bool:
        """Update user's last_location (PostGIS)."""
        point_wkt = f"POINT({lon} {lat})"  # PostGIS WKT: longitude first
        user = await self.get_by_id(db, user_id)
        if user:
            user.last_location = ST_GeomFromText(point_wkt, srid=4326)
            await db.flush()
            return True
        return False

    async def update_fcm_token(self, db: AsyncSession, *, user: User, token: str | None) -> User:
        """Set or clear FCM token."""
        user.fcm_token = token
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def update_refresh_token(self, db: AsyncSession, *, user: User, refresh_token: str | None) -> User:
        """Set or clear refresh token (login/logout)."""
        user.refresh_token = refresh_token
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def update_password(self, db: AsyncSession, *, user: User, hashed_password: str) -> User:
        """Update hashed password only."""
        user.hashed_password = hashed_password
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def mark_as_premium(self, db: AsyncSession, *, user: User) -> User:
        """Mark user as premium after successful payment."""
        user.is_premium = True
        user.premium_since = datetime.now(UTC)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def update_stripe_customer_id(self, db: AsyncSession, *, user: User, stripe_customer_id: str) -> User:
        """Save Stripe customer ID on first payment."""
        user.stripe_customer_id = stripe_customer_id
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def update_last_active(self, db: AsyncSession, *, user_id: UUID | str) -> bool:
        """Bump last_active_at (chat, etc.); does not touch last_login."""
        user = await self.get_by_id(db, user_id)
        if not user:
            return False
        user.last_active_at = datetime.now(UTC)
        db.add(user)
        await db.flush()
        return True


# Singleton for services
crud_user = CRUDUser()
