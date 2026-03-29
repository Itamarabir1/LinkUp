from datetime import datetime, timezone
from typing import Optional, Any, Dict, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from geoalchemy2.functions import ST_GeomFromText

# ייבוא המודל והסכימות
from app.domain.users.model import User
from app.domain.users.schema import UserCreate, UserUpdate


class CRUDUser:
    """
    מחלקה המרכזת את כל הפעולות מול מסד הנתונים עבור מודל User.
    מימוש אסינכרוני מלא (SQLAlchemy 2.0) התואם לשיטת DDD.
    """

    async def get_by_id(self, db: AsyncSession, id: Union[UUID, str]) -> Optional[User]:
        """שליפת משתמש לפי ID (UUID)"""
        uid = UUID(str(id)) if isinstance(id, str) else id
        result = await db.execute(select(User).filter(User.user_id == uid))
        return result.scalars().first()

    async def get(self, db: AsyncSession, *, id: Union[UUID, str]) -> Optional[User]:
        """שליפת משתמש לפי ID – חתימה get(db, id=...) לשימוש ב־NotificationHandler. id יכול להיות UUID או str."""
        return await self.get_by_id(db, id)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """שליפת משתמש לפי אימייל (case-insensitive)"""
        result = await db.execute(
            select(User).filter(func.lower(User.email) == func.lower(email))
        )
        return result.scalars().first()

    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[User]:
        """שליפת משתמש לפי מספר טלפון"""
        result = await db.execute(select(User).filter(User.phone_number == phone))
        return result.scalars().first()

    async def create(
        self, db: AsyncSession, *, obj_in: UserCreate, hashed_password: str
    ) -> User:
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
        # שים לב: הורדנו את ה-commit!
        # אנחנו עושים flush כדי לקבל את ה-ID (user_id) שנוצר מה-DB
        # מבלי לסיים את הטרנזקציה.
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]],
    ) -> User:
        """
        עדכון דינמי וחסין.
        משתמש ב-model_dump כדי לעדכן רק שדות שנשלחו בבקשה.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # exclude_unset=True מבטיח שלא נדרוס שדות שלא נשלחו ב-JSON
            update_data = obj_in.model_dump(exclude_unset=True)

        # שדות שאסור לעדכן דרך פונקציה כללית
        protected_fields = ["user_id", "created_at", "hashed_password"]

        for field, value in update_data.items():
            if hasattr(db_obj, field) and field not in protected_fields:
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_location(
        self, db: AsyncSession, *, user_id: Union[UUID, str], lat: float, lon: float
    ) -> bool:
        """עדכון מיקום גיאוגרפי (GIS)"""
        point_wkt = f"POINT({lon} {lat})"  # סטנדרט PostGIS: Longitude קודם
        user = await self.get_by_id(db, user_id)
        if user:
            user.last_location = ST_GeomFromText(point_wkt, srid=4326)
            await db.commit()
            return True
        return False

    async def update_fcm_token(
        self, db: AsyncSession, *, user: User, token: str
    ) -> User:
        """עדכון ה-FCM Token של המשתמש"""
        user.fcm_token = token
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_refresh_token(
        self, db: AsyncSession, *, user: User, refresh_token: Optional[str]
    ) -> User:
        """עדכון או ניקוי Refresh Token (לשימוש ב-login וב-logout)."""
        user.refresh_token = refresh_token
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_password(
        self, db: AsyncSession, *, user: User, hashed_password: str
    ) -> User:
        """עדכון סיסמה (מוצפנת בלבד)"""
        user.hashed_password = hashed_password
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def mark_as_verified(self, db: AsyncSession, user: User) -> User:
        """סימון משתמש כמאומת"""
        user.is_verified = True
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_last_active(self, db: AsyncSession, *, user_id: Union[UUID, str]) -> bool:
        """עדכון זמן פעילות אחרונה (צ'אט וכו') — לא משנה last_login."""
        user = await self.get_by_id(db, user_id)
        if not user:
            return False
        user.last_active_at = datetime.now(timezone.utc)
        db.add(user)
        await db.commit()
        return True


# יצירת מופע יחיד (Singleton) שישמש את ה-Services
crud_user = CRUDUser()
