---
name: feedback-ui-pattern
description: "Critical feedback on UI construction in ddii_scopus — always use .ui files, never build layouts in Python code"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8d53f832-ade7-4947-b43b-45a00ffb5c80
---

Use `.ui` Qt Designer files for ALL widget layouts. Never build UI structure in Python code.

**Why:** The entire project uses `loadUi(Path(__file__).parent / "name.ui", self)`. When I built `DeviceSettingsWidget` entirely in Python (QVBoxLayout, addWidget calls), the user explicitly corrected: "Ты сделал все через код, хотя у меня весь ui сделан в *.ui и подключается через loadUi".

**How to apply:** Any new widget = create `.ui` first. Python file only wires validators, connects signals, and optionally builds truly dynamic content (like a 32-field grid) inside a placeholder QWidget from the `.ui`.

---

Widgets passed into `widget_model` must be flat — no outer `QScrollArea`.

**Why:** `create_tab_widget_items()` already wraps each dict entry in `QGroupBox` + one shared `QScrollArea` per tab. If a widget adds its own outer scroll, the result is nested scrollbars. User said: "Компановку виджетов во вкладке Настройка нужно сделать также как в Осциллограф, а то сейчас слишком много вложенных scrollbar".

**How to apply:** Reference the "Осциллограф" tab as the canonical pattern — each sub-widget is a flat `QWidget`, the outer system provides all scrolling. A fixed-height inner `QScrollArea` for a dense sub-section (e.g. HH grid) is fine.
