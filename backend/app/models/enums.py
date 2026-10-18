"""Domain enums (stored as VARCHAR; validated at the Pydantic/domain layer)."""

from enum import Enum

from app.core.stages import Stage


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class CasteCategory(str, Enum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"
    EWS = "ews"


class EntityType(str, Enum):
    PRIVATE_LIMITED = "private_limited"
    LLP = "llp"
    OPC = "opc"
    PARTNERSHIP = "partnership"
    SOLE_PROPRIETOR = "sole_proprietor"


# The one stage vocabulary (app.core.stages); kept under this name for the models.
StartupStage = Stage


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DocumentType(str, Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    COMMUNITY_CERTIFICATE = "community_certificate"
    GST_CERTIFICATE = "gst_certificate"
    INCORPORATION_CERTIFICATE = "incorporation_certificate"
    DPIIT_CERTIFICATE = "dpiit_certificate"
    MARK_SHEET = "mark_sheet"
    BANK_STATEMENT = "bank_statement"


# ── v2 hybrid-ideology fields (design ADDENDUM v2 · B1) ──
class EntryMode(str, Enum):
    IDEA = "idea"
    DOMAIN_ONLY = "domain_only"
    INTENT_ONLY = "intent_only"


class RegSubtype(str, Enum):
    REGISTERED_PRODUCT = "registered_product"  # 2A
    REGISTERED_NO_PRODUCT = "registered_no_product"  # 2B
    IDEA_WORKER_NO_COMPANY = "idea_worker_no_company"  # 2C
    UNREGISTERED = "unregistered"


class Terrain(str, Enum):
    URBAN_TECH = "urban_tech"
    RURAL_MICRO = "rural_micro"
    ACADEMIC_SPINOFF = "academic_spinoff"
    DEEP_TECH = "deep_tech"
