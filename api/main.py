from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("moneyplus")

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from api.config import settings
    from api.db import Base, engine, get_db
    from api.models import Lender, OtpSession, Product, User
    from api.schemas import (
        DashboardPayload,
        LenderPayload,
        OffersResponse,
        RegisterUserRequest,
        RegisterUserResponse,
        SendOtpRequest,
        SendOtpResponse,
        VerifyOtpRequest,
        VerifyOtpResponse,
    )
    from api.seed import ensure_database_schema, seed_database
else:
    from .config import settings
    from .db import Base, engine, get_db
    from .models import Lender, OtpSession, Product, User
    from .schemas import (
        DashboardPayload,
        LenderPayload,
        OffersResponse,
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
    # Startup runs on every cold start of this serverless function. If Neon is
    # waking from suspend (or has a transient hiccup) this must not raise, or
    # Vercel returns a bare error page with no CORS headers - the browser then
    # reports the request as "Failed to fetch" instead of a real error.
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await ensure_database_schema(connection)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            await seed_database(session)
    except Exception:
        logger.exception("Startup schema/seed step failed; continuing so the API can still respond")

    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=r"http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?",
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


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "message": "MoneyPlus API is running"}


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico")
@app.get("/favicon.png")
async def favicon() -> Response:
    return Response(status_code=204)


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
    first_name, last_name = split_full_name(payload.full_name)

    existing_user = await db.scalar(select(User).where(User.mobile == payload.mobile))

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
    user.email = payload.email
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
            "email": user.email,
            "role": user.role,
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


@app.get("/api/offers", response_model=OffersResponse)
async def get_offers(
    product: str = Query(..., min_length=1, max_length=80),
    amount: int = Query(500_000, ge=0),
    monthly_income: int = Query(50_000, ge=0),
    db: AsyncSession = Depends(get_db),
) -> OffersResponse:
    lenders = (
        await db.scalars(
            select(Lender).where(Lender.product_title == product).order_by(Lender.rank.asc())
        )
    ).all()

    offers = [
        LenderPayload(
            rank=lender.rank,
            name=lender.name,
            logo_url=lender.logo_url,
            roi_min=lender.roi_min,
            roi_max=lender.roi_max,
            roi_label=lender.roi_label,
            amount_min=lender.amount_min,
            amount_max=lender.amount_max,
            amount_label=lender.amount_label,
            min_salary=lender.min_salary,
            eligible=(
                lender.amount_min <= amount <= lender.amount_max
                and monthly_income >= lender.min_salary
            ),
        )
        for lender in lenders
    ]

    eligible_offers = sorted((offer for offer in offers if offer.eligible), key=lambda offer: offer.roi_min)

    return OffersResponse(
        product_title=product,
        total_count=len(offers),
        eligible_count=len(eligible_offers),
        offers=eligible_offers,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
