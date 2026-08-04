"""Offline news corpus (Task 6.1).

Written for this repository to exercise the pipeline: deduplication, recency
decay, tier weighting and actionability detection. Dates are relative to the
run date so recency behaves sensibly whenever the suite is executed.

These are NOT real articles. They are plausible synthetic items standing in for
a real feed, and the URLs point at allowlisted domains so the guard can be
exercised without any network. Nothing here should be presented to a founder as
real reporting — the board labels the provider, so a fixture-backed board is
visibly a demo.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.news.models import RawArticle


def _d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


ARTICLES: list[RawArticle] = [
    RawArticle(
        source_id="startuptn",
        title="TANSEED 6.0 applications open for early-stage Tamil Nadu startups",
        url="https://startuptn.in/tanseed-6-applications-open/",
        published=_d(1),
        extract=(
            "StartupTN has opened applications for the sixth edition of TANSEED, its "
            "early-stage grant for startups registered in Tamil Nadu. Selected startups "
            "receive up to Rs 10 lakh. The last date for application is four weeks away."
        ),
        tags=("schemes", "tn", "funding", "deadline"),
    ),
    RawArticle(
        source_id="tansim",
        title="Tamil Nadu announces cluster support for Coimbatore engineering MSMEs",
        url="https://tansim.tn.gov.in/coimbatore-cluster-support/",
        published=_d(3),
        extract=(
            "A new cluster programme will provide shared testing facilities and working "
            "capital subsidy to engineering MSMEs in Coimbatore. Registration for the "
            "first cohort opens this month."
        ),
        tags=("schemes", "tn", "msme", "coimbatore"),
    ),
    RawArticle(
        source_id="startupindia",
        title="DPIIT revises recognition criteria for startups",
        url="https://www.startupindia.gov.in/notifications/dpiit-recognition-update",
        published=_d(6),
        extract=(
            "The Department for Promotion of Industry and Internal Trade has updated the "
            "eligibility conditions for startup recognition, including turnover limits and "
            "the definition of the incorporation window."
        ),
        tags=("dpiit", "policy", "national"),
    ),
    # --- deliberate near-duplicate of the DPIIT story, from a weaker tier ---
    RawArticle(
        source_id="inc42",
        title="DPIIT revises startup recognition criteria",
        url="https://inc42.com/buzz/dpiit-revises-startup-recognition-criteria/",
        published=_d(6),
        extract=(
            "DPIIT has updated startup recognition norms, changing turnover thresholds and "
            "the incorporation window used to assess eligibility."
        ),
        tags=("dpiit", "policy"),
    ),
    RawArticle(
        source_id="businessline",
        title="Tiruppur knitwear exporters report improved order flow",
        url="https://www.thehindubusinessline.com/economy/tiruppur-knitwear-orders/",
        published=_d(4),
        extract=(
            "Knitwear exporters in Tiruppur are seeing a recovery in order volumes, with "
            "buyers advancing their procurement schedules for the coming season."
        ),
        tags=("tn", "textile", "tiruppur", "business"),
    ),
    RawArticle(
        source_id="dinamalar",
        title="தமிழ்நாட்டில் புதிய தொழில் முனைவோர் திட்டம் அறிவிப்பு",
        url="https://www.dinamalar.com/news/tn-entrepreneur-scheme",
        published=_d(2),
        extract=(
            "தமிழ்நாடு அரசு புதிய தொழில் முனைவோர் ஆதரவு திட்டத்தை அறிவித்துள்ளது. "
            "விண்ணப்பங்கள் அடுத்த மாதம் முதல் ஏற்கப்படும்."
        ),
        language="ta",
        tags=("tn", "schemes", "tamil"),
    ),
    RawArticle(
        source_id="yourstory",
        title="Chennai agritech startup raises seed round for irrigation sensors",
        url="https://yourstory.com/2026/chennai-agritech-seed-round",
        published=_d(8),
        extract=(
            "A Chennai-based agritech company building low-cost irrigation sensors has "
            "closed a seed round led by a South India focused fund, and plans to expand "
            "to farmer producer organisations across the state."
        ),
        tags=("startups", "funding", "agritech", "tn"),
    ),
    RawArticle(
        source_id="entrackr",
        title="Seed funding activity slows across Indian consumer startups",
        url="https://entrackr.com/2026/seed-funding-slowdown",
        published=_d(19),
        extract=(
            "Seed-stage deal counts have declined quarter on quarter, with investors "
            "concentrating cheques into fewer companies."
        ),
        tags=("funding", "startups"),
    ),
    RawArticle(
        source_id="msme",
        title="Credit guarantee cover enhanced for micro enterprises",
        url="https://msme.gov.in/credit-guarantee-enhanced",
        published=_d(11),
        extract=(
            "The credit guarantee scheme for micro and small enterprises has been extended "
            "with a higher cover ceiling. Lenders have been advised to pass the benefit on "
            "to eligible borrowers on application."
        ),
        tags=("schemes", "msme", "credit"),
    ),
    RawArticle(
        source_id="newindianexpress",
        title="Madurai industrial park to add plug-and-play units",
        url="https://www.newindianexpress.com/states/tamil-nadu/madurai-industrial-park",
        published=_d(14),
        extract=(
            "SIPCOT will add ready-built plug-and-play units at its Madurai park, aimed at "
            "small manufacturers who cannot fund their own construction."
        ),
        tags=("tn", "infrastructure", "madurai", "msme"),
    ),
]
