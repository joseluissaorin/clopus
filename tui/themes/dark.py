"""Dark theme for CLOPUS TUI"""

DARK_THEME = """
$primary: #3b82f6;
$secondary: #6366f1;
$accent: #22d3ee;
$success: #22c55e;
$warning: #f59e0b;
$error: #ef4444;
$background: #0f172a;
$surface: #1e293b;
$surface-light: #334155;
$text: #f8fafc;
$text-muted: #94a3b8;
$border: #475569;

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
    color: $accent;
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
    background: $surface-light;
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
    color: $text;
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
    background: $surface-light;
    color: $text;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $primary;
    color: $text;
}

Input {
    background: $surface-light;
    border: solid $border;
    color: $text;
}

Input:focus {
    border: solid $primary;
}

TextArea {
    background: $surface-light;
    border: solid $border;
    color: $text;
}

Select {
    background: $surface-light;
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
    background: $surface-light;
    color: $text;
    text-style: bold;
}

Tab:hover {
    background: $surface-light;
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
    background: $accent 20%;
}

.selected {
    background: $primary 30%;
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
