from enum import Enum


class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    CYBER_WARRIOR = "CYBER_WARRIOR"
    ADMIN = "ADMIN"


class ComplaintStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class ComplaintPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReportedSuspectIdentifierType(str, Enum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    UPI = "UPI"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    WEBSITE = "WEBSITE"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    OTHER = "OTHER"


class ReportedSuspectStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class WarriorVerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class WarriorApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ResumeParsingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WarriorReportType(str, Enum):
    THREAT = "THREAT"
    VULNERABILITY = "VULNERABILITY"
    SCAM = "SCAM"
    PHISHING = "PHISHING"
    MALWARE = "MALWARE"
    OSINT = "OSINT"
    OTHER = "OTHER"


class WarriorReportStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
