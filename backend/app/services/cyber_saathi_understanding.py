import json
import re
from datetime import date, timedelta
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.schemas.cyber_saathi import (
    ConfidenceBand,
    CrimeDomain,
    Entity,
    EntityType,
    Intent,
    LanguageCode,
    Sentiment,
    UnderstandingResult,
    Urgency,
    confidence_band,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cyber_saathi"
TAXONOMY = json.loads((DATA_DIR / "taxonomy.json").read_text(encoding="utf-8"))

DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097f]")
WORD_PATTERN = re.compile(r"[a-zA-Z]+")
URL_PATTERN = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"(?<![\w.])[\w.+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?!\w)")
UPI_PATTERN = re.compile(
    r"(?<![\w.])[a-zA-Z0-9._-]{2,}@(upi|ybl|paytm|okaxis|okhdfcbank|oksbi|ibl|axl)(?![\w.])",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
TRANSACTION_PATTERN = re.compile(
    r"\b(?:(?:txn|utr|ref(?:erence)?)(?:\s*(?:id|no|number|#))?|"
    r"transaction\s*(?:id|no|number|#))\s*[:#-]?\s*([a-z0-9-]{6,30})\b",
    re.IGNORECASE,
)
AMOUNT_PATTERN = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*(?P<currency_value>[0-9][0-9,]*(?:\.[0-9]{1,2})?)"
    r"\s*(?P<currency_unit>hazaar|hazar|thousand|lakh|crore|हजार|लाख|करोड़)?|"
    r"(?P<unit_value>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*"
    r"(?P<unit>hazaar|hazar|thousand|lakh|crore|हजार|लाख|करोड़|rupees?|rupaye|रुपये|रुपए))",
    re.IGNORECASE,
)
COMPOSITE_AMOUNT_PATTERN = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*)?"
    r"(?P<major_value>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*"
    r"(?P<major_unit>lakh|crore|लाख|करोड़)\s*(?:and\s+)?"
    r"(?P<minor_value>[0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*"
    r"(?P<minor_unit>hazaar|hazar|thousand|lakh|हजार|लाख)"
    r"(?:\s*(?:rupees?|rupaye|रुपये|रुपए))?",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"\b(?:[0-2]?\d|3[01])[-/]?(?:0?\d|1[0-2])[-/]?(?:20)?\d{2}\b")
TIME_PATTERN = re.compile(
    r"\b(?:(?:[01]?\d|2[0-3]):[0-5]\d\s*(?:am|pm)?|(?:0?[1-9]|1[0-2])\s*(?:am|pm))\b",
    re.IGNORECASE,
)
USERNAME_PATTERN = re.compile(r"(?<![\w.@])@[a-zA-Z0-9_.]{2,30}\b")

HINGLISH_MARKERS = {
    "aaj", "abhi", "aaya", "aa", "hai", "hain", "hua", "hue", "kar", "karna",
    "karu", "karo", "koi", "ko", "mera", "mere", "meri", "mujhe", "nahi", "paise",
    "paisa", "par", "raha", "rahe", "rupaye", "se", "gaya", "gaye", "kya", "dhamki",
    "chahiye", "mil", "fake", "samajh", "samajh nahi",
}
LOSS_MARKERS = {
    "debited", "deducted", "money lost", "lost money", "cut gaye", "kat gaye", "कट गए",
    "पैसे गए", "transfer ho", "transfer karwa", "transfer karwa liye", "sent money",
    "payment kiya", "paise chale", "paise chale gaye", "sare paise", "सारे पैसे",
    "chale gaye", "chala gaya", "nikal gaye", "nikal gaya", "निकल गए", "चले गए",
}
RECENT_MARKERS = {"now", "today", "just now", "ongoing", "abhi", "aaj", "अभी", "आज"}
HIGH_URGENCY_MARKERS = {
    "threat", "threatening", "blackmail", "dhamki", "धमकी", "ब्लैकमेल", "ongoing",
    "right now", "abhi", "अभी",
}
CRITICAL_MARKERS = {"suicide", "self harm", "immediate danger", "life threat", "urgent help", "तुरंत मदद"}
CHILD_CONTEXT_PATTERN = re.compile(
    r"(?:\b(?:child|minor|underage|kid|schoolgirl|schoolboy|bachcha|baccha|bachchi|bacchi|"
    r"bacha|bache)\b|बच्च|नाबालिग|"
    r"\b(?:[1-9]|1[0-7])\s*(?:years?(?:\s+old)?|yrs?(?:\s+old)?|saal)(?:\s+(?:ka|ki|ke))?\b)",
    re.IGNORECASE,
)
INTIMATE_CONTENT_MARKERS = (
    "private photo", "private image", "private video", "intimate photo", "intimate image",
    "intimate video", "nude photo", "nude image", "nude video", "nudes", "revenge porn",
    "morphed photo", "morphed image", "अश्लील फोटो", "निजी फोटो", "निजी वीडियो",
)
IMAGE_ABUSE_MARKERS = (
    "blackmail", "sextortion", "leak", "upload", "post online", "share online", "viral",
    "threat", "dhamki", "force", "coerc", "maang", "मांग", "धमकी", "ब्लैकमेल",
    "वायरल", "अपलोड",
)
PROVIDERS = {
    "sbi": "SBI", "hdfc": "HDFC Bank", "icici": "ICICI Bank", "axis": "Axis Bank",
    "paytm": "Paytm", "phonepe": "PhonePe", "google pay": "Google Pay", "gpay": "Google Pay",
    "amazon pay": "Amazon Pay", "whatsapp": "WhatsApp",
}
PLATFORMS = ("instagram", "facebook", "whatsapp", "telegram", "x.com", "twitter", "snapchat", "youtube")
ACCOUNT_SERVICES = ("bank account", "email account", "social media account", "upi account", "wallet")
LOCATIONS = ("delhi", "mumbai", "ahmedabad", "bengaluru", "bangalore", "kolkata", "chennai", "pune", "jaipur")
CRITICAL_TYPES = {EntityType(value) for value in TAXONOMY["critical_entity_types"]}

NOISY_TOKEN_REPLACEMENTS = {
    "acount": "account",
    "adahr": "aadhaar",
    "adhar": "aadhaar",
    "bnak": "bank",
    "ciber": "cyber",
    "deepfek": "deepfake",
    "delevery": "delivery",
    "gruming": "grooming",
    "haced": "hacked",
    "harrasment": "harassment",
    "harrasing": "harassment",
    "lnik": "link",
    "polce": "police",
    "remot": "remote",
    "seler": "seller",
    "stoking": "stalking",
    "syber": "cyber",
    "thret": "threat",
    "morfed": "morphed",
    "morphd": "morphed",
    "morfd": "morphed",
    "mminor": "minor",
    "nbakli": "nakli",
    "minnor": "minor",
    "chlid": "child",
    "wommen": "women",
    "screnshot": "screenshot",
    "screenshort": "screenshot",
    "instgram": "instagram",
    "whatsap": "whatsapp",
    "phising": "phishing",
    "fising": "phishing",
    "img": "image",
    "kardiya": "kar diya",
    "krdiya": "kr diya",
    "karvadiya": "karva diya",
    "karwadiya": "karwa diya",
    "krvadiya": "krva diya",
    "krwadiya": "krwa diya",
}


class UnderstandingEngine:
    @classmethod
    def analyze(
        cls, message: str, preferred_language: LanguageCode | None = None
    ) -> UnderstandingResult:
        text = " ".join(message.strip().split())
        lowered = cls.normalize_query(text)
        language = cls.detect_language(text, preferred_language)
        response_language = cls.response_language(language, preferred_language)
        intent = cls.classify_intent(lowered)
        domain = cls.classify_domain(lowered)
        entities = cls.extract_entities(text)
        urgency = cls.classify_urgency(lowered, domain)
        sentiment = cls.classify_sentiment(lowered)
        confidence = cls.score_confidence(intent, domain, language, entities)
        band = confidence_band(confidence)
        needs_clarification = band != ConfidenceBand.HIGH

        return UnderstandingResult(
            language=language,
            response_language=response_language,
            intent=intent,
            crime_domain=domain,
            entities=entities,
            urgency=urgency,
            sentiment=sentiment,
            confidence=confidence,
            confidence_band=band,
            needs_clarification=needs_clarification,
            clarification_prompt=cls.clarification_prompt(
                band, intent, domain, response_language
            ),
        )

    @staticmethod
    def detect_language(
        message: str, preferred_language: LanguageCode | None = None
    ) -> LanguageCode:
        devanagari_count = len(DEVANAGARI_PATTERN.findall(message))
        latin_words = WORD_PATTERN.findall(message.casefold())
        if devanagari_count:
            return LanguageCode.MIXED if len(latin_words) > 4 else LanguageCode.HI
        if latin_words:
            marker_count = sum(word in HINGLISH_MARKERS for word in latin_words)
            if marker_count >= 2:
                return LanguageCode.HINGLISH
            return LanguageCode.EN
        return preferred_language or LanguageCode.MIXED

    @staticmethod
    def response_language(
        detected: LanguageCode, preferred_language: LanguageCode | None
    ) -> LanguageCode:
        if detected != LanguageCode.MIXED:
            return detected
        if preferred_language in {LanguageCode.EN, LanguageCode.HI, LanguageCode.HINGLISH}:
            return preferred_language
        return LanguageCode.HINGLISH

    @staticmethod
    def classify_intent(text: str) -> Intent:
        track_markers = [
            marker for marker in TAXONOMY["intents"]["track_report"] if marker != "track"
        ]
        if any(marker in text for marker in track_markers) or re.search(r"\btrack\b", text):
            return Intent.TRACK_REPORT
        if any(marker in text for marker in TAXONOMY["intents"]["cyber_warrior"]):
            return Intent.CYBER_WARRIOR
        if any(marker in text for marker in TAXONOMY["intents"]["explore_cyber_risk"]):
            return Intent.EXPLORE_CYBER_RISK
        if any(marker in text for marker in TAXONOMY["intents"]["check_identifier"]):
            return Intent.CHECK_IDENTIFIER
        if any(marker in text for marker in TAXONOMY["intents"]["report_incident"]):
            return Intent.REPORT_INCIDENT
        if any(marker in text for marker in LOSS_MARKERS):
            return Intent.REPORT_INCIDENT
        if any(marker in text for marker in TAXONOMY["intents"]["seek_guidance"]):
            return Intent.SEEK_GUIDANCE
        if any(marker in text for marker in TAXONOMY["intents"]["general_awareness"]):
            return Intent.GENERAL_AWARENESS
        if UnderstandingEngine.classify_domain(text) != CrimeDomain.UNKNOWN:
            return Intent.SEEK_GUIDANCE
        return Intent.UNKNOWN

    @staticmethod
    def normalize_query(message: str) -> str:
        """Normalize common citizen/STT noise without changing extracted values."""
        lowered = " ".join(message.casefold().split())
        tokens = re.findall(r"[a-z0-9\u0900-\u097f]+|[^a-z0-9\u0900-\u097f\s]", lowered)
        normalized = [NOISY_TOKEN_REPLACEMENTS.get(token, token) for token in tokens]
        result = re.sub(r"\s+([@:/.,!?])", r"\1", " ".join(normalized))
        return re.sub(r"\s*-\s*", "-", result)

    @staticmethod
    def has_child_context(text: str) -> bool:
        return bool(CHILD_CONTEXT_PATTERN.search(text))

    @staticmethod
    def has_intimate_image_abuse(text: str) -> bool:
        return any(marker in text for marker in INTIMATE_CONTENT_MARKERS) and any(
            marker in text for marker in IMAGE_ABUSE_MARKERS
        )

    @staticmethod
    def classify_domain(text: str) -> CrimeDomain:
        domain_markers = TAXONOMY["crime_domains"]
        # Safety-sensitive image abuse must win before broad financial words.
        # A blackmailer asking for money is not evidence that money was lost,
        # and an explicitly under-18 victim must stay on the child-safety path.
        child_context = UnderstandingEngine.has_child_context(text)
        intimate_image_abuse = UnderstandingEngine.has_intimate_image_abuse(text)
        if child_context and (
            intimate_image_abuse
            or any(
                marker in text
                for marker in (
                    "groom", "online friend", "secret request", "send photo", "bhejne",
                    "bully", "harass", "threat", "blackmail", "dhamki", "धमकी",
                )
            )
        ):
            return CrimeDomain.CHILD_SAFETY
        if intimate_image_abuse:
            return CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY
        # A paid order that was never delivered is a consumer/e-commerce
        # dispute, not an unauthorised-money-loss case.  Keep that route ahead
        # of the broad payment wording below.
        if any(
            marker in text
            for marker in domain_markers[CrimeDomain.ECOMMERCE_FRAUD.value]
        ):
            return CrimeDomain.ECOMMERCE_FRAUD
        # When money has actually gone, the immediate victim workflow is
        # financial fraud even if the lure was a fake officer, health scheme, or
        # another impersonation. The impersonation facts remain in the summary.
        if any(marker in text for marker in LOSS_MARKERS) and any(
            marker in text for marker in ("bank", "account", "upi", "payment", "transfer", "paise", "पैसे")
        ):
            return CrimeDomain.FINANCIAL_FRAUD
        if "account" in text and any(
            marker in text
            for marker in (
                "compromised", "compromise", "hacked", "cannot log in",
                "can't log in", "cant log in", "login nahi", "access nahi",
            )
        ):
            return CrimeDomain.ACCOUNT_COMPROMISE
        # Specific scenarios must otherwise win over broad words such as bank,
        # payment, or money. A KYC link or fake-authority call without loss must
        # retain its own preventive guidance.
        priority_domains = (
            CrimeDomain.ECOMMERCE_FRAUD,
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
            CrimeDomain.CHILD_SAFETY,
            CrimeDomain.CYBERSTALKING,
            CrimeDomain.IMPERSONATION,
            CrimeDomain.ACCOUNT_COMPROMISE,
        )
        for domain in priority_domains:
            if any(marker in text for marker in domain_markers[domain.value]):
                return domain
        if "link" in text and any(
            marker in text
            for marker in (
                "suspicious", "fake", "scam", "kyc", "account block",
                "open kar", "click", "संदिग्ध", "फर्जी", "खोल",
            )
        ):
            return CrimeDomain.PHISHING_SCAM
        if any(marker in text for marker in LOSS_MARKERS):
            return CrimeDomain.FINANCIAL_FRAUD
        if any(marker in text for marker in domain_markers["phishing_scam"]):
            return CrimeDomain.PHISHING_SCAM
        if any(
            marker in text
            for marker in (
                "another cyber issue",
                "other cyber issue",
                "othr cyber isue",
                "dusri cyber problem",
                "anya cyber samasya",
                "अन्य साइबर",
            )
        ):
            return CrimeDomain.OTHER
        scored = {
            CrimeDomain(domain): sum(
                (2 if " " in marker else 1) for marker in markers if marker in text
            )
            for domain, markers in domain_markers.items()
        }
        best_domain, score = max(scored.items(), key=lambda item: item[1])
        return best_domain if score else CrimeDomain.UNKNOWN

    @classmethod
    def extract_entities(cls, message: str) -> list[Entity]:
        entities: list[Entity] = []
        occupied: list[tuple[int, int]] = []

        def add_matches(
            entity_type: EntityType,
            matches: Iterable[re.Match[str]],
            confidence: float,
            normalizer=lambda match: match.group(0),
        ) -> None:
            for match in matches:
                if any(match.start() < end and match.end() > start for start, end in occupied):
                    continue
                value = match.group(0).rstrip(".,)")
                normalized = normalizer(match)
                entities.append(
                    Entity(
                        type=entity_type,
                        value=value,
                        normalized_value=normalized,
                        confidence=confidence,
                        requires_confirmation=entity_type in CRITICAL_TYPES,
                    )
                )
                occupied.append((match.start(), match.end()))

        add_matches(EntityType.URL, URL_PATTERN.finditer(message), 0.98, lambda m: m.group(0).rstrip(".,)"))
        add_matches(EntityType.EMAIL, EMAIL_PATTERN.finditer(message), 0.99, lambda m: m.group(0).casefold())
        add_matches(EntityType.UPI_ID, UPI_PATTERN.finditer(message), 0.98, lambda m: m.group(0).casefold())
        add_matches(EntityType.PHONE_NUMBER, PHONE_PATTERN.finditer(message), 0.97, lambda m: re.sub(r"\D", "", m.group(0))[-10:])
        add_matches(EntityType.TRANSACTION_ID, TRANSACTION_PATTERN.finditer(message), 0.94, lambda m: m.group(1).upper())
        # Parse Indian composite amounts before the single-unit pattern so
        # "2 lakh 30 hazar" is one value (230000), not two ambiguous values.
        add_matches(
            EntityType.AMOUNT,
            COMPOSITE_AMOUNT_PATTERN.finditer(message),
            0.97,
            cls._normalize_composite_amount,
        )
        add_matches(EntityType.AMOUNT, AMOUNT_PATTERN.finditer(message), 0.95, cls._normalize_amount)
        add_matches(EntityType.DATE, DATE_PATTERN.finditer(message), 0.9)
        add_matches(EntityType.TIME, TIME_PATTERN.finditer(message), 0.88)
        add_matches(EntityType.USERNAME, USERNAME_PATTERN.finditer(message), 0.9, lambda m: m.group(0).casefold())

        lowered = message.casefold()
        relative_date: date | None = None
        if not any(entity.type == EntityType.DATE for entity in entities):
            if any(marker in lowered for marker in ("today", "aaj", "आज")):
                relative_date = date.today()
            elif any(marker in lowered for marker in ("yesterday", "kal", "कल")):
                relative_date = date.today() - timedelta(days=1)
            if relative_date is not None:
                cls._add_literal_entity(
                    entities,
                    EntityType.DATE,
                    "today" if relative_date == date.today() else "yesterday",
                    relative_date.isoformat(),
                    0.88,
                )
        if relative_date is not None:
            time_entity = next(
                (entity for entity in entities if entity.type == EntityType.TIME), None
            )
            if time_entity is not None:
                clock = TIME_PATTERN.fullmatch(time_entity.value.strip())
                if clock is not None:
                    time_text = time_entity.value.strip().casefold()
                    hour_text, _, minute_text = time_text.partition(":")
                    hour = int(re.match(r"\d+", hour_text).group(0))
                    minute_match = re.match(r"\d+", minute_text) if minute_text else None
                    minute = int(minute_match.group(0)) if minute_match else 0
                    if "pm" in time_text and hour < 12:
                        hour += 12
                    elif "am" in time_text and hour == 12:
                        hour = 0
                    cls._add_literal_entity(
                        entities,
                        EntityType.DATE_TIME,
                        f"{time_entity.value} {'today' if relative_date == date.today() else 'yesterday'}",
                        f"{relative_date.isoformat()}T{hour:02d}:{minute:02d}:00",
                        0.9,
                    )
        for marker, canonical in PROVIDERS.items():
            if marker in lowered:
                cls._add_literal_entity(entities, EntityType.PROVIDER, marker, canonical, 0.91)
        for platform in PLATFORMS:
            if platform in lowered:
                cls._add_literal_entity(entities, EntityType.SOCIAL_PLATFORM, platform, platform.title(), 0.94)
        for service in ACCOUNT_SERVICES:
            if service in lowered:
                cls._add_literal_entity(entities, EntityType.ACCOUNT_SERVICE, service, service, 0.9)
        for location in LOCATIONS:
            if re.search(rf"\b{re.escape(location)}\b", lowered):
                cls._add_literal_entity(entities, EntityType.LOCATION, location, location.title(), 0.85)
        return entities[:30]

    @staticmethod
    def _add_literal_entity(
        entities: list[Entity], entity_type: EntityType, value: str, normalized: str, confidence: float
    ) -> None:
        if any(entity.type == entity_type and entity.normalized_value == normalized for entity in entities):
            return
        entities.append(
            Entity(
                type=entity_type,
                value=value,
                normalized_value=normalized,
                confidence=confidence,
                requires_confirmation=entity_type in CRITICAL_TYPES,
            )
        )

    @staticmethod
    def _normalize_amount(match: re.Match[str]) -> str:
        raw = match.group("currency_value") or match.group("unit_value")
        unit = (match.group("currency_unit") or match.group("unit") or "").casefold()
        multiplier = {
            "hazaar": Decimal("1000"), "hazar": Decimal("1000"), "thousand": Decimal("1000"),
            "हजार": Decimal("1000"), "lakh": Decimal("100000"), "लाख": Decimal("100000"),
            "crore": Decimal("10000000"), "करोड़": Decimal("10000000"),
        }.get(unit, Decimal("1"))
        try:
            value = Decimal(raw.replace(",", "")) * multiplier
        except InvalidOperation:
            return raw
        return UnderstandingEngine._format_amount(value)

    @staticmethod
    def _normalize_composite_amount(match: re.Match[str]) -> str:
        multipliers = {
            "hazaar": Decimal("1000"), "hazar": Decimal("1000"),
            "thousand": Decimal("1000"), "हजार": Decimal("1000"),
            "lakh": Decimal("100000"), "लाख": Decimal("100000"),
            "crore": Decimal("10000000"), "करोड़": Decimal("10000000"),
        }
        try:
            major = Decimal(match.group("major_value").replace(",", ""))
            minor = Decimal(match.group("minor_value").replace(",", ""))
            value = (
                major * multipliers[match.group("major_unit").casefold()]
                + minor * multipliers[match.group("minor_unit").casefold()]
            )
        except (InvalidOperation, KeyError):
            return match.group(0)
        return UnderstandingEngine._format_amount(value)

    @staticmethod
    def _format_amount(value: Decimal) -> str:
        rendered = format(value, "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered

    @staticmethod
    def format_amount_for_display(normalized: str) -> str:
        """Render a normalized amount with Indian digit grouping."""
        whole, dot, fraction = normalized.partition(".")
        sign = "-" if whole.startswith("-") else ""
        digits = whole.lstrip("-")
        if not digits.isdigit():
            return normalized
        if len(digits) > 3:
            tail = digits[-3:]
            head = digits[:-3]
            groups: list[str] = []
            while head:
                groups.insert(0, head[-2:])
                head = head[:-2]
            digits = ",".join([*groups, tail])
        rendered = f"{sign}{digits}"
        if dot and fraction:
            rendered += f".{fraction}"
        return f"₹{rendered}"

    @staticmethod
    def classify_urgency(text: str, domain: CrimeDomain) -> Urgency:
        if any(marker in text for marker in CRITICAL_MARKERS):
            return Urgency.CRITICAL
        if any(marker in text for marker in HIGH_URGENCY_MARKERS):
            return Urgency.HIGH
        if domain == CrimeDomain.FINANCIAL_FRAUD and any(marker in text for marker in RECENT_MARKERS):
            return Urgency.HIGH
        if domain == CrimeDomain.MISINFORMATION:
            return Urgency.LOW
        if domain != CrimeDomain.UNKNOWN:
            return Urgency.MEDIUM
        return Urgency.LOW

    @staticmethod
    def classify_sentiment(text: str) -> Sentiment:
        if any(marker in text for marker in ("furious", "angry", "gussa", "गुस्सा")):
            return Sentiment.ANGRY
        if any(marker in text for marker in ("scared", "afraid", "fear", "darr", "डर", "threat", "dhamki", "धमकी")):
            return Sentiment.FEARFUL
        if any(marker in text for marker in ("panic", "distressed", "lost money", "i lost", "cut gaye", "kat gaye", "कट गए", "chale gaye", "चले गए", "hack hua", "हैक हुआ", "was hacked", "impersonating")):
            return Sentiment.DISTRESSED
        if any(marker in text for marker in ("confused", "samajh nahi", "समझ नहीं")):
            return Sentiment.CONFUSED
        if any(marker in text for marker in ("worried", "concerned", "suspicious", "संदिग्ध", "help", "madad", "मदद")):
            return Sentiment.CONCERNED
        return Sentiment.NEUTRAL

    @staticmethod
    def score_confidence(
        intent: Intent,
        domain: CrimeDomain,
        language: LanguageCode,
        entities: list[Entity],
    ) -> float:
        score = 0.24
        if intent != Intent.UNKNOWN:
            score += 0.34
        if domain != CrimeDomain.UNKNOWN:
            score += 0.25
        elif intent in {
            Intent.REPORT_INCIDENT,
            Intent.TRACK_REPORT,
            Intent.CHECK_IDENTIFIER,
            Intent.CYBER_WARRIOR,
            Intent.GENERAL_AWARENESS,
            Intent.EXPLORE_CYBER_RISK,
        }:
            score += 0.25
        if entities:
            score += 0.08
        if language != LanguageCode.MIXED:
            score += 0.05
        return min(round(score, 2), 0.96)

    @staticmethod
    def clarification_prompt(
        band: ConfidenceBand,
        intent: Intent,
        domain: CrimeDomain,
        language: LanguageCode,
    ) -> str | None:
        if band == ConfidenceBand.HIGH:
            return None
        if band == ConfidenceBand.MEDIUM:
            if intent == Intent.UNKNOWN:
                key = "intent"
            elif domain == CrimeDomain.UNKNOWN:
                key = "domain"
            else:
                key = "confirm"
        else:
            key = "uncertain"
        prompts = {
            "intent": {
                LanguageCode.EN: "Do you want to report this incident, check an identifier, or get safety guidance?",
                LanguageCode.HI: "क्या आप घटना रिपोर्ट करना, किसी पहचानकर्ता की जांच करना, या सुरक्षा मार्गदर्शन लेना चाहते हैं?",
                LanguageCode.HINGLISH: "Aap incident report karna, identifier check karna, ya safety guidance lena chahte hain?",
            },
            "domain": {
                LanguageCode.EN: "Was this about money, account access, harassment, a suspicious link, or harmful content?",
                LanguageCode.HI: "क्या यह पैसे, अकाउंट एक्सेस, उत्पीड़न, संदिग्ध लिंक या हानिकारक सामग्री से जुड़ा है?",
                LanguageCode.HINGLISH: "Kya ye money, account access, harassment, suspicious link, ya harmful content se related hai?",
            },
            "confirm": {
                LanguageCode.EN: "Please confirm the main incident type before continuing.",
                LanguageCode.HI: "आगे बढ़ने से पहले मुख्य घटना प्रकार की पुष्टि करें।",
                LanguageCode.HINGLISH: "Continue karne se pehle main incident type confirm karein.",
            },
            "uncertain": {
                LanguageCode.EN: "I am not fully certain what happened. What happened, and what help do you need?",
                LanguageCode.HI: "मुझे अभी पूरी तरह स्पष्ट नहीं है कि क्या हुआ। क्या हुआ था और आपको किस मदद की जरूरत है?",
                LanguageCode.HINGLISH: "Mujhe abhi fully clear nahi hai. Kya hua tha aur aapko kis help ki zarurat hai?",
            },
        }
        localized = prompts[key]
        return localized.get(language, localized[LanguageCode.EN])
