from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import CVTemplate, Package


async def seed_packages(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(Package))
    if result.scalar_one() > 0:
        return

    db.add_all(
        [
            Package(
                name="Basic",
                slug="basic",
                description={
                    "id": "Paket CV dasar dengan 2 revisi.",
                    "en": "Basic CV package with 2 revisions.",
                },
                price=75000,
                max_revisions=2,
                includes_letter=False,
                includes_linkedin=False,
                priority_support=False,
                sort_order=1,
            ),
            Package(
                name="Professional",
                slug="professional",
                description={
                    "id": "Paket CV profesional dengan 2 revisi, surat lamaran, dan template modern.",
                    "en": "Professional CV package with 2 revisions, cover letter, and modern template.",
                },
                price=150000,
                max_revisions=2,
                includes_letter=True,
                includes_linkedin=False,
                priority_support=False,
                sort_order=2,
            ),
            Package(
                name="Premium",
                slug="premium",
                description={
                    "id": "Paket lengkap dengan revisi tanpa batas, surat lamaran, LinkedIn, dan prioritas.",
                    "en": "Complete package with unlimited revisions, cover letter, LinkedIn, and priority support.",
                },
                price=250000,
                max_revisions=-1,
                includes_letter=True,
                includes_linkedin=True,
                priority_support=True,
                sort_order=3,
            ),
        ]
    )


async def seed_templates(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(CVTemplate))
    if result.scalar_one() > 0:
        return

    db.add_all(
        [
            CVTemplate(
                name="Modern",
                slug="modern",
                description={
                    "id": "Desain bersih dengan aksen warna dan layout sidebar.",
                    "en": "Clean design with colorful accents and sidebar layout.",
                },
                sort_order=1,
            ),
            CVTemplate(
                name="Classic",
                slug="classic",
                description={
                    "id": "Desain tradisional, formal, dan abadi.",
                    "en": "Traditional and formal timeless design.",
                },
                sort_order=2,
            ),
            CVTemplate(
                name="ATS-Friendly",
                slug="ats-friendly",
                description={
                    "id": "Format minimal, dioptimalkan dengan kata kunci untuk ATS.",
                    "en": "Minimal formatting, keyword optimized for ATS.",
                },
                sort_order=3,
            ),
        ]
    )


async def seed_data(db: AsyncSession) -> None:
    await seed_packages(db)
    await seed_templates(db)
    await db.commit()
