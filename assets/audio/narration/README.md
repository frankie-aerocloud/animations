# Local narration files

Place a locally recorded mono or stereo WAV here. To use a complete 90-second recording, set `audio.narration_wav` in the project YAML to `../../assets/audio/narration/your-recording.wav`. Include its speaker consent and licence/source details in the project asset manifest. The render pipeline resamples, pads or trims the WAV to the configured project duration.

On macOS, the pipeline can also try the built-in `say` voice configured as `audio.tts_voice`; no network TTS service is used. If the system voice produces no audio on your installation, provide the WAV instead.
