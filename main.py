from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Dict, Iterable, Literal, Optional, Sequence, Tuple
import logging
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, constr, Field
from sqlalchemy import create_engine, Column, Integer, String, Date, Enum, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt
from typing import Annotated
import enum
import datetime
from sqlalchemy import Float, ForeignKey, Interval
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Numeric
from uuid import UUID as PyUUID
from sqlalchemy.dialects.postgresql import UUID as SAUUID
from typing import List
# Настройка логгера — вывод в консоль с уровнем INFO
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import os
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

class UTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Устанавливаем правильную кодировку для JSON
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response

# Добавьте после создания app, но до других middleware
app = FastAPI()

# Добавьте UTF8 middleware ПЕРВЫМ
app.add_middleware(UTF8Middleware)

# Затем добавьте CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------- ENUM Definitions ----------
class GenderEnum(str, enum.Enum):
    male = "Мужской"
    female = "Женский"
    other = "Иное"

class CarBrandEnum(str, enum.Enum):
    Toyota = "Toyota"
    BMW = "BMW"
    Mercedes = "Mercedes"
    Audi = "Audi"
    Kia = "Kia"

class CarColorEnum(str, enum.Enum):
    Black = "Черный"
    White = "Белый"
    Red = "Красный"
    Blue = "Синий"
    Green = "Зеленый"

class DrivingStyleEnum(str, enum.Enum):
    aggressive = "Агрессивный"
    dynamic = "Динамичный"
    careful = "Плавный"
    undefined = "Неопределен"

class EventTypeEnum(str, enum.Enum):
    braking = "braking"
    acceleration = "acceleration"
    turn = "turn"

class SeverityEnum(str, enum.Enum):
    dangerous = "dangerous"
    medium = "medium"
    soft = "soft"


# ---------- DB Setup ----------
#DATABASE_URL = "postgresql://postgres:SouKir666%21@localhost:5432/DTP"
DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------- User Model ----------
class User(Base):
    __tablename__ = "users"

    user_id = Column(SAUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    birth_date = Column(Date, nullable=False)
    driving_experience = Column(Integer, nullable=False)
    car_brand = Column(Enum(CarBrandEnum), nullable=False)
    car_color = Column(Enum(CarColorEnum), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ---------- Trip Model ----------
class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    start_time = Column(TIMESTAMP)
    end_time = Column(TIMESTAMP)

    total_distance = Column(Numeric(10,2))

    user = relationship("User", backref="trips")


# ---------- Event Model ----------
class Event(Base):
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.trip_id"), nullable=False)

    event_time = Column(TIMESTAMP)
    event_type = Column(Enum(EventTypeEnum))
    severity = Column(Enum(SeverityEnum))
    points = Column(Integer)
    latitude = Column(Numeric(9,6))
    longitude = Column(Numeric(9,6))

    trip = relationship("Trip", backref="events")


# ---------- Dangerous Zone per Trip ----------
class Zone(Base):
    __tablename__ = "zones"

    dangerous_zone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.trip_id"), nullable=False)

    start_zone = Column(TIMESTAMP)
    end_zone = Column(TIMESTAMP)

    trip = relationship("Trip", backref="zones")


# ---------- Overall Stats ----------
class OverallStat(Base):
    __tablename__ = "overall_stats"

    stat_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    driving_style = Column(Enum(DrivingStyleEnum))
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="overall_stats")


# ---------- Danger Zones (geometry) ----------
class DangerZone(Base):
    __tablename__ = "danger_zones"

    zone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    polygon = Column(Geometry("POLYGON", srid=4326))


# ---------- CORS Middleware ----------
origins = [
    "http://localhost:1234",
    "http://127.0.0.1:1234",
    "http://10.0.2.2:8000",
    "*"
]

# ---------- Startup Hook ----------
@app.on_event("startup")
def startup():
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database setup completed.")

# ---------- Value Maps ----------
GENDER_MAP = {
    "мужской": GenderEnum.male,
    "женский": GenderEnum.female,
    "иное": GenderEnum.other,
}

COLOR_MAP = {
    "черный": CarColorEnum.Black,
    "белый": CarColorEnum.White,
    "красный": CarColorEnum.Red,
    "синий": CarColorEnum.Blue,
    "зеленый": CarColorEnum.Green,
}

class RegisterUserRaw(BaseModel):
    username: str
    email: EmailStr
    password: str
    gender: str
    birth_date: str
    driving_experience: int
    car_brand: str
    car_color: str


class RegisterUser(BaseModel):
    username: str
    email: EmailStr
    password: str
    gender: GenderEnum
    birth_date: datetime.date
    driving_experience: int
    car_brand: CarBrandEnum
    car_color: CarColorEnum

# ---------- Registration Endpoint ----------
@app.post("/register")
def register_user(user_raw: RegisterUserRaw = Body(...)):
    logger.info(f"Received registration data: {user_raw.dict()}")
    try:
        birth_date = datetime.datetime.strptime(user_raw.birth_date, "%Y-%m-%d").date()
        gender_value = GENDER_MAP.get(user_raw.gender.strip().lower())
        if not gender_value:
            raise HTTPException(status_code=400, detail="Неверное значение 'gender'")
        color_value = COLOR_MAP.get(user_raw.car_color.strip().lower())
        if not color_value:
            raise HTTPException(status_code=400, detail="Неверное значение 'car_color'")
        brand_value = CarBrandEnum(user_raw.car_brand.strip())

        user_data = RegisterUser(
            username=user_raw.username.strip(),
            email=user_raw.email.strip(),
            password=user_raw.password,
            gender=gender_value,
            birth_date=birth_date,
            driving_experience=user_raw.driving_experience,
            car_brand=brand_value,
            car_color=color_value
        )

    except Exception as e:
        logger.error(f"Error processing registration data: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обработки данных: {e}")

    db = SessionLocal()
    try:
        logger.info(f"Checking if email '{user_data.email}' already exists...")
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            logger.warning(f"Email {user_data.email} is already registered.")
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

        logger.info("Creating new user record...")
        user_obj = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            gender=user_data.gender,
            birth_date=user_data.birth_date,
            driving_experience=user_data.driving_experience,
            car_brand=user_data.car_brand,
            car_color=user_data.car_color
        )
        logger.info(f"Adding user to DB session: {user_obj}")
        db.add(user_obj)
        db.commit()
        logger.info(f"User {user_data.email} successfully registered.")
        print(f"DEBUG: User {user_data.email} registered successfully.")

        return {"message": "Регистрация успешна"}
    except Exception as e:
        logger.error(f"Error during DB operation: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {e}")
    finally:
        logger.info("Closing database session.")
        db.close()

from fastapi import Depends
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

from geoalchemy2.functions import ST_Contains
from geoalchemy2 import functions as geo_func
from sqlalchemy import func
from pydantic import BaseModel

class TripPointRequest(BaseModel):
    latitude: float
    longitude: float

@app.post("/login")
def login_user(login_data: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            raise HTTPException(status_code=400, detail="Неверный email или пароль")
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=400, detail="Неверный email или пароль")

        return {
                   "message": "Авторизация успешна",
                   "user_id": user.user_id,
                   "name": user.username,
                   "email": user.email
               }

    finally:
        db.close()


@app.post("/check-danger-zone")
def check_danger_zone(point: TripPointRequest):
    db = SessionLocal()
    try:
        # Создаём точку PostGIS
        point_geom = func.ST_SetSRID(
            func.ST_MakePoint(point.longitude, point.latitude),
            4326
        )

        # Проверяем, входит ли точка в какой-либо полигон
        danger_zone = db.query(DangerZone).filter(
            func.ST_Contains(DangerZone.polygon, point_geom)
        ).first()

        if danger_zone:
            return {"in_danger_zone": True}
        else:
            return {"in_danger_zone": False}

    finally:
        db.close()


class TripCreate(BaseModel):
    user_id: PyUUID
    start_time: datetime.datetime


class TripUpdate(BaseModel):
    end_time: datetime.datetime
    # В километрах, без конвертации.
    total_distance: float = Field(ge=0)


class EventItem(BaseModel):
    event_time: datetime.datetime
    event_type: str
    severity: str
    points: int
    latitude: float
    longitude: float


class EventsBulkCreate(BaseModel):
    trip_id: PyUUID
    events: List[EventItem]


@app.post("/trips")
def create_trip(trip_data: TripCreate):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == trip_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_trip = Trip(
            user_id=trip_data.user_id,
            start_time=trip_data.start_time,
        )

        db.add(new_trip)
        db.commit()
        db.refresh(new_trip)

        # Критично для фронта: должен вернуться id поездки.
        return {"id": new_trip.trip_id, "trip_id": new_trip.trip_id}
    finally:
        db.close()


@app.patch("/trips/{trip_id}")
def finish_trip(trip_id: PyUUID, trip_data: TripUpdate):
    db = SessionLocal()
    try:
        trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        trip.end_time = trip_data.end_time
        trip.total_distance = trip_data.total_distance

        db.commit()
        return {"message": "Trip updated"}
    finally:
        db.close()


@app.post("/events")
def create_events(payload: EventsBulkCreate):
    db = SessionLocal()
    try:
        trip = db.query(Trip).filter(Trip.trip_id == payload.trip_id).first()
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        for event in payload.events:
            db.add(
                Event(
                    trip_id=payload.trip_id,
                    event_time=event.event_time,
                    event_type=EventTypeEnum(event.event_type),
                    severity=SeverityEnum(event.severity),
                    points=event.points,
                    latitude=event.latitude,
                    longitude=event.longitude,
                )
            )

        db.commit()
        # Фронту достаточно статуса 200.
        return {"message": "Events saved"}
    finally:
        db.close()

from fastapi import Query
from sqlalchemy import extract

from sqlalchemy import func
from collections import defaultdict
from datetime import timedelta


@app.get("/stats/daily")
def get_daily_stats(user_id: PyUUID = Query(...), date: datetime.date = Query(...)):
    db = SessionLocal()
    try:
        # --- получаем поездки пользователя за день ---
        trips = db.query(Trip).filter(
            Trip.user_id == user_id,
            func.date(Trip.start_time) == date
        ).all()

        if not trips:
            return {"has_data": False}

        trip_ids = [t.trip_id for t in trips]

        # --- получаем все события по этим поездкам ---
        events = db.query(Event).filter(
            Event.trip_id.in_(trip_ids)
        ).all()

        # ---------- МАНЕВРЫ ПО ТИПАМ + ОПАСНОСТИ (для stacked bar) ----------
        maneuver_type_severity = {
            "acceleration": {"soft": 0, "medium": 0, "dangerous": 0},
            "braking": {"soft": 0, "medium": 0, "dangerous": 0},
            "turn": {"soft": 0, "medium": 0, "dangerous": 0},
        }

        for e in events:
            # В вашей модели event_type/severity могут приходить как Enum или str
            et = e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type)
            sv = e.severity.value if hasattr(e.severity, "value") else str(e.severity)

            if et in maneuver_type_severity and sv in maneuver_type_severity[et]:
                maneuver_type_severity[et][sv] += 1

        # ---------- МАНЕВРЫ ----------
        soft = sum(1 for e in events if e.severity.value == "soft")
        medium = sum(1 for e in events if e.severity.value == "medium")
        dangerous = sum(1 for e in events if e.severity.value == "dangerous")

        # ---------- ОЧКИ ----------
        total_points = sum(e.points or 0 for e in events)

        # ---------- ДЛИТЕЛЬНОСТЬ ----------
        total_duration_min = sum(
            ((t.end_time - t.start_time).total_seconds() / 60)
            for t in trips if t.start_time and t.end_time
        )

        # ---------- ПОЧАСОВАЯ СТАТИСТИКА ----------
        points_by_hour = [0] * 24
        for e in events:
            if e.event_time:
                hour = e.event_time.hour
                points_by_hour[hour] += int(e.points or 0)

        # ---------- ДИНАМИКА МАНЕВРОВ ПО 5-МИНУТНЫМ ИНТЕРВАЛАМ В АКТИВНОЕ ВРЕМЯ ----------
                # Берем только интервалы, которые попадают в реальные поездки пользователя за день.
                # Если поездки: 14:00-15:00, график будет только для этого активного диапазона.
                interval_minutes = 5

                # Нормализуем поездки (только валидные интервалы)
                trip_windows = []
                for t in trips:
                    if t.start_time and t.end_time and t.end_time > t.start_time:
                        trip_windows.append((t.start_time, t.end_time))

                if trip_windows:
                    active_start = min(w[0] for w in trip_windows)
                    active_end = max(w[1] for w in trip_windows)

                    # Выравниваем начало/конец к сетке 5 минут
                    aligned_start = active_start.replace(second=0, microsecond=0)
                    aligned_start -= timedelta(minutes=aligned_start.minute % interval_minutes)

                    aligned_end = active_end.replace(second=0, microsecond=0)
                    if (aligned_end.minute % interval_minutes) != 0:
                        aligned_end += timedelta(minutes=interval_minutes - (aligned_end.minute % interval_minutes))

                    # Генерируем слоты [slot, slot+5min)
                    slots = []
                    cur = aligned_start
                    while cur < aligned_end:
                        slots.append(cur)
                        cur += timedelta(minutes=interval_minutes)

                    soft_by_slot = defaultdict(int)
                    medium_by_slot = defaultdict(int)
                    dangerous_by_slot = defaultdict(int)

                    def in_any_trip_window(dt: datetime) -> bool:
                        for ws, we in trip_windows:
                            if ws <= dt < we:
                                return True
                        return False

                    for e in events:
                        if not e.event_time or not e.severity.value:
                            continue

                        # только активное время поездки
                        if not in_any_trip_window(e.event_time):
                            continue

                        minute_bucket = (e.event_time.minute // interval_minutes) * interval_minutes
                        bucket_time = e.event_time.replace(
                            minute=minute_bucket,
                            second=0,
                            microsecond=0,
                        )

                        if e.severity.value == "soft":
                            soft_by_slot[bucket_time] += 1
                        elif e.severity.value == "medium":
                            medium_by_slot[bucket_time] += 1
                        elif e.severity.value == "dangerous":
                            dangerous_by_slot[bucket_time] += 1

                    maneuver_timeline = {
                        "labels": [s.strftime("%H:%M") for s in slots],
                        "soft": [soft_by_slot[s] for s in slots],
                        "medium": [medium_by_slot[s] for s in slots],
                        "dangerous": [dangerous_by_slot[s] for s in slots],
                        "intervalMinutes": interval_minutes,
                        "activeWindow": {
                            "start": active_start.strftime("%H:%M"),
                            "end": active_end.strftime("%H:%M"),
                        },
                    }
                else:
                    maneuver_timeline = {
                        "labels": [],
                        "soft": [],
                        "medium": [],
                        "dangerous": [],
                        "intervalMinutes": interval_minutes,
                        "activeWindow": None,
                    }

                return {
                    "has_data": True,
                    "maneuvers": {
                        "soft": soft,
                        "medium": medium,
                        "dangerous": dangerous
                    },
                    "durationHours": round(total_duration_min),
                    "totalPoints": total_points,
                    "pointsByHour": points_by_hour,
                    "maneuverTimeline": maneuver_timeline,
                    "maneuverTypeSeverity": maneuver_type_severity
                }
    finally:
        db.close()


from typing import List, Dict, Optional

def _as_str(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _calc_driving_style(total: int, dangerous: int, medium: int, soft: int) -> str:
    if total <= 0:
        return DrivingStyleEnum.undefined.value

    # --- доли ---
    dangerous_ratio = dangerous / total
    medium_ratio = medium / total
    soft_ratio = soft / total

    # --- веса (ключевая идея) ---
    weighted_score = (soft * 1) + (medium * 2) + (dangerous * 4)
    aggression_index = weighted_score / total

    # --- ЛОГИКА ---

    # 🔴 Агрессивный
    if dangerous_ratio >= 0.25 or aggression_index >= 2.5:
        return DrivingStyleEnum.aggressive.value

    # 🟡 Динамичный
    if dangerous_ratio >= 0.15 or aggression_index >= 1.8:
        return DrivingStyleEnum.dynamic.value

    # 🟢 Плавный
    return DrivingStyleEnum.careful.value


def _calc_level(total_points: int) -> Dict[str, int]:
    # Простая линейная шкала, чтобы фронт всегда получал валидные данные.
    points_per_level = 100
    current_level = max(1, (total_points // points_per_level) + 1)
    points_for_current_level_start = (current_level - 1) * points_per_level
    current_points = total_points - points_for_current_level_start
    return {
        "currentLevel": current_level,
        "currentPoints": current_points,
        "pointsForNextLevel": points_per_level,
    }


@app.get("/stats/summary")
def get_stats_summary(
    user_id: uuid.UUID = Query(..., description="UUID пользователя"),
    days: int = Query(30, ge=1, le=365),
):
    db = SessionLocal()
    try:
        user_exists = db.query(User.user_id).filter(User.user_id == user_id).first()
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")

        # 1. Получаем дату первой поездки
        first_trip = db.query(Trip.start_time).filter(Trip.user_id == user_id).order_by(Trip.start_time.asc()).first()

        if not first_trip:
            # Пользователь ещё не ездил – тренды пока бессмысленно показывать
            return {
                "message": "Недостаточно данных для отображения трендов",
                "show_trends": False
            }

        first_trip_date = first_trip[0].date()
        today = datetime.date.today()

        # 2. Вычисляем диапазон для тренда
        actual_days = min(days, (today - first_trip_date).days + 1)
        start_date = today - datetime.timedelta(days=actual_days - 1)

        trips = (
            db.query(Trip.trip_id, Trip.start_time, Trip.end_time, Trip.total_distance)
            .filter(
                Trip.user_id == user_id,
                func.date(Trip.start_time) >= start_date,
                func.date(Trip.start_time) <= today,
            )
            .all()
        )

        trip_ids = [row.trip_id for row in trips]
        if not trip_ids:
            empty_series = [{"dayIndex": i, "count": 0} for i in range(days)]
            return {
                "currentLevel": 1,
                "currentPoints": 0,
                "pointsForNextLevel": 100,
                "drivingStyle": DrivingStyleEnum.undefined.value,
                "smoothManeuversOverTime30d": empty_series,
                "mediumManeuversOverTime30d": empty_series,
                "dangerousManeuversOverTime30d": empty_series,
                "brakeByType30d": {"smooth": 0, "medium": 0, "dangerous": 0},
                "turnByType30d": {"smooth": 0, "medium": 0, "dangerous": 0},
                "accelerationByType30d": {"smooth": 0, "medium": 0, "dangerous": 0},
            }

        events = (
            db.query(Event)
            .filter(
                Event.trip_id.in_(trip_ids),
                func.date(Event.event_time) >= start_date,
                func.date(Event.event_time) <= today,
            )
            .all()
        )

        TrendWord = Literal["better", "worse", "stable", "more", "less"]

        @dataclass(frozen=True)
        class TrendResult:
            slope: float
            intercept: float
            r2: float
            trend: TrendWord
            line: List[float]


        def _linear_regression(values: Sequence[float]) -> Tuple[float, float, float]:
            """OLS y = a*x + b for x=[0..n-1]. Returns (a, b, r2)."""
            n = len(values)
            if n < 2:
                return 0.0, float(values[0] if values else 0.0), 0.0

            x_mean = (n - 1) / 2
            y_mean = sum(values) / n

            ss_xx = 0.0
            ss_xy = 0.0
            ss_tot = 0.0

            for i, y in enumerate(values):
                dx = i - x_mean
                dy = y - y_mean
                ss_xx += dx * dx
                ss_xy += dx * dy
                ss_tot += dy * dy

            if ss_xx == 0:
                return 0.0, y_mean, 0.0

            slope = ss_xy / ss_xx
            intercept = y_mean - slope * x_mean

            ss_res = 0.0
            for i, y in enumerate(values):
                y_hat = slope * i + intercept
                err = y - y_hat
                ss_res += err * err

            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            return slope, intercept, max(0.0, min(1.0, r2))


        def _is_slope_stable(values: Sequence[float], slope: float, min_effect_sigma: float = 0.5) -> bool:
            if len(values) < 2:
                return True

            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            sigma = sqrt(variance)

            # If signal has almost no variance, any tiny slope should be stable.
            if sigma < 1e-9:
                return abs(slope) < 1e-9

            # Compare full-window effect against volatility.
            full_window_effect = abs(slope) * (len(values) - 1)
            return full_window_effect < (sigma * min_effect_sigma)


        def classify_trend(
            values: Sequence[Optional[float]],
                *,
                positive_word: Literal["more", "better"] = "more",
                negative_word: Literal["less", "worse"] = "less",
            ) -> TrendResult:
                # исключаем дни без поездок
                filtered_values = [v for v in values if v is not None]

                slope, intercept, r2 = _linear_regression(filtered_values)
                if _is_slope_stable(filtered_values, slope):
                    trend: TrendWord = "stable"
                elif slope > 0:
                    trend = positive_word
                else:
                    trend = negative_word

                line = [slope * i + intercept for i in range(len(filtered_values))]
                return TrendResult(slope=slope, intercept=intercept, r2=r2, trend=trend, line=line)

        def build_daily_event_scores(
            events: Iterable[object],
            trips: Iterable[object],  # ← ДОБАВИЛИ
            *,
            start_date: datetime.date,
            days: int,
            soft_weight: float = 1.0,
            medium_weight: float = 2.0,
            dangerous_weight: float = 4.0,
        ) -> Dict[str, List[float]]:
            """
            Build per-day normalized badness score (per km) for:
            braking / turn / acceleration
            """

            # --- базовые бакеты ---
            buckets = {
                "braking": [0.0 for _ in range(days)],
                "turn": [0.0 for _ in range(days)],
                "acceleration": [0.0 for _ in range(days)],
            }

            # --- веса ---
            severity_weights = {
                "soft": soft_weight,
                "medium": medium_weight,
                "dangerous": dangerous_weight,
            }

            # --- 1. собираем события ---
            for e in events:
                event_time = getattr(e, "event_time", None)
                if event_time is None:
                    continue

                day_index = (event_time.date() - start_date).days
                if not (0 <= day_index < days):
                    continue

                event_type = _as_str(getattr(e, "event_type", ""))
                severity = _as_str(getattr(e, "severity", ""))

                if event_type not in buckets:
                    continue

                buckets[event_type][day_index] += severity_weights.get(severity, 0.0)

            # --- 2. собираем дистанцию ---
            distance_by_day = [0.0 for _ in range(days)]

            for t in trips:
                start_time = getattr(t, "start_time", None)
                if start_time is None:
                    continue

                day_index = (start_time.date() - start_date).days
                if not (0 <= day_index < days):
                    continue

                distance = float(getattr(t, "total_distance", 0.0) or 0.0)
                distance_by_day[day_index] += (distance + 1)

            # --- 3. нормализация (САМОЕ ВАЖНОЕ) ---
            for i in range(days):
                distance = distance_by_day[i]

                if distance <= 0:
                    # день без поездок → не учитывать в тренде
                    buckets["braking"][i] = None
                    buckets["turn"][i] = None
                    buckets["acceleration"][i] = None
                else:
                    buckets["braking"][i] /= distance
                    buckets["turn"][i] /= distance
                    buckets["acceleration"][i] /= distance

            return buckets


        def build_daily_trip_time(trips: Iterable[object], *, start_date: datetime.date, days: int) -> List[float]:
            """Average trip duration in seconds per day."""
            sums = [0.0 for _ in range(days)]
            counts = [0 for _ in range(days)]

            for t in trips:
                start_time = getattr(t, "start_time", None)
                end_time = getattr(t, "end_time", None)
                if start_time is None or end_time is None:
                    continue

                day_index = (start_time.date() - start_date).days
                if day_index < 0 or day_index >= days:
                    continue

                seconds = (end_time - start_time).total_seconds()
                if seconds < 0:
                    continue

                sums[day_index] += seconds
                counts[day_index] += 1

            return [(sums[i] / counts[i]) if counts[i] else 0.0 for i in range(days)]


        def calculate_summary_trends(
            *,
            events: Sequence[object],
            trips: Sequence[object],
            start_date: datetime.date,
            days: int,
        ) -> Dict[str, str]:

            # --- используем уже нормальные score ---
            event_scores = build_daily_event_scores(
                events,
                trips,
                start_date=start_date,
                days=days,
                soft_weight=1.0,
                medium_weight=2.0,
                dangerous_weight=4.0,
            )

            trip_time_series = build_daily_trip_time(
                trips,
                start_date=start_date,
                days=days
            )

            # --- ТРЕНДЫ ПО ТИПАМ МАНЕВРОВ ---
            braking_trend = classify_trend(
                event_scores["braking"],
                positive_word="worse",   # больше score = хуже
                negative_word="better"
            )

            turn_trend = classify_trend(
                event_scores["turn"],
                positive_word="worse",
                negative_word="better"
            )

            acceleration_trend = classify_trend(
                event_scores["acceleration"],
                positive_word="worse",
                negative_word="better"
            )

            # --- тренд времени поездок ---
            trip_time_trend = classify_trend(
                trip_time_series,
                positive_word="more",
                negative_word="less"
            )

            return {
                "brakingTrend": braking_trend.trend,
                "turnTrend": turn_trend.trend,
                "accelerationTrend": acceleration_trend.trend,
                "tripTimeTrend": trip_time_trend.trend,
            }

        trends = calculate_summary_trends(
            events=events,
            trips=trips,
            start_date=start_date,
            days=days,
        )



        daily_smooth = [0 for _ in range(days)]
        daily_medium = [0 for _ in range(days)]
        daily_dangerous = [0 for _ in range(days)]

        type_buckets: Dict[str, Dict[str, int]] = {
            "braking": {"smooth": 0, "medium": 0, "dangerous": 0},
            "turn": {"smooth": 0, "medium": 0, "dangerous": 0},
            "acceleration": {"smooth": 0, "medium": 0, "dangerous": 0},
        }

        total_points = 0
        total_events = 0
        total_medium = 0
        total_dangerous = 0

        for e in events:
            if e.event_time is None:
                continue
            day_idx = (e.event_time.date() - start_date).days
            if day_idx < 0 or day_idx >= days:
                continue

            severity = e.severity.value
            event_type = _as_str(e.event_type)

            if severity == "soft":
                daily_smooth[day_idx] += 1
                if event_type in type_buckets:
                    type_buckets[event_type]["smooth"] += 1
            elif severity == "medium":
                daily_medium[day_idx] += 1
                total_medium += 1
                if event_type in type_buckets:
                    type_buckets[event_type]["medium"] += 1
            elif severity == "dangerous":
                daily_dangerous[day_idx] += 1
                total_dangerous += 1
                if event_type in type_buckets:
                    type_buckets[event_type]["dangerous"] += 1

            total_events += 1
            total_points += int(e.points or 0)

        level = _calc_level(total_points)
        total_soft = total_events - total_medium - total_dangerous

        style = _calc_driving_style(
            total_events,
            total_dangerous,
            total_medium,
            total_soft
        )
        return {
            "currentLevel": level["currentLevel"],
            "currentPoints": level["currentPoints"],
            "pointsForNextLevel": level["pointsForNextLevel"],
            "drivingStyle": style,
            "smoothManeuversOverTime30d": [
                {"dayIndex": i, "count": daily_smooth[i]} for i in range(days)
            ],
            "mediumManeuversOverTime30d": [
                {"dayIndex": i, "count": daily_medium[i]} for i in range(days)
            ],
            "dangerousManeuversOverTime30d": [
                {"dayIndex": i, "count": daily_dangerous[i]} for i in range(days)
            ],
            "brakeByType30d": {
                "smooth": type_buckets["braking"]["smooth"],
                "medium": type_buckets["braking"]["medium"],
                "dangerous": type_buckets["braking"]["dangerous"],
            },
            "turnByType30d": {
                "smooth": type_buckets["turn"]["smooth"],
                "medium": type_buckets["turn"]["medium"],
                "dangerous": type_buckets["turn"]["dangerous"],
            },
            "accelerationByType30d": {
                "smooth": type_buckets["acceleration"]["smooth"],
                "medium": type_buckets["acceleration"]["medium"],
                "dangerous": type_buckets["acceleration"]["dangerous"],
            },
            "brakingTrend": trends["brakingTrend"],
                "turnTrend": trends["turnTrend"],
                "accelerationTrend": trends["accelerationTrend"],
                "tripTimeTrend": trends["tripTimeTrend"],
        }
    finally:
        db.close()

# ---------- Test Endpoint ----------
@app.get("/")
def read_root():
    logger.info("Root endpoint called.")
    return {"message": "Привет! FastAPI работает!"}


# ---------- Запуск сервера ----------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Render передаст свой порт, локально используем 8000
    uvicorn.run("main:app", host="0.0.0.0", port=port)
