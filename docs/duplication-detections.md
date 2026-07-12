Duplicate Detection Implementation Guide
1. Purpose
The duplicate-detection service determines whether a newly submitted report describes the same real-world event as one or more existing reports.
The service must remain deterministic:
Sentence Transformer generates semantic embeddings.
Cosine similarity measures description similarity.
Location, category, and time proximity apply deterministic constraints.
The backend calculates the final duplicate score.
Every submitted report is stored independently.
Duplicate reports are never merged, dropped, or overwritten.
Duplicate detection only adds metadata such as:
possible_duplicate
matched_report_id
similarity_score
duplicate_count
duplicate_group_key

It may also influence report priority, but it must not modify the original report content.

2. Core Architecture
New Report
    ↓
Text Normalization
    ↓
Sentence Transformer Embedding
    ↓
Candidate Selection
    ↓
Cosine Similarity Search
    ↓
Location Validation
    ↓
Category and Time Comparison
    ↓
Final Duplicate Score
    ↓
Threshold Decision
    ↓
Store Report with Duplicate Metadata

Recommended service structure:
services/
└── duplicate_detection/
    ├── constants.py
    ├── normalizers.py
    ├── embedding_service.py
    ├── candidate_service.py
    ├── similarity_service.py
    ├── duplicate_service.py
    ├── scoring.py
    ├── selectors.py
    └── exceptions.py

File responsibilities
File
Responsibility
constants.py
Model name, thresholds, weights, and limits
normalizers.py
Description and location normalization
embedding_service.py
Sentence Transformer loading and embedding generation
candidate_service.py
Select likely matching reports before detailed scoring
similarity_service.py
Description and location similarity calculation
scoring.py
Final hybrid duplicate-score calculation
selectors.py
Select the best matching report and related report group
duplicate_service.py
Orchestrate the complete duplicate-detection workflow
exceptions.py
Duplicate-detection-specific exceptions


3. Recommended Technology
Use:
sentence-transformers
PostgreSQL
pgvector
Django ORM

Suggested Sentence Transformer model:
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

A multilingual model is important because reports may contain:
Bangla
English
Mixed Bangla-English text
The model converts semantically similar reports into nearby vectors even when wording differs.
Example:
"A shop is burning and people may be trapped."

"দোকানে আগুন লেগেছে এবং ভিতরে মানুষ আটকা পড়েছে।"

These reports should produce relatively similar embeddings despite being written in different languages.

4. Database Fields
The existing report model should include duplicate-related fields.
class Report(models.Model):
    description = models.TextField()
    location = models.CharField(max_length=500)
    normalized_location = models.CharField(
        max_length=500,
        blank=True,
        db_index=True,
    )

    category = models.CharField(
        max_length=50,
        db_index=True,
    )

    description_embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
    )

    possible_duplicate = models.BooleanField(
        default=False,
        db_index=True,
    )

    matched_report = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="matched_duplicates",
    )

    similarity_score = models.FloatField(
        null=True,
        blank=True,
    )

    duplicate_count = models.PositiveIntegerField(
        default=0,
    )

    duplicate_group_key = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

Field meanings
Field
Meaning
description_embedding
Semantic representation of the report description
possible_duplicate
Whether a similar report was detected
matched_report
Best matching existing report
similarity_score
Final deterministic duplicate score
duplicate_count
Number of reports identified in the same duplicate group
duplicate_group_key
Stable identifier used to group related reports

duplicate_group_key is optional but useful for:
related-report retrieval
bulk status updates
duplicate counting
duplicate-based ranking

5. Text Normalization
Normalization should occur before embedding generation.
Description normalization
Recommended operations:
Trim leading and trailing spaces.
Collapse repeated whitespace.
Normalize Unicode.
Convert repeated punctuation.
Remove invisible characters.
Preserve meaningful words.
Do not aggressively remove stop words.
Do not translate the report before embedding.
Example:
import re
import unicodedata


def normalize_description(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()

    return normalized

Do not lowercase Bangla-specific text manually unless the normalization library safely supports it. Sentence Transformer models generally handle case and multilingual text appropriately.

6. Location Normalization
Location must be treated as a major duplicate constraint.
Two reports with semantically identical descriptions but different locations should usually remain separate reports.
Example:
"Transformer is burning in Uttara."
"Transformer is burning in Dhanmondi."

The descriptions are nearly identical, but they represent different incidents.
Recommended location normalization:
def normalize_location(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s,-]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value

Optional improvements:
Normalize common abbreviations.
Convert Bangla and English location variants into a canonical form.
Use a geocoding API to store latitude and longitude.
Use geographic distance when coordinates are available.
Example:
Sylhet Bondor Bazar
Bondor Bazar, Sylhet
Sylhet Bandar Bazaar

These may require fuzzy matching or geocoding rather than exact text comparison.

7. Embedding Service
The model should be loaded once when the application process starts.
Do not reload the model for every request.
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> list[float]:
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()

Using normalized embeddings allows cosine similarity to be calculated efficiently.
Important configuration
EMBEDDING_MODEL = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

EMBEDDING_DIMENSIONS = 384


8. Candidate Selection
Do not compare every new report against every historical report in Python.
First select a small set of likely candidates.
Recommended candidate conditions:
Created within the last 24–72 hours
AND
same or related category
AND
same or similar normalized location

Example:
from datetime import timedelta

from django.utils import timezone


def get_candidate_reports(
    *,
    category: str,
    created_within_hours: int = 72,
):
    minimum_time = timezone.now() - timedelta(
        hours=created_within_hours
    )

    return Report.objects.filter(
        created_at__gte=minimum_time,
        category=category,
        description_embedding__isnull=False,
    )

Category should not always be a hard requirement because AI classification may occasionally differ.
A safer candidate strategy:
Primary candidates:
same category + recent reports

Secondary candidates:
nearby location + recent reports

Fallback candidates:
recent reports with high vector similarity


9. Cosine Similarity Search with pgvector
When using normalized embeddings, cosine distance can be queried directly in PostgreSQL.
Conceptually:
from pgvector.django import CosineDistance


candidates = (
    Report.objects
    .filter(created_at__gte=minimum_time)
    .annotate(
        description_distance=CosineDistance(
            "description_embedding",
            new_embedding,
        )
    )
    .order_by("description_distance")[:20]
)

Convert distance to similarity:
description_similarity = 1 - description_distance

Example:
Cosine distance:   0.09
Cosine similarity: 0.91

Only retrieve the top candidates rather than loading all reports into application memory.

10. Similarity Components
The final decision should use multiple deterministic signals.
Description similarity
Calculated using Sentence Transformer embeddings:
0.00 = completely unrelated
1.00 = nearly identical meaning

Location similarity
Possible methods:
Exact normalized-location match
Fuzzy string similarity
Geographic distance
Landmark overlap
City/area matching
Example normalized location score:
Exact match                    → 1.00
Very close fuzzy match         → 0.85–0.99
Same area but different detail → 0.60–0.84
Different location             → 0.00

Category match
Same category       → 1.00
Related category    → 0.50
Different category  → 0.00

Related categories may include:
fire ↔ infrastructure
flood ↔ public_service
accident ↔ medical
crime ↔ public_service

Use related-category rules only when justified.
Temporal proximity
Reports submitted close together are more likely to describe the same incident.
Example:
Within 1 hour      → 1.00
Within 6 hours     → 0.90
Within 24 hours    → 0.70
Within 72 hours    → 0.40
Older than 72h     → 0.00


11. Hybrid Duplicate Score
Recommended formula:
final_duplicate_score =
    0.55 × description_similarity
  + 0.30 × location_similarity
  + 0.10 × category_similarity
  + 0.05 × temporal_similarity

Example:
Description similarity: 0.91
Location similarity:    0.88
Category similarity:    1.00
Temporal similarity:    0.90

Calculation:
0.55 × 0.91 = 0.5005
0.30 × 0.88 = 0.2640
0.10 × 1.00 = 0.1000
0.05 × 0.90 = 0.0450

Final score = 0.9095

The report is highly likely to be a duplicate.

12. Location Safety Gate
The final score alone should not determine duplication.
Use a hard location requirement:
If location similarity is below the minimum threshold:
    treat as a new independent report

Recommended:
MIN_LOCATION_SIMILARITY = 0.60

Decision logic:
is_duplicate = (
    location_similarity >= MIN_LOCATION_SIMILARITY
    and final_score >= DUPLICATE_THRESHOLD
)

This prevents identical incidents in different areas from being grouped incorrectly.

13. Threshold Strategy
Recommended initial thresholds:
POSSIBLE_DUPLICATE_THRESHOLD = 0.78
STRONG_DUPLICATE_THRESHOLD = 0.86
MIN_DESCRIPTION_SIMILARITY = 0.72
MIN_LOCATION_SIMILARITY = 0.60

Possible interpretation:
Score
Result
< 0.70
Not duplicate
0.70–0.77
Weak similarity; do not mark automatically
0.78–0.85
Possible duplicate
>= 0.86
Strong duplicate match

Thresholds should be stored in configuration, not hardcoded throughout the service.
DUPLICATE_THRESHOLD=0.78
STRONG_DUPLICATE_THRESHOLD=0.86
DUPLICATE_WINDOW_HOURS=72


14. Duplicate Detection Result Contract
The internal service should return a structured result:
from dataclasses import dataclass
from uuid import UUID


@dataclass
class DuplicateDetectionResult:
    possible_duplicate: bool
    matched_report_id: UUID | None
    final_score: float | None
    description_similarity: float | None
    location_similarity: float | None
    category_similarity: float | None
    temporal_similarity: float | None
    duplicate_group_key: UUID | None
    duplicate_count: int

Example result:
{
  "possibleDuplicate": true,
  "matchedReportId": "d087e410-6a34-4dd8-b426-b205218e99cd",
  "finalScore": 0.91,
  "descriptionSimilarity": 0.92,
  "locationSimilarity": 0.89,
  "categorySimilarity": 1.0,
  "temporalSimilarity": 0.93,
  "duplicateGroupKey": "36f8f8a6-cd5f-4e88-8755-df9fef660fa1",
  "duplicateCount": 4
}


15. Duplicate Grouping Logic
When no duplicate is found:
Generate a new duplicate_group_key
duplicate_count = 0
matched_report = null
possible_duplicate = false

When a duplicate is found:
Reuse the matched report's duplicate_group_key
Set matched_report to the best candidate
possible_duplicate = true
Recalculate duplicate count for the group

If the matched report has no group key yet:
Create a new group key
Assign it to both the existing report and the new report

Conceptual flow:
if result.possible_duplicate:
    group_key = (
        matched_report.duplicate_group_key
        or uuid.uuid4()
    )

    if matched_report.duplicate_group_key is None:
        matched_report.duplicate_group_key = group_key
        matched_report.save(
            update_fields=["duplicate_group_key"]
        )
else:
    group_key = uuid.uuid4()

Every report remains an independent database row.

16. Duplicate Count Calculation
duplicate_count should represent the number of other reports in the same group.
Example:
Group contains 1 report:
duplicate_count = 0

Group contains 4 reports:
each report may expose duplicate_count = 3

Recommended source-of-truth approach:
group_size = Report.objects.filter(
    duplicate_group_key=group_key
).count()

duplicate_count = max(group_size - 1, 0)

Avoid relying entirely on manually incremented counters unless concurrency is handled carefully.
For performance, a cached count may be maintained, but the group query remains the authoritative source.

17. Concurrency Handling
Two similar reports may arrive at the same time.
Potential issue:
Request A finds no duplicate.
Request B also finds no duplicate.
Both create separate groups.

Possible mitigations:
Simple hackathon approach
Save reports normally.
Run a post-save reconciliation check.
If another similar report was created within the same second, regroup both.
Stronger approach
Use a database transaction and advisory lock based on:
normalized location + category + time bucket

Conceptually:
Lock candidate group
→ run duplicate search
→ assign group
→ save report
→ release lock

For the hackathon, transaction-based consistency is enough unless very high request concurrency is expected.

18. Priority Integration
Duplicate detection should provide a capped bonus to the report ranking.
Example:
priority_score =
    urgency_score
  + confidence_bonus
  + duplicate_bonus
  + recency_bonus

Recommended duplicate bonus:
import math


def calculate_duplicate_bonus(
    duplicate_count: int,
) -> float:
    return min(
        math.log2(duplicate_count + 1) * 5,
        15,
    )

This produces controlled growth:
Duplicate count
Approximate bonus
0
0
1
5
3
10
7
15
20
capped at 15

The cap prevents frequently reported low-risk complaints from automatically outranking critical emergencies.

19. Bulk Status Update Support
Reports in the same duplicate group can be updated together.
The duplicate service should expose a helper:
def get_related_report_ids(
    duplicate_group_key,
) -> list:
    return list(
        Report.objects.filter(
            duplicate_group_key=duplicate_group_key
        ).values_list("id", flat=True)
    )

Bulk status logic can then:
Select duplicate group
→ validate requested status
→ update all selected reports atomically
→ create timeline/audit records

This removes the need for managers to update each related report individually.

20. Duplicate Service Orchestration
Conceptual implementation:
class DuplicateDetectionService:
    def __init__(
        self,
        *,
        embedding_service,
        candidate_service,
        similarity_service,
    ):
        self.embedding_service = embedding_service
        self.candidate_service = candidate_service
        self.similarity_service = similarity_service

    def detect(
        self,
        *,
        description: str,
        location: str,
        category: str,
    ) -> DuplicateDetectionResult:
        normalized_description = normalize_description(
            description
        )
        normalized_location = normalize_location(
            location
        )

        embedding = self.embedding_service.encode(
            normalized_description
        )

        candidates = self.candidate_service.find(
            embedding=embedding,
            category=category,
            location=normalized_location,
        )

        best_match = None

        for candidate in candidates:
            score = self.similarity_service.calculate(
                new_description_embedding=embedding,
                new_location=normalized_location,
                new_category=category,
                candidate=candidate,
            )

            if (
                best_match is None
                or score.final_score
                > best_match.final_score
            ):
                best_match = score

        return build_detection_result(best_match)

The service should not:
write HTTP responses
perform authentication
update report statuses
calculate final API response messages
call the LLM
modify existing report descriptions

21. Failure Handling
Sentence Transformer failure should not block report submission unnecessarily.
Possible fallback:
Embedding unavailable
→ use normalized text similarity
→ use location + category + time comparison
→ mark detection method as fallback

Recommended internal metadata:
duplicate_detection_method:
- embedding
- hybrid
- keyword_fallback
- unavailable

Example fallback score:
0.50 × fuzzy description match
+ 0.35 × location similarity
+ 0.10 × category match
+ 0.05 × time proximity

If duplicate detection completely fails:
possible_duplicate = false
matched_report_id = null
similarity_score = null
duplicate_detection_status = failed

The report should still be stored.

22. Logging
Log:
Request/report identifier
Number of candidates evaluated
Best candidate ID
Description similarity
Location similarity
Final score
Duplicate decision
Processing duration
Detection method
Avoid logging:
Full contact information
Sensitive raw report descriptions
Embedding vectors
Authentication data

23. Testing Strategy
Unit tests
Test:
Exact duplicate description
Semantically similar wording
Bangla-English semantic match
Same description but different location
Same location but unrelated issue
Same event with slightly different category
Old report outside the time window
Threshold boundary values
No candidate reports
Embedding-service failure
Duplicate-group creation
Existing group reuse
Duplicate-count calculation
Example test cases
Same event
Report A:
"Fire near Bondor Bazar shop, people trapped."

Report B:
"Bondor Bazar-er dokaner pashe agun, vitore manush atka."

Expected:
possible_duplicate = true

Same description, different location
Report A:
"Electric pole caught fire in Uttara."

Report B:
"Electric pole caught fire in Dhanmondi."

Expected:
possible_duplicate = false

Similar location, different issue
Report A:
"Road is flooded near Bondor Bazar."

Report B:
"A person was injured in an accident near Bondor Bazar."

Expected:
possible_duplicate = false


24. Final Responsibility Boundary
Sentence Transformer:
- Generate semantic embeddings

PostgreSQL + pgvector:
- Store vectors
- Retrieve nearest candidates

Duplicate Detection Service:
- Normalize input
- Calculate deterministic similarities
- Apply thresholds
- Select best match
- Assign duplicate group metadata

Priority Service:
- Apply capped duplicate bonus

Report Service:
- Persist every report independently
- Return duplicate metadata

Management Logic:
- Perform bulk status updates for related reports

The duplicate-detection layer must identify semantic overlap without changing the identity or original content of any submitted report. Every report remains independently stored, while duplicate metadata improves ranking, grouping, and operational management.

