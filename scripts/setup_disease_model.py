#!/usr/bin/env python
"""
Optional: train or place a Keras plant-disease model for local inference.

Without a model file, disease detection uses:
  1. Gemini Vision (if GEMINI_API_KEY is set) — recommended
  2. Color-heuristic fallback

To use TensorFlow locally:
  pip install tensorflow
  Place your trained model at: agro/ml/models/plant_disease_mobilenet.keras
  Or set DISEASE_MODEL_PATH in .env

Train on PlantVillage or your dataset, export with:
  model.save('agro/ml/models/plant_disease_mobilenet.keras')
"""
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / 'agro' / 'ml' / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)
target = MODEL_DIR / 'plant_disease_mobilenet.keras'

print('AgroSathi disease model setup')
print('Target path:', target)
print()
print('Recommended: set GEMINI_API_KEY in .env for real AI vision analysis.')
print('Optional: copy a .keras model to the path above and pip install tensorflow.')
