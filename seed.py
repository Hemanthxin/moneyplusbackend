from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from .models import Product, User


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

USER_TABLE_PATCHES = [
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
]


async def ensure_database_schema(connection: AsyncConnection) -> None:
    for statement in USER_TABLE_PATCHES:
        await connection.execute(text(statement))


async def seed_database(session: AsyncSession) -> None:
    user_exists = await session.scalar(select(User.id).where(User.mobile == "9876543210"))
    if not user_exists:
        session.add(
            User(
                first_name="Arjun",
                last_name="Sharma",
                mobile="9876543210",
                role="Financial Partner",
                credit_score=742,
                credit_label="Good",
                credit_last_updated="20 May 2025",
                onboarding_completed=True,
            )
        )

    existing_products = await session.scalar(select(Product.id))
    if not existing_products:
        await session.execute(delete(Product))
        session.add_all([Product(**product) for product in PRODUCT_SEED])

    await session.commit()
