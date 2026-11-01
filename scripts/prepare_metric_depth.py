"""Cache and validate the real metric model while building the worker image."""
import argparse
from pathlib import Path
import numpy as np
import torch
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from ml.depth.model_config import METRIC_DEPTH_MODEL_ID, METRIC_DEPTH_MODEL_REVISION


def prepare(output):
    torch.set_num_threads(1)
    processor = AutoImageProcessor.from_pretrained(METRIC_DEPTH_MODEL_ID, revision=METRIC_DEPTH_MODEL_REVISION)
    model = AutoModelForDepthEstimation.from_pretrained(METRIC_DEPTH_MODEL_ID, revision=METRIC_DEPTH_MODEL_REVISION, use_safetensors=True)
    if getattr(model.config, 'depth_estimation_type', None) != 'metric':
        raise RuntimeError('METRIC_DEPTH_MODEL_INVALID: relative depth models cannot replace metric depth')
    model.eval()
    with torch.inference_mode():
        prediction = model(**processor(images=np.zeros((64, 64, 3), dtype=np.uint8), return_tensors='pt')).predicted_depth
    if not torch.isfinite(prediction).all().item() or not (prediction > 0).all().item():
        raise RuntimeError('METRIC_DEPTH_MODEL_INVALID: inference produced nonpositive or nonfinite depth')
    Path(output).mkdir(parents=True, exist_ok=True)
    processor.save_pretrained(output)
    model.save_pretrained(output, safe_serialization=True)
    # Validate the same local-only loading contract used at runtime.
    AutoImageProcessor.from_pretrained(output, local_files_only=True)
    AutoModelForDepthEstimation.from_pretrained(output, local_files_only=True, use_safetensors=True)
    print(f'Metric depth model cached and inference verified: {METRIC_DEPTH_MODEL_ID}@{METRIC_DEPTH_MODEL_REVISION}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    prepare(parser.parse_args().output)
