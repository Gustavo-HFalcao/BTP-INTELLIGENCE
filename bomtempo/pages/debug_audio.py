import time

import reflex as rx

from bomtempo.core.tts_service import TTSService


class DebugAudioState(rx.State):
    logs: list[str] = []
    test_url: str = ""
    audio_ctx_state: str = "Unknown"

    def log(self, msg: str):
        self.logs.append(f"{time.strftime('%H:%M:%S')} - {msg}")

    async def generate_sample(self):
        self.log("Generating TTS Sample...")
        try:
            url = TTSService.generate_speech("Este é um teste de áudio da plataforma Bomtempo.")
            if url:
                # Add timestamp to avoid cache
                self.test_url = f"{url}?t={int(time.time())}"
                self.log(f"Generated: {self.test_url}")
            else:
                self.log("Error: TTSService returned None")
        except Exception as e:
            self.log(f"Exception: {str(e)}")

    def play_js_element(self):
        self.log("Attempting JS Element play...")
        return rx.call_script(
            "var p = document.getElementById('debug_player'); "
            "if(p) { "
            "  p.play().then(() => console.log('Playing')).catch(e => alert(e)); "
            "} else { alert('Player element not found'); }"
        )

    def play_js_new_audio(self):
        self.log("Attempting new Audio() play...")
        return rx.call_script(
            f"new Audio('{self.test_url}').play().then(() => console.log('Playing New')).catch(e => alert('Error: ' + e));"
        )

    def check_context(self):
        return rx.call_script(
            "if(window.audioCtx) { return window.audioCtx.state; } else { return 'No Global Ctx'; }",
            callback=self.set_audio_ctx_state,
        )

    def set_audio_ctx_state(self, state: str):
        self.audio_ctx_state = state
        self.log(f"Audio Context State: {state}")


def debug_audio_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Audio Debug Lab", size="8"),
            rx.text("Use this page to isolate audio playback issues."),
            rx.divider(),
            rx.hstack(
                rx.button("1. Generate Sample", on_click=DebugAudioState.generate_sample),
                rx.text(DebugAudioState.test_url),
            ),
            rx.audio(
                id="debug_player",
                url=DebugAudioState.test_url,
                controls=True,
            ),
            rx.divider(),
            rx.heading("Playback Tests", size="4"),
            rx.hstack(
                rx.button("Test A: JS Element .play()", on_click=DebugAudioState.play_js_element),
                rx.button("Test B: new Audio()", on_click=DebugAudioState.play_js_new_audio),
            ),
            rx.divider(),
            rx.heading("Environment", size="4"),
            rx.button("Check Audio Context", on_click=DebugAudioState.check_context),
            rx.text(f"Context State: {DebugAudioState.audio_ctx_state}"),
            rx.divider(),
            rx.heading("Logs", size="4"),
            rx.box(
                rx.foreach(
                    DebugAudioState.logs,
                    lambda log: rx.text(log, font_family="monospace", font_size="0.8em"),
                ),
                bg="#1e1e1e",
                color="#00ff00",
                p="4",
                width="100%",
                height="300px",
                overflow_y="auto",
                border_radius="8px",
            ),
            spacing="4",
            padding="20px",
        )
    )
