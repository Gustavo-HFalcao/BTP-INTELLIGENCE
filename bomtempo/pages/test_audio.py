from pathlib import Path

import reflex as rx


def test_audio_page() -> rx.Component:
    """
    Página de diagnóstico para problemas de áudio.
    Testa:
    1. Player com URL pública (Teste de Navegador/Codec)
    2. Player com Arquivo Uploaded Existente (Teste de Servidor/Rota)
    3. Exibe caminhos de configuração.
    """

    # Arquivo que sabemos que existe (baseado no `ls` anterior)
    test_file_name = "speech_2c5d36bc.mp3"
    local_path = Path("uploaded_files") / test_file_name
    file_exists = local_path.exists()
    file_size = local_path.stat().st_size if file_exists else 0

    return rx.center(
        rx.vstack(
            rx.heading("Diagnóstico de Áudio 🎧", size="8", color="white"),
            rx.text("Use esta página para isolar onde está o erro.", color="#ccc"),
            rx.divider(margin_y="20px"),
            # --- SEÇÃO 1: CONFIGURAÇÃO DO SERVIDOR ---
            rx.box(
                rx.text("1. Configuração do Servidor", font_weight="bold", color="#4ADE80"),
                rx.text(
                    f"Upload Dir (Config): {rx.get_upload_dir()}",
                    font_family="monospace",
                    color="white",
                ),
                rx.text(
                    f"Upload URL Pattern: {rx.get_upload_url('teste.mp3')}",
                    font_family="monospace",
                    color="white",
                ),
                rx.text(
                    f"Arquivo de Teste Local ({test_file_name}): {'✅ EXISTE' if file_exists else '❌ NÃO ENCONTRADO'}",
                    color="white",
                ),
                rx.text(f"Tamanho: {file_size} bytes", color="white"),
                bg="rgba(255,255,255,0.1)",
                padding="15px",
                border_radius="10px",
                width="100%",
            ),
            # --- SEÇÃO 2: TESTE DE NAVEGADOR (URL PÚBLICA) ---
            rx.box(
                rx.text("2. Teste de Navegador (URL Externa)", font_weight="bold", color="#FACC15"),
                rx.text(
                    "Se este não tocar, o problema é seu navegador ou caixa de som.",
                    font_size="12px",
                    color="#ccc",
                ),
                rx.audio(
                    url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                    controls=True,
                    width="100%",
                ),
                bg="rgba(255,255,255,0.1)",
                padding="15px",
                border_radius="10px",
                width="100%",
                margin_top="20px",
            ),
            # --- SEÇÃO 3: TESTE DE SERVIDOR (VIA PROXY) ---
            rx.box(
                rx.text(
                    "3. Teste de Servidor (Via Proxy Frontend)", font_weight="bold", color="#F472B6"
                ),
                rx.text(
                    f"Tentando tocar: /_upload/{test_file_name}", font_size="12px", color="#ccc"
                ),
                rx.audio(
                    url=f"/_upload/{test_file_name}",
                    controls=True,
                    width="100%",
                ),
                bg="rgba(255,255,255,0.1)",
                padding="15px",
                border_radius="10px",
                width="100%",
                margin_top="20px",
            ),
            # --- SEÇÃO 4: TESTE DIRETO (BACKEND :8000) ---
            rx.box(
                rx.text("4. Teste Direto (Link Backend)", font_weight="bold", color="#A78BFA"),
                rx.text(
                    "Se este link abrir, o arquivo existe e o backend está servindo.",
                    font_size="12px",
                    color="#ccc",
                ),
                rx.link(
                    "🔗 Abrir MP3 Direto no Navegador",
                    href=f"http://localhost:8000/_upload/{test_file_name}",
                    is_external=True,
                    color="#4ADE80",
                    font_size="16px",
                    font_weight="bold",
                ),
                rx.text(
                    "Player usando URL absoluta (localhost:8000):",
                    margin_top="10px",
                    font_size="12px",
                    color="#ccc",
                ),
                rx.audio(
                    url=f"http://localhost:8000/_upload/{test_file_name}",
                    controls=True,
                    width="100%",
                ),
                bg="rgba(255,255,255,0.1)",
                padding="15px",
                border_radius="10px",
                width="100%",
                margin_top="20px",
            ),
            rx.button(
                "Voltar para Home",
                on_click=rx.redirect("/"),
                margin_top="40px",
                variant="outline",
                color="white",
                border_color="white",
            ),
            max_width="600px",
            padding="40px",
            bg="#111",
            min_height="100vh",
        ),
        bg="#000",
        height="100vh",
        width="100%",
    )
