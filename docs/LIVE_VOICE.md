# Live voice workflow

## From the Jesse panel

With `GLADIA_API_KEY` in `.env`, start `uv run --env-file .env jesse-ui` and press the microphone button.
The controller captures the local microphone (macOS asks the terminal for microphone permission) and streams it
to Gladia. Each completed turn starts a catalogue investigation, or, while a session accepts messages, is sent to it
as a researcher correction (`source: "voice"`). The panel shows the partial transcript while listening.

A local near-field gate (`jesse.voice.gate`) sends silence instead of audio unless a block is at least 15 dB louder
than the room level measured over the last 15 s, so distant voices are not transcribed. The first second is used to
measure the room. Raise `JESSE_VOICE_GATE_DB` in `.env` (for example 20) if other voices still get through; lower it
if your own voice is cut. A headset microphone isolates best.

## Jesse's voice

When an OpenAI key is set, the panel's speaker button reads Jesse's announcements aloud (experiment selection,
simulator opening, each recorded trial, the outcome). The controller sends only those event texts to OpenAI
text-to-speech (`gpt-4o-mini-tts`, voice `ash`, an original character voice) and caches the mp3 in the run folder.
Earlier history is never read aloud. Override with `JESSE_TTS_VOICE` or `JESSE_TTS_MODEL`.

## Terminal preview

This prototype streams microphone audio to Gladia, displays partial transcripts,
and groups final utterances into researcher turns. By default it only prints
the transcript. Only speak content you are comfortable sending to Gladia.

To enrich each completed turn with OpenAI and send it to an interactive H
browser session, set `GLADIA_API_KEY`, `OPENAI_API_KEY` (or `OPENAI_KEY`) and
`HAI_API_KEY` in `.env`, then run:

```sh
uv run --env-file .env python -m jesse.voice.live --run
```

The first turn starts a hosted visual-browser session; subsequent turns are
enriched independently and sent to that same session while it remains open.
The terminal shows the enriched request, H answers, and Agent View link.
Original transcripts, prepared requests, submission status and session events
are saved under `runs/`. Both OpenAI and H receive the request, and H can browse
the web; their services may incur charges. Do not speak private data unless you
intend to send it to all three providers.

This general browser workflow does not select or execute the approved
experiment protocols or their recording and analysis tools. H's response and
any scientific conclusions are unverified. It is instructed not to log in,
submit forms or make external changes, but these are model instructions, not
an enforced browser access policy. Watch Agent View. The session has a
10-minute maximum and may also end after an idle timeout. Jesse checks session
status before a follow-up, but H can restart a finished session if it ends
between that check and the message submission. An accepted message is not
confirmation that H has processed it. Delivery failures are reported as
unknown and are not automatically retried.

Pressing Ctrl+C stops listening, waits for queued turns to be processed, then
cancels H; unfinished H work may be interrupted. Keep the listener open while
waiting for answers or making follow-up requests. Background speech can still
delay the detection of a completed turn.

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
before closing. Detection is restricted to French and English (per-utterance switching), and Gladia's audio
enhancer plus a strict speech threshold (0.8) reduce background voices and noise. Live sessions are billed by Gladia and require internet access.

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
microphone capture. `build_spoken_request` formats a transcript for preview.
