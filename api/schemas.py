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
    pan_number: str = Field(min_length=10, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    aadhaar_number: str = Field(min_length=12, max_length=12, pattern=r"^\d{12}$")
    date_of_birth: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    permanent_address: str = Field(min_length=10, max_length=500)
    current_address: str = Field(min_length=10, max_length=500)
    same_as_permanent: bool = False
    reference_number: str | None = Field(default=None, max_length=50)
    selfie_image: str = Field(min_length=30)


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
    role: str
    date_of_birth: str | None = None
    pan_number: str | None = None
    aadhaar_number: str | None = None
    permanent_address: str | None = None
    current_address: str | None = None
    same_as_permanent: bool = False
    reference_number: str | None = None
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
