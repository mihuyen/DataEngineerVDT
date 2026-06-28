"""
topic_model/push_to_hub.py — Upload topic model lên HuggingFace Hub.

Input:  ./checkpoints/topic/best_model/
Output: Model đã upload tại HF_TOPIC_MODEL_REPO.
"""

import logging

from nlp.topic_model.distill import push_to_hub

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    push_to_hub()
