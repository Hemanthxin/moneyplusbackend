from pydantic import BaseModel, Field


class SendOtpRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")


class VerifyOtpRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class SessionPayload(BaseModel):
    mobile: str
    first_name: str


class VerifyOtpResponse(BaseModel):
    message: str
    onboarding_required: bool
    session: SessionPayload | None = None


class SendOtpResponse(BaseModel):
    message: str


class RegisterUserRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterUserResponse(BaseModel):
    message: str
    session: SessionPayload


class CreditScorePayload(BaseModel):
    score: int
    label: str
    last_updated: str


class UserPayload(BaseModel):
    first_name: str
    last_name: str | None = None
    mobile: str
    email: str | None = None
    role: str
    onboarding_completed: bool = False


class ProductPayload(BaseModel):
    rank: int
    title: str
    subtitle: str
    features: list[str]


class DashboardPayload(BaseModel):
    user: UserPayload
    credit_score: CreditScorePayload
    products: list[ProductPayload]


class LenderPayload(BaseModel):
    rank: int
    name: str
    roi_min: float
    roi_max: float
    roi_label: str
    amount_min: int
    amount_max: int
    amount_label: str
    min_salary: int
    eligible: bool


class OffersResponse(BaseModel):
    product_title: str
    total_count: int
    eligible_count: int
    offers: list[LenderPayload]
