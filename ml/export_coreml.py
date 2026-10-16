"""
VĀSTU CoreML Converter & Model Exporter
Converts VastuMobileDepthNet to Apple CoreML (.mlpackage) format for low-power, high-FPS inference on iPhone Neural Engine (ANE).
"""

import sys
import os

try:
    import torch
    import coremltools as ct
    from ml.models.mobile_depth_net import VastuMobileDepthNet
    HAS_CONVERTER = True
except ImportError as e:
    print(f"CoreML converter warning: missing dependency ({e})")
    HAS_CONVERTER = False

def export_model_to_coreml(output_path: str = "ios/VastuSpatial/Models/VastuMobileDepth.mlpackage"):
    if not HAS_CONVERTER:
        print("PyTorch or CoreMLTools not installed in environment. Skipping export execution.")
        return False
        
    print("Initializing VastuMobileDepthNet PyTorch model...")
    model = VastuMobileDepthNet()
    model.eval()

    # Trace model with example RGB frame input (1, 3, 256, 256)
    example_input = torch.rand(1, 3, 256, 256)
    traced_model = torch.jit.trace(model, example_input)

    print("Converting PyTorch trace to CoreML Neural Engine format...")
    coreml_model = ct.convert(
        traced_model,
        inputs=[
            ct.ImageType(
                name="colorImage",
                shape=(1, 3, 256, 256),
                scale=1.0 / 255.0,
                bias=[0, 0, 0],
                color_layout=ct.colorlayout.RGB
            )
        ],
        outputs=[
            ct.TensorType(name="depthMap"),
            ct.TensorType(name="semanticLogits"),
            ct.TensorType(name="qualityMetrics")
        ],
        minimum_deployment_target=ct.target.iOS17
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    coreml_model.save(output_path)
    print(f"Successfully exported CoreML model package to: {output_path}")
    return True

if __name__ == "__main__":
    export_model_to_coreml()
