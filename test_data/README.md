# VĀSTU Test Dataset — Indoor Spatial Reconstruction Sample
**Competition:** Techfest IIT Bombay 2026 — Round 1  
**Directory:** `test_data/`

This test directory contains pre-validated sample indoor smartphone capture video for testing the VĀSTU 3D reconstruction pipeline.

## Sample Assets
* **`sample_indoor_scan.mp4`** (2.8 MB): A pre-filtered 720p 30fps indoor spatial sequence adhering to the VĀSTU SOP (smooth translation, continuous visual overlap, low motion blur).

## How to Run Reconstruction on this Sample:
From the repository root:

```bash
# 1. Activate your Python environment (or use docker)
python -m venv venv && source venv/bin/activate
pip install -r backend/workers/requirements.txt

# 2. Execute the reconstruction CLI
python scripts/reconstruct.py --video test_data/sample_indoor_scan.mp4 --output digital_twin_output --deploy

# 3. View the generated 3D twin in your browser
# Open digital_twin_output/index.html directly or browse to http://localhost:3000/output
```

