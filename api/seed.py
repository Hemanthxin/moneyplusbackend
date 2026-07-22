import re

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from .models import Lender, Product, User


PRODUCT_SEED = [
    {
        "rank": 1,
        "title": "Personal Loan",
        "subtitle": "Quick funds for your personal needs",
        "features": ["Up to \u20B950 Lakhs", "Interest from 10.49%"],
    },
    {
        "rank": 2,
        "title": "Business Loan",
        "subtitle": "Grow your business with ease",
        "features": ["Up to \u20B95 Crores", "Interest from 11.49%"],
    },
    {
        "rank": 3,
        "title": "Home Loan",
        "subtitle": "Fulfil your dream of owning a home",
        "features": ["Up to \u20B910 Crores", "Interest from 8.40%"],
    },
    {
        "rank": 4,
        "title": "Car Loan",
        "subtitle": "Drive your dream car today",
        "features": ["Up to \u20B975 Lakhs", "Interest from 8.99%"],
    },
    {
        "rank": 5,
        "title": "Health Insurance",
        "subtitle": "Secure your health, secure your future",
        "features": ["Family Floater Plans", "Cashless Hospitals"],
    },
    {
        "rank": 6,
        "title": "Term Insurance",
        "subtitle": "Life cover for your family's security",
        "features": ["High Coverage", "Low Premium"],
    },
    {
        "rank": 7,
        "title": "FD Credit Card",
        "subtitle": "Build credit with FD backed card",
        "features": ["100% Secured", "Improve CIBIL Score"],
    },
    {
        "rank": 8,
        "title": "Gold Loan",
        "subtitle": "Get instant loan against your gold",
        "features": ["Up to \u20B92 Crores", "Interest from 9.25%"],
    },
    {
        "rank": 9,
        "title": "FD / RD",
        "subtitle": "Save today for a better tomorrow",
        "features": ["FD: Up to 8.50%", "RD: Up to 7.50%"],
    },
]

# Raw rows straight from the partner-supplied rate sheet: (name, ROI range text,
# loan amount range text, minimum monthly salary, loan type). Kept as the
# original short-hand ("25T", "1CR", "1L") and parsed below rather than
# hand-transcribed as numbers, so the seed data matches the source exactly.
LENDER_RAW = [
    ("HDFC BANK", "9.99 TO 18%", "25T TO 1CR", 25000, "Personal Loan"),
    ("ICICI BANK", "9.99 TO 18%", "1L TO 1CR", 25000, "Personal Loan"),
    ("AXIS BANK", "9.99 TO 20%", "25T TO 1CR", 25000, "Personal Loan"),
    ("KOTAK BANK", "9.99 TO 22%", "50T TO 1CR", 25000, "Personal Loan"),
    ("INDUSIND BANK", "9.99 TO 25%", "50T TO 1CR", 25000, "Personal Loan"),
    ("IDFC BANK", "9.99 TO 25%", "50T TO 1CR", 20000, "Personal Loan"),
    ("BANDHAN BANK", "10.85 TO 25%", "50T TO 25L", 25000, "Personal Loan"),
    ("BAJAJ FINANCE", "10.85 TO 30%", "25T TO 1CR", 25000, "Personal Loan"),
    ("INCREAD FINANCE", "13 TO 35%", "25T TO 15L", 15000, "Personal Loan"),
    ("PRIMAL FINANCE", "13 TO 35%", "25T TO 50L", 20000, "Personal Loan"),
    ("POONAWALA", "13 TO 35%", "25T TO 60L", 25000, "Personal Loan"),
    ("CHOLA FINANCE", "13 TO 35%", "25T TO 50L", 25000, "Personal Loan"),
    ("FINNABLE FINANCE", "13 TO 35%", "25T TO 15L", 20000, "Personal Loan"),
    ("AXIS FINANCE", "13 TO 35%", "25T TO 50L", 25000, "Personal Loan"),
    ("SHRI RAM FINANCE", "13 TO 35%", "25T TO 30L", 25000, "Personal Loan"),
]

# Public logo files from Wikimedia Commons, keyed by the lender name above.
# A few smaller NBFCs (InCred, Poonawalla, Finnable) don't have a usable
# free-use logo file available, so they fall back to the initial badge.
LENDER_LOGOS = {
    "HDFC BANK": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/HDFC_Bank_Logo.svg/250px-HDFC_Bank_Logo.svg.png",
    "ICICI BANK": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ICICI_Bank_Logo.svg/250px-ICICI_Bank_Logo.svg.png",
    "AXIS BANK": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/AXISBank_Logo.svg/250px-AXISBank_Logo.svg.png",
    "KOTAK BANK": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3b/Kotak_Mahindra_Bank_logo.svg/250px-Kotak_Mahindra_Bank_logo.svg.png",
    "INDUSIND BANK": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/IndusInd_Bank_SVG_Logo.svg/250px-IndusInd_Bank_SVG_Logo.svg.png",
    "IDFC BANK": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Logo_of_IDFC_First_Bank.svg/250px-Logo_of_IDFC_First_Bank.svg.png",
    "BANDHAN BANK": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Bandhan_Bank_Svg_Logo.svg/250px-Bandhan_Bank_Svg_Logo.svg.png",
    "BAJAJ FINANCE": "https://upload.wikimedia.org/wikipedia/en/thumb/8/8b/Bajaj_Finance_Logo_2025.svg/250px-Bajaj_Finance_Logo_2025.svg.png",
    "PRIMAL FINANCE": "https://upload.wikimedia.org/wikipedia/en/thumb/d/dc/Piramal_Finance_logo.svg/250px-Piramal_Finance_logo.svg.png",
    "CHOLA FINANCE": "https://upload.wikimedia.org/wikipedia/en/thumb/1/14/Cholamandalam_Investment_and_Finance_Company.svg/250px-Cholamandalam_Investment_and_Finance_Company.svg.png",
    "AXIS FINANCE": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/AXISBank_Logo.svg/250px-AXISBank_Logo.svg.png",
    "SHRI RAM FINANCE": "https://upload.wikimedia.org/wikipedia/en/thumb/c/cf/Shriram_Group.svg/250px-Shriram_Group.svg.png",
}

_AMOUNT_UNITS = {"T": 1_000, "L": 100_000, "CR": 10_000_000}


def _parse_amount_token(token: str) -> int:
    match = re.match(r"([\d.]+)\s*(T|L|CR)", token.strip().upper())
    if not match:
        raise ValueError(f"Unrecognized amount token: {token!r}")
    value, unit = match.groups()
    return round(float(value) * _AMOUNT_UNITS[unit])


def _format_amount_token(rupees: int) -> str:
    for unit, factor in (("CR", 10_000_000), ("L", 100_000), ("T", 1_000)):
        if rupees % factor == 0:
            return f"{rupees // factor}{unit}"
    return str(rupees)


def _parse_range(text_value: str, parser) -> tuple[float, float]:
    low_text, high_text = (part.strip() for part in re.split(r"TO|-", text_value, maxsplit=1))
    return parser(low_text), parser(high_text)


def _build_lender_seed() -> list[dict]:
    rows = []
    for rank, (name, roi_text, amount_text, min_salary, product_title) in enumerate(LENDER_RAW, start=1):
        roi_min, roi_max = _parse_range(roi_text, lambda part: float(part.rstrip("%")))
        amount_min, amount_max = _parse_range(amount_text, _parse_amount_token)
        rows.append(
            {
                "rank": rank,
                "product_title": product_title,
                "name": name,
                "roi_min": roi_min,
                "roi_max": roi_max,
                "roi_label": f"{roi_min:g}% - {roi_max:g}%",
                "amount_min": amount_min,
                "amount_max": amount_max,
                "amount_label": f"₹{_format_amount_token(amount_min)} - ₹{_format_amount_token(amount_max)}",
                "min_salary": min_salary,
                "logo_url": LENDER_LOGOS.get(name),
            }
        )
    return rows


LENDER_SEED = _build_lender_seed()


USER_TABLE_PATCHES = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS pan_number VARCHAR(10)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS aadhaar_number VARCHAR(12)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth VARCHAR(10)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS permanent_address TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_address TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS same_as_permanent BOOLEAN DEFAULT FALSE NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS reference_number VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS selfie_image TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW() NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW() NOT NULL",
    "ALTER TABLE lenders ADD COLUMN IF NOT EXISTS logo_url TEXT",
]


async def ensure_database_schema(connection: AsyncConnection) -> None:
    for statement in USER_TABLE_PATCHES:
        await connection.execute(text(statement))


DEMO_MOBILE = "9876543210"


async def seed_database(session: AsyncSession) -> None:
    demo_user = await session.scalar(select(User).where(User.mobile == DEMO_MOBILE))
    if not demo_user:
        session.add(
            User(
                first_name="Arjun",
                last_name="Sharma",
                mobile=DEMO_MOBILE,
                role="Financial Partner",
                credit_score=742,
                credit_label="Good",
                credit_last_updated="20 May 2025",
                onboarding_completed=True,
            )
        )
    elif not demo_user.onboarding_completed:
        # A later schema migration added onboarding_completed with a NOT NULL
        # DEFAULT FALSE, which silently flipped this already-seeded demo user
        # back to "incomplete". Self-heal it so the demo login keeps working.
        demo_user.onboarding_completed = True

    existing_products = await session.scalar(select(Product.id))
    if not existing_products:
        await session.execute(delete(Product))
        session.add_all([Product(**product) for product in PRODUCT_SEED])

    # Rate-sheet data changes independently of a schema migration, so keep it
    # fully in sync with LENDER_SEED on every startup rather than seeding once.
    await session.execute(delete(Lender))
    session.add_all([Lender(**lender) for lender in LENDER_SEED])

    await session.commit()
