# Live voice preview

This prototype streams microphone audio to Gladia, displays partial transcripts,
and groups final utterances into researcher turns. Each completed turn is printed
as a formatted message. Nothing is sent to H; there is no model reply or
conversation history. Only speak content you are comfortable sending to Gladia.

On Debian or Ubuntu, install PortAudio if it is missing:

```sh
sudo apt install libportaudio2
```

Set `GLADIA_API_KEY` in your local `.env`, ensure your microphone is available
and permitted, and run:

```sh
uv sync
uv run --env-file .env python -m jesse.voice.live
```

By default, the preview waits 1.5 seconds after the last speech event or transcript
update, and for all observed partial utterances to become final. Processing and
network delays add latency. A pause longer than the threshold can still split a
thought; background noise or delayed speech events can affect turn detection.
Change the threshold when running the preview:

```sh
uv run --env-file .env python -m jesse.voice.live --silence-seconds 2.5
```

Press Ctrl+C to stop listening; the preview waits for remaining final transcripts
before closing. Gladia automatically detects the language using its default
configuration. Live sessions are billed by Gladia and require internet access.

For integration, `run_live_preview` accepts `on_turn(transcript)` and
`on_partial(text)` callbacks. The finalized turn callback receives the raw
transcript on the capture thread; consumers should enqueue work rather than block
microphone capture. `build_spoken_request` formats a transcript for H. The
prototype has not yet been connected to an H session.
