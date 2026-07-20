from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from app.config import settings
    from app.db import Base, engine, get_db
    from app.models import OtpSession, Product, User
    from app.schemas import (
        DashboardPayload,
        RegisterUserRequest,
        RegisterUserResponse,
        SendOtpRequest,
        SendOtpResponse,
        VerifyOtpRequest,
        VerifyOtpResponse,
    )
    from app.seed import ensure_database_schema, seed_database
else:
    from .config import settings
    from .db import Base, engine, get_db
    from .models import OtpSession, Product, User
    from .schemas import (
        DashboardPayload,
        RegisterUserRequest,
        RegisterUserResponse,
        SendOtpRequest,
        SendOtpResponse,
        VerifyOtpRequest,
        VerifyOtpResponse,
    )
    from .seed import ensure_database_schema, seed_database

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await ensure_database_schema(connection)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await seed_database(session)

    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_session_payload(user: User) -> dict[str, str]:
    return {
        "mobile": user.mobile,
        "first_name": user.first_name,
    }


def split_full_name(full_name: str) -> tuple[str, str | None]:
    parts = [part for part in full_name.strip().split() if part]
    first_name = parts[0] if parts else "User"
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    return first_name, last_name


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/send-otp", response_model=SendOtpResponse)
async def send_otp(payload: SendOtpRequest, db: AsyncSession = Depends(get_db)) -> SendOtpResponse:
    await db.execute(delete(OtpSession).where(OtpSession.mobile == payload.mobile))
    db.add(OtpSession(mobile=payload.mobile, otp_code=settings.dev_demo_otp))
    await db.commit()

    message = "OTP sent successfully."
    if settings.debug:
        message = f"{message} Use {settings.dev_demo_otp} in development."

    return SendOtpResponse(message=message)


@app.post("/api/auth/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(payload: VerifyOtpRequest, db: AsyncSession = Depends(get_db)) -> VerifyOtpResponse:
    otp_session = await db.scalar(
        select(OtpSession).where(OtpSession.mobile == payload.mobile, OtpSession.otp_code == payload.otp)
    )
    user = await db.scalar(select(User).where(User.mobile == payload.mobile))
    if not otp_session:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    await db.execute(delete(OtpSession).where(OtpSession.mobile == payload.mobile))
    await db.commit()

    if not user:
        return VerifyOtpResponse(
            message="OTP verified. Complete your onboarding to continue.",
            onboarding_required=True,
            session=None,
        )

    if not user.onboarding_completed:
        return VerifyOtpResponse(
            message="OTP verified. Complete your onboarding to continue.",
            onboarding_required=True,
            session=None,
        )

    return VerifyOtpResponse(
        message="Authenticated successfully",
        onboarding_required=False,
        session=build_session_payload(user),
    )


@app.post("/api/auth/register", response_model=RegisterUserResponse)
async def register_user(payload: RegisterUserRequest, db: AsyncSession = Depends(get_db)) -> RegisterUserResponse:
    if not payload.selfie_image.startswith("data:image/"):
        raise HTTPException(status_code=422, detail="Please upload a valid selfie image")

    first_name, last_name = split_full_name(payload.full_name)
    current_address = payload.permanent_address if payload.same_as_permanent else payload.current_address

    existing_user = await db.scalar(select(User).where(User.mobile == payload.mobile))
    pan_user = await db.scalar(select(User).where(User.pan_number == payload.pan_number, User.mobile != payload.mobile))
    aadhaar_user = await db.scalar(
        select(User).where(User.aadhaar_number == payload.aadhaar_number, User.mobile != payload.mobile)
    )

    if pan_user:
        raise HTTPException(status_code=409, detail="PAN card number is already linked to another user")
    if aadhaar_user:
        raise HTTPException(status_code=409, detail="Aadhaar number is already linked to another user")

    if existing_user:
        user = existing_user
    else:
        user = User(
            first_name=first_name,
            last_name=last_name,
            mobile=payload.mobile,
            role="Financial Partner",
            credit_score=742,
            credit_label="Good",
            credit_last_updated="20 May 2025",
        )
        db.add(user)

    user.first_name = first_name
    user.last_name = last_name
    user.pan_number = payload.pan_number
    user.aadhaar_number = payload.aadhaar_number
    user.date_of_birth = payload.date_of_birth
    user.permanent_address = payload.permanent_address
    user.current_address = current_address
    user.same_as_permanent = payload.same_as_permanent
    user.reference_number = payload.reference_number
    user.selfie_image = payload.selfie_image
    user.onboarding_completed = True

    await db.commit()
    await db.refresh(user)

    return RegisterUserResponse(
        message="Registration completed successfully",
        session=build_session_payload(user),
    )


@app.get("/api/dashboard/overview", response_model=DashboardPayload)
async def dashboard_overview(
    mobile: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{10}$"),
    db: AsyncSession = Depends(get_db),
) -> DashboardPayload:
    user = await db.scalar(select(User).where(User.mobile == mobile))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.onboarding_completed:
        raise HTTPException(status_code=403, detail="Complete onboarding to access the dashboard")

    products = (await db.scalars(select(Product).order_by(Product.rank.asc()))).all()

    return DashboardPayload(
        user={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "mobile": user.mobile,
            "role": user.role,
            "date_of_birth": user.date_of_birth,
            "pan_number": user.pan_number,
            "aadhaar_number": user.aadhaar_number,
            "permanent_address": user.permanent_address,
            "current_address": user.current_address,
            "same_as_permanent": user.same_as_permanent,
            "reference_number": user.reference_number,
            "onboarding_completed": user.onboarding_completed,
        },
        credit_score={
            "score": user.credit_score,
            "label": user.credit_label,
            "last_updated": user.credit_last_updated,
        },
        products=[
            {
                "rank": product.rank,
                "title": product.title,
                "subtitle": product.subtitle,
                "features": product.features,
            }
            for product in products
        ],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
