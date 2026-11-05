"""Stylesheets shared by the Streamlit app and the exported report.

COMPONENT_CSS styles the fragments and inherits its colours, so it works
on the light and dark Streamlit themes. PAGE_CSS adds the page rules the
standalone report needs.
"""

COMPONENT_CSS = """
.qd-muted { opacity: 0.75; font-size: 0.9rem; }
.qd-line { margin: 0 0 4px; }
.qd-card { border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 8px;
           padding: 14px 18px; margin-bottom: 14px; }
.qd-scroll { overflow-x: auto; }
.qd-table { border-collapse: collapse; width: 100%; font-size: 0.78rem; }
.qd-table th:first-child, .qd-table td:first-child { white-space: normal; }
.qd-table th, .qd-table td { text-align: left; padding: 3px 4px; white-space: nowrap;
                             border-bottom: 1px solid rgba(128, 128, 128, 0.35); }
.qd-subject { max-width: 520px; }
.qd-badge { display: inline-block; border-radius: 9999px; padding: 6px 14px;
            font-weight: 700; font-size: 0.95rem; margin: 6px 0 10px; }
.qd-alert { background: #fef3c7; border: 1px solid #f59e0b; color: #78350f;
            border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; }
.qd-error { color: #dc2626; font-size: 0.9rem; }
"""

PAGE_CSS = """
:root { color-scheme: light; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
       color: #0f172a; background: #ffffff; margin: 0; }
main { max-width: 1100px; margin: 0 auto; padding: 16px; }
h1, h2, h3 { margin: 1rem 0 0.5rem; }
hr { border: 0; border-top: 1px solid #e2e8f0; margin: 12px 0; }
"""

BASE_CSS = PAGE_CSS + COMPONENT_CSS
