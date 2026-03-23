import sys
import re

file_path = r'c:\Users\Gustavo\bomtempo-dashboard\bomtempo\components\charts.py'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_str = '        class_name="kpi-card",\n        position="relative",\n        width="100%",\n        height="100%",\n        # Interactivity\n        on_click=on_click,\n        cursor="pointer" if on_click else "default",\n        _hover=(\n            {\n                "transform": "translateY(-4px)",\n                "box_shadow": "0 10px 30px -10px rgba(201, 139, 42, 0.2)",\n                "border_color": S.COPPER,\n            }'
    
    new_str = '        class_name="kpi-card glass-panel",\n        bg="rgba(14, 26, 23, 0.6)",\n        border=f"1px solid {S.BORDER_SUBTLE}",\n        border_radius="12px",\n        padding="24px",\n        position="relative",\n        width="100%",\n        height="100%",\n        # Interactivity\n        on_click=on_click,\n        cursor="pointer" if on_click else "default",\n        _hover=(\n            {\n                "transform": "translateY(-4px)",\n                "box_shadow": "0 10px 30px -10px rgba(201, 139, 42, 0.2)",\n                "border": f"1px solid {S.COPPER}",\n                "bg": "rgba(201, 139, 42, 0.05)",\n            }'

    if old_str in content:
        content = content.replace(old_str, new_str)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated charts component successfully.")
    else:
        print("Target block not found in charts.py!")

except Exception as e:
    print(f"Error: {e}")
