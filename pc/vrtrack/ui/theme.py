"""Design tokens and the application stylesheet (dark theme)."""

BG = "#101319"
SURFACE = "#171b23"
SURFACE_2 = "#1f242e"
BORDER = "#2a303c"
TEXT = "#e8ebf2"
MUTED = "#8b93a7"
ACCENT = "#4da3ff"
ACCENT_DIM = "#2b5f99"
GOOD = "#43d19e"
WARN = "#ffc857"
BAD = "#ff6b6b"

STYLESHEET = f"""
* {{ font-family: 'Segoe UI', 'Inter', 'Ubuntu', sans-serif; font-size: 13px; color: {TEXT}; }}
QMainWindow, QWidget#root, QStackedWidget, QWidget#page {{ background: {BG}; }}
QLabel {{ background: transparent; }}
QLabel[muted="true"] {{ color: {MUTED}; }}
QLabel[h1="true"] {{ font-size: 22px; font-weight: 600; }}
QLabel[h2="true"] {{ font-size: 15px; font-weight: 600; }}
QLabel[mono="true"] {{ font-family: 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', monospace; }}

QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#sidebar {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}

QToolButton#nav {{ background: transparent; border: none; border-radius: 8px; padding: 10px 14px;
    text-align: left; color: {MUTED}; font-size: 14px; }}
QToolButton#nav:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
QToolButton#nav:checked {{ background: {ACCENT_DIM}; color: white; }}

QPushButton {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 16px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {MUTED}; }}
QPushButton[primary="true"] {{ background: {ACCENT}; border-color: {ACCENT}; color: #06121f; font-weight: 600; }}
QPushButton[primary="true"]:hover {{ background: #6bb4ff; }}
QPushButton[danger="true"]:hover {{ border-color: {BAD}; color: {BAD}; }}
QPushButton:checked {{ background: {WARN}; border-color: {WARN}; color: #1b1400; font-weight: 600; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {SURFACE_2}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 6px 8px; selection-background-color: {ACCENT_DIM}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {SURFACE_2}; border: 1px solid {BORDER}; selection-background-color: {ACCENT_DIM}; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {BORDER}; background: {SURFACE_2}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 9px 12px; border-radius: 8px; color: {MUTED}; }}
QListWidget::item:selected {{ background: {ACCENT_DIM}; color: white; }}
QListWidget::item:hover:!selected {{ background: {SURFACE_2}; }}

QToolTip {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px 6px; }}
QAbstractScrollArea, QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""
