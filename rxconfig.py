import reflex as rx
# Force Reload Trigger 1

config = rx.Config(
    app_name="bomtempo",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    uploads_dir="uploaded_files", # Explicitly set for dynamic serving
)
