from core.constants.languages import DEFAULT_RESPONSE_LANGUAGE, SUPPORTED_RESPONSE_LANGUAGES


MESSAGES = {
    "LOGIN_SUCCESSFUL": {
        "en": "Login successful.",
        "bn": "লগইন সফল হয়েছে।",
    },
    "TOKEN_REFRESHED": {
        "en": "Token refreshed successfully.",
        "bn": "টোকেন সফলভাবে রিফ্রেশ হয়েছে।",
    },
    "LOGOUT_SUCCESSFUL": {
        "en": "Logout successful.",
        "bn": "লগআউট সফল হয়েছে।",
    },
    "PROFILE_RETRIEVED": {
        "en": "Profile retrieved successfully.",
        "bn": "প্রোফাইল সফলভাবে পাওয়া গেছে।",
    },
    "REPORT_CREATED": {
        "en": "Report submitted successfully.",
        "bn": "রিপোর্টটি সফলভাবে জমা হয়েছে।",
    },
    "REPORT_CREATED_WITH_DUPLICATE_MATCH": {
        "en": "Report submitted successfully. A similar report was detected.",
        "bn": "রিপোর্টটি সফলভাবে জমা হয়েছে। একটি অনুরূপ রিপোর্ট শনাক্ত হয়েছে।",
    },
    "REPORTS_RETRIEVED": {
        "en": "{count} reports retrieved successfully.",
        "bn": "{count}টি রিপোর্ট সফলভাবে পাওয়া গেছে।",
    },
    "REPORT_RETRIEVED": {
        "en": "Report retrieved successfully.",
        "bn": "রিপোর্ট সফলভাবে পাওয়া গেছে।",
    },
    "REPORT_NOT_FOUND": {
        "en": "Report '{report_id}' was not found.",
        "bn": "রিপোর্ট '{report_id}' পাওয়া যায়নি।",
    },
    "REPORT_STATUS_UPDATED": {
        "en": "Report status changed from '{previous_status}' to '{current_status}'.",
        "bn": "রিপোর্টের স্ট্যাটাস '{previous_status}' থেকে '{current_status}' করা হয়েছে।",
    },
    "REPORT_BULK_STATUS_UPDATED": {
        "en": "{updated_count} reports updated successfully.",
        "bn": "{updated_count}টি রিপোর্ট সফলভাবে আপডেট হয়েছে।",
    },
    "REPORT_DELETED": {
        "en": "Report deleted successfully.",
        "bn": "রিপোর্ট সফলভাবে মুছে ফেলা হয়েছে।",
    },
    "REPORT_ASSIGNED": {
        "en": "Report assigned successfully.",
        "bn": "রিপোর্ট সফলভাবে অ্যাসাইন করা হয়েছে।",
    },
    "REPORT_ESCALATED": {
        "en": "Report escalated successfully.",
        "bn": "রিপোর্ট সফলভাবে এস্কেলেট করা হয়েছে।",
    },
    "RELATED_REPORTS_RETRIEVED": {
        "en": "{count} related reports retrieved successfully.",
        "bn": "{count}টি সম্পর্কিত রিপোর্ট সফলভাবে পাওয়া গেছে।",
    },
    "DUPLICATE_REPORTS_RETRIEVED": {
        "en": "{count} duplicate reports retrieved successfully.",
        "bn": "{count}টি ডুপ্লিকেট রিপোর্ট সফলভাবে পাওয়া গেছে।",
    },
    "REPORT_TIMELINE_RETRIEVED": {
        "en": "Report timeline retrieved successfully.",
        "bn": "রিপোর্ট টাইমলাইন সফলভাবে পাওয়া গেছে।",
    },
    "REPORT_STATS_RETRIEVED": {
        "en": "Report statistics retrieved successfully.",
        "bn": "রিপোর্ট পরিসংখ্যান সফলভাবে পাওয়া গেছে।",
    },
    "VALIDATION_ERROR": {
        "en": "The request contains invalid fields.",
        "bn": "অনুরোধে কিছু ভুল তথ্য রয়েছে।",
    },
    "INVALID_CREDENTIALS": {
        "en": "Invalid email or password.",
        "bn": "ইমেইল অথবা পাসওয়ার্ড সঠিক নয়।",
    },
    "AUTHENTICATION_REQUIRED": {
        "en": "Authentication credentials were not provided.",
        "bn": "অথেনটিকেশন তথ্য দেওয়া হয়নি।",
    },
    "PERMISSION_DENIED": {
        "en": "You do not have permission to perform this action.",
        "bn": "এই কাজটি করার অনুমতি আপনার নেই।",
    },
    "INVALID_STATUS_TRANSITION": {
        "en": "Report status cannot be changed from '{previous_status}' to '{current_status}'.",
        "bn": "রিপোর্টের স্ট্যাটাস '{previous_status}' থেকে '{current_status}' করা যাবে না।",
    },
    "AI_PROCESSING_FAILED": {
        "en": "AI processing failed. The report needs manual review.",
        "bn": "AI প্রসেসিং ব্যর্থ হয়েছে। রিপোর্টটি ম্যানুয়াল রিভিউ প্রয়োজন।",
    },
    "INTERNAL_SERVER_ERROR": {
        "en": "An unexpected server error occurred.",
        "bn": "সার্ভারে একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।",
    },
}


def get_message(code: str, language: str = DEFAULT_RESPONSE_LANGUAGE, **kwargs) -> str:
    translations = MESSAGES.get(code)
    if not translations:
        return "Unknown message."

    resolved_language = language if language in SUPPORTED_RESPONSE_LANGUAGES else DEFAULT_RESPONSE_LANGUAGE
    template = translations.get(resolved_language) or translations.get(DEFAULT_RESPONSE_LANGUAGE)

    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template
