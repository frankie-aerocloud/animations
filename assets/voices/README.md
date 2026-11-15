# Piper voices

Voice models are downloaded locally (no account needed) and are not committed.

| Voice | Dataset licence | Model card | Retrieved | SHA-256 (onnx) |
|---|---|---|---|---|
| `en_GB-cori-high` | Public domain (LibriVox recordings, see model card) | https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_GB/cori/high/MODEL_CARD | 2026-11-12 | `470b4dd634c98f8a4850d7626ffc3dfc90774628eeef6605a6dd8f88f30a5903` |

Download with:

```sh
.venv/bin/python -m piper.download_voices en_GB-cori-high --download-dir assets/voices
```

Piper itself (`piper-tts` 1.8.0) is GPL-3.0-or-later; `onnxruntime` is MIT.
