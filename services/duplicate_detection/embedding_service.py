from functools import lru_cache

from services.duplicate_detection.constants import EMBEDDING_MODEL_NAME
from services.duplicate_detection.exceptions import EmbeddingUnavailableError
from services.duplicate_detection.normalizers import normalize_description


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingUnavailableError("sentence-transformers is not installed") from exc

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


class EmbeddingService:
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name

    def encode(self, text: str) -> list[float]:
        model = get_embedding_model()
        normalized = normalize_description(text)
        embedding = model.encode(normalized, normalize_embeddings=True)

        return embedding.tolist()


def generate_embedding(description: str) -> list[float]:
    return EmbeddingService().encode(description)
