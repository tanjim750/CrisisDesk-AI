from functools import lru_cache

from core.constants.duplicate_detection import EMBEDDING_MODEL_NAME
from services.duplicate_detection.normalizers import normalize_description


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("sentence-transformers is not installed") from exc

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def generate_embedding(description: str) -> list[float]:
    model = get_embedding_model()
    normalized = normalize_description(description)
    embedding = model.encode(normalized, normalize_embeddings=True)

    return embedding.tolist()
