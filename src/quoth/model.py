from abc import ABC, abstractmethod

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from torch import Tensor
from transformers import AutoModel, AutoProcessor
from transformers.modeling_utils import PreTrainedModel
from transformers.models.siglip.configuration_siglip import SiglipConfig
from transformers.models.siglip.modeling_siglip import SiglipModel
from transformers.models.siglip.processing_siglip import SiglipProcessor
from transformers.processing_utils import ProcessorMixin


class QuothModel(ABC):
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embeddings."""
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Return the embedding for the given text."""
        raise NotImplementedError

    @abstractmethod
    def embed_image(self, image_url: str) -> np.ndarray:
        """Return the embedding for the given image."""
        raise NotImplementedError


class SentenceTransformerModel(QuothModel):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def get_embedding_dimension(self) -> int:
        dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None:
            raise ValueError("Undefined embedding dimension")
        return dimension

    def embed_text(self, text: str) -> np.ndarray:
        return self.model.encode(text, convert_to_numpy=True)

    def embed_image(self, image_url: str) -> np.ndarray:
        raise NotImplementedError


class SiglipModel(QuothModel):  # type: ignore[no-redef]
    def __init__(self, model_name: str):
        self.processor: SiglipProcessor = AutoProcessor.from_pretrained(model_name)
        self.model: SiglipModel = AutoModel.from_pretrained(model_name)
        self.config: SiglipConfig = self.model.config

    def get_embedding_dimension(self) -> int:
        text_dimension = self.model.config.text_config.hidden_size
        image_dimension = self.model.config.vision_config.hidden_size
        if text_dimension != image_dimension:
            raise ValueError(f"{text_dimension=} != {image_dimension=}")
        return text_dimension

    def embed_text(self, text: str) -> np.ndarray:
        inputs = self.processor(text, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).numpy()

    def embed_image(self, image_url: str) -> np.ndarray:
        raise NotImplementedError
