
import reflex as rx

config = rx.Config(
    app_name="bomtempo",
    tailwind={
        "theme": {
            "extend": {
                "fontFamily": {
                    "tech": ["Rajdhani", "sans-serif"],
                    "body": ["Outfit", "sans-serif"],
                    "mono": ["JetBrains Mono", "monospace"],
                },
                "colors": {
                    "copper": "#C98B2A",
                    "patina": "#2A9D8F",
                    "void": "#030504",
                    "depth": "#081210",
                }
            }
        }
    }
)
