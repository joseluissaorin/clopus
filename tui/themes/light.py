"""Light theme for CLOPUS TUI"""

LIGHT_THEME = """
$primary: #2563eb;
$secondary: #4f46e5;
$accent: #0891b2;
$success: #16a34a;
$warning: #d97706;
$error: #dc2626;
$background: #f8fafc;
$surface: #ffffff;
$surface-dark: #f1f5f9;
$text: #0f172a;
$text-muted: #64748b;
$border: #cbd5e1;

Screen {
    background: $background;
}

Header {
    dock: top;
    height: 3;
    background: $surface;
    color: $text;
    border-bottom: solid $border;
}

Footer {
    dock: bottom;
    height: 1;
    background: $surface;
    color: $text-muted;
}

.title {
    text-style: bold;
    color: $primary;
}

.panel {
    background: $surface;
    border: solid $border;
    padding: 1;
}

.panel-title {
    text-style: bold;
    color: $primary;
    margin-bottom: 1;
}

.card {
    background: $surface-dark;
    border: round $border;
    padding: 1;
    margin: 1;
}

.worker-busy {
    color: $primary;
}

.worker-idle {
    color: $text-muted;
}

.worker-error {
    color: $error;
}

.status-pending {
    color: $warning;
}

.status-completed {
    color: $success;
}

.status-failed {
    color: $error;
}

.status-assigned {
    color: $primary;
}

Button {
    background: $primary;
    color: white;
    border: none;
    padding: 0 2;
    margin: 0 1;
}

Button:hover {
    background: $secondary;
}

Button.-success {
    background: $success;
}

Button.-warning {
    background: $warning;
}

Button.-error {
    background: $error;
}

DataTable {
    background: $surface;
}

DataTable > .datatable--header {
    background: $surface-dark;
    color: $text;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $primary;
    color: white;
}

Input {
    background: $surface;
    border: solid $border;
    color: $text;
}

Input:focus {
    border: solid $primary;
}

TextArea {
    background: $surface;
    border: solid $border;
    color: $text;
}

Select {
    background: $surface;
    border: solid $border;
}

ProgressBar > .bar--bar {
    color: $primary;
}

ProgressBar > .bar--complete {
    color: $success;
}

Tabs {
    background: $surface;
    dock: top;
}

Tab {
    background: $surface;
    color: $text-muted;
    padding: 1 2;
}

Tab.-active {
    background: $surface-dark;
    color: $text;
    text-style: bold;
}

Tab:hover {
    background: $surface-dark;
    color: $text;
}

Log {
    background: $surface;
    color: $text;
    scrollbar-background: $surface;
    scrollbar-color: $border;
}

Tree {
    background: $surface;
    color: $text;
}

Tree > .tree--cursor {
    background: $primary;
    color: white;
}

.log-info {
    color: $primary;
}

.log-warning {
    color: $warning;
}

.log-error {
    color: $error;
}

.log-debug {
    color: $text-muted;
}

.sparkline {
    color: $accent;
}

.progress-complete {
    color: $success;
}

.progress-partial {
    color: $primary;
}

.highlight {
    background: $accent 10%;
}

.selected {
    background: $primary 20%;
}

#sidebar {
    width: 30;
    background: $surface;
    border-right: solid $border;
}

#main-content {
    background: $background;
}

.notification {
    background: $surface;
    border: solid $primary;
    padding: 1;
    margin: 1;
}

.notification-success {
    border: solid $success;
}

.notification-error {
    border: solid $error;
}

.notification-warning {
    border: solid $warning;
}
"""
