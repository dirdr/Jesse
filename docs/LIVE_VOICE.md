# Live voice preview

This prototype streams microphone audio to Gladia, displays partial transcripts,
and groups final utterances into researcher turns. Each completed turn is printed
as a formatted message. Nothing is sent to H; there is no model reply or
conversation history. Only speak content you are comfortable sending to Gladia.

To preview an enriched request for the future computer-use agent without
restricting it to the current catalogue, set `OPENAI_API_KEY` (or `OPENAI_KEY`)
and run:

```sh
uv run --env-file .env python -m jesse.voice.live --prepare
```

Each final turn is sent to OpenAI and printed alongside the original transcript
with an objective, supplied and missing information, a suggested approach, and
limitations. This is a model-generated preview: it does not verify tool
availability, execute experiments, start H, or retain conversation history.
Use it only with information you are comfortable sending to OpenAI. Preparation
uses the same bounded background queue described below.

To pass each completed turn to the existing OpenAI/Pydantic AI catalogue
selector, set `OPENAI_API_KEY` (or `OPENAI_KEY`) and `HAI_API_KEY` in `.env`
and run:

```sh
uv run --env-file .env python -m jesse.voice.live --plan
```

Each turn starts a **separate plan-only investigation**: the transcript is sent
to OpenAI for protocol selection and the selected or blocked result is printed
and saved under `runs/`. The selector checks execution-surface availability,
including H credentials, even though no H session is started in this mode.
Spoken corrections are not yet applied to an active investigation. Planning is
queued separately from microphone capture; up to four turns can wait while one
is being planned. If the queue is full, the preview stops with an explicit
error. Stopping the preview waits for queued plans to finish. `--surface` and
`--planner-model` select the same surface preference and OpenAI model as the
text runner.

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
The session stays open without a fixed turn-duration limit. Partial transcripts
are never submitted to the planner; if Gladia keeps detecting background speech
or does not finalize an utterance, automatic completion can be delayed.
Change the threshold when running the preview:

```sh
uv run --env-file .env python -m jesse.voice.live --silence-seconds 2.5
```

Press Ctrl+C to stop listening; the preview waits for remaining final transcripts
before closing. Gladia automatically detects the language using its default
configuration. Live sessions are billed by Gladia and require internet access.

If partial transcripts continue while nobody is speaking, check for background
speech, audio playing through speakers, or an unintended input source. Gladia
may detect those sounds as speech, preventing the silence timer from expiring.
List available inputs and select a microphone (not a monitor/output source):

```sh
uv run python -m jesse.voice.live --list-inputs
uv run --env-file .env python -m jesse.voice.live --plan --input-device INDEX
```

Replace `INDEX` with the listed microphone index; indices can change when devices
are connected. Check the system input meter and test the microphone in another
recording application if recognition remains poor.

For integration, `run_live_preview` accepts `on_turn(transcript)` and
`on_partial(text)` callbacks. The finalized turn callback receives the raw
transcript on the capture thread; consumers should enqueue work rather than block
microphone capture. `build_spoken_request` formats a transcript for H. The
prototype has not yet been connected to an H session.
