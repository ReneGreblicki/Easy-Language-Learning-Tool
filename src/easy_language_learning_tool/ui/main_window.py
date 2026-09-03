from __future__ import annotations

import random
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from easy_language_learning_tool.config.paths import AppPaths, resolve_app_paths
from easy_language_learning_tool.domain.enums import CefrLevel, CefrMode, Language, Provider
from easy_language_learning_tool.domain.frequency import FrequencyRepository
from easy_language_learning_tool.domain.models import CefrSelection, GenerationSettings
from easy_language_learning_tool.domain.planner import build_generation_plan
from easy_language_learning_tool.flashcards import (
    FlashcardAudioPlayer,
    FlashcardAudioService,
    FlashcardMode,
    FlashcardService,
    FlashcardSession,
)
from easy_language_learning_tool.generation.service import GenerationService
from easy_language_learning_tool.history.service import HistoryItem, HistoryService
from easy_language_learning_tool.providers.factory import create_provider
from easy_language_learning_tool.providers.pricing import PricingRegistry
from easy_language_learning_tool.security.credentials import CredentialStore, secure_store_name
from easy_language_learning_tool.tts.manifest import file_checksum, settings_checksum
from easy_language_learning_tool.tts.models import TtsSettings, VoiceSettings
from easy_language_learning_tool.tts.service import EdgeFfmpegBackend, TtsService, list_edge_voices
from easy_language_learning_tool.workbook.service import (
    export_xlsx,
    import_language_pair,
    import_xlsx,
)

from .controls import (
    ClickableFrame,
    ScrollPage,
)
from .controls import (
    DeliberateWheelComboBox as QComboBox,
)
from .controls import (
    DeliberateWheelSlider as QSlider,
)
from .controls import (
    DeliberateWheelSpinBox as QSpinBox,
)
from .task_worker import TaskThread

LIGHT_THEME = """
QWidget { background: #F7F9FC; color: #172033; font-size: 13px; }
QGroupBox { border: 1px solid #CAD5E3; border-radius: 7px; margin-top: 12px; padding: 12px; font-weight: 600; }
QGroupBox::title { color: #2E74B5; subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QPushButton { background: #2E74B5; color: white; border: 0; border-radius: 5px; padding: 8px 14px; font-weight: 600; }
QPushButton:disabled { background: #AAB7C7; }
QComboBox, QSpinBox, QLineEdit, QTableWidget { background: white; border: 1px solid #B8C4D4; border-radius: 4px; padding: 5px; }
QTabBar::tab:selected { color: #2E74B5; font-weight: 700; }
QProgressBar { border: 1px solid #B8C4D4; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #2E74B5; }
QFrame#flashcardControls { background: #EEF3F9; border: 1px solid #D5DEEA; border-radius: 10px; }
QFrame#flashcardSurface { background: white; border: 1px solid #D5DEEA; border-radius: 18px; }
QLabel#flashcardWord { background: transparent; font-size: 34pt; font-weight: 700; }
QLabel#flashcardSentence { background: transparent; font-size: 20pt; }
QLabel#flashcardLanguage { background: #E1EDF9; color: #245E96; border-radius: 14px; padding: 6px 12px; font-weight: 700; }
QPushButton#flashcardSound { background: white; color: #245E96; border: 1px solid #9CC6E8; border-radius: 22px; padding: 0; font-size: 18pt; }
"""

DARK_THEME = """
QWidget { background: #111827; color: #E5EAF2; font-size: 13px; }
QGroupBox { border: 1px solid #334155; border-radius: 7px; margin-top: 12px; padding: 12px; font-weight: 600; }
QGroupBox::title { color: #60A5FA; subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QPushButton { background: #2563A6; color: white; border: 0; border-radius: 5px; padding: 8px 14px; font-weight: 600; }
QPushButton:disabled { background: #475569; color: #94A3B8; }
QComboBox, QSpinBox, QLineEdit, QTableWidget { background: #1E293B; border: 1px solid #475569; border-radius: 4px; padding: 5px; }
QTabBar::tab:selected { color: #60A5FA; font-weight: 700; }
QProgressBar { border: 1px solid #475569; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #3B82C4; }
QFrame#flashcardControls { background: #172033; border: 1px solid #334155; border-radius: 10px; }
QFrame#flashcardSurface { background: #18233B; border: 1px solid #334155; border-radius: 18px; }
QLabel#flashcardWord { background: transparent; font-size: 34pt; font-weight: 700; }
QLabel#flashcardSentence { background: transparent; font-size: 20pt; color: #D8E1EE; }
QLabel#flashcardLanguage { background: #203E61; color: #8BC7F5; border-radius: 14px; padding: 6px 12px; font-weight: 700; }
QPushButton#flashcardSound { background: #18233B; color: #8BC7F5; border: 1px solid #4EA5E0; border-radius: 22px; padding: 0; font-size: 18pt; }
"""

VOICE_DEFAULTS: dict[Language, tuple[str, str]] = {
    Language.US_ENGLISH: ("en-US-JennyNeural", "en-US-GuyNeural"),
    Language.EUROPEAN_SPANISH: ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
    Language.GERMAN: ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
    Language.EUROPEAN_PORTUGUESE: ("pt-PT-RaquelNeural", "pt-PT-DuarteNeural"),
    Language.FRENCH: ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
    Language.ITALIAN: ("it-IT-ElsaNeural", "it-IT-DiegoNeural"),
    Language.THAI_SCRIPT: ("th-TH-PremwadeeNeural", "th-TH-NiwatNeural"),
    Language.THAI_PAIBOON: ("th-TH-PremwadeeNeural", "th-TH-NiwatNeural"),
}

LANGUAGE_BADGES: dict[Language, str] = {
    Language.US_ENGLISH: "EN",
    Language.EUROPEAN_SPANISH: "ES",
    Language.GERMAN: "DE",
    Language.EUROPEAN_PORTUGUESE: "PT",
    Language.FRENCH: "FR",
    Language.ITALIAN: "IT",
    Language.THAI_SCRIPT: "ไทย",
    Language.THAI_PAIBOON: "TH-PB",
}

PRONOUN_SCALE_EXPLANATIONS = {
    0: (
        "Option 0: Every sentence uses a neutral or impersonal subject structure, such as "
        "‘The day is nice’, ‘The sun is up’, or ‘The school is far’."
    ),
    1: (
        "Option 1: 80% of sentences stay neutral or impersonal; 20% use a randomly selected "
        "first-, second-, or third-person form."
    ),
    2: (
        "Option 2: 60% of sentences stay neutral or impersonal; 40% use a randomly selected "
        "first-, second-, or third-person form."
    ),
    3: (
        "Option 3: 40% of sentences stay neutral or impersonal; 60% use a randomly selected "
        "first-, second-, or third-person form."
    ),
    4: (
        "Option 4: 20% of sentences stay neutral or impersonal; 80% use a randomly selected "
        "first-, second-, or third-person form."
    ),
    5: (
        "Option 5: Every sentence changes to a different subject pattern. Neutral or impersonal "
        "structures are included alongside first-, second-, and third-person forms."
    ),
}


def resource_path(*parts: str) -> Path:
    packaged = Path(sys.argv[0]).resolve().parent
    for root in (packaged, packaged.parent / "Resources"):
        if root.joinpath(parts[0]).exists():
            return root.joinpath(*parts)
    return Path(__file__).resolve().parents[3].joinpath(*parts)


def frequency_data_path() -> Path:
    for filename in ("words.jsonl.gz", "words.jsonl"):
        production = resource_path("resources", "frequency_data", "production", filename)
        if production.is_file():
            return production
    return resource_path("resources", "frequency_data", "demo", "words.jsonl")


def trash_name() -> str:
    return "Trash" if sys.platform == "darwin" else "Recycle Bin"


class MainWindow(QMainWindow):
    def __init__(self, paths: AppPaths | None = None) -> None:
        super().__init__()
        self.paths = paths or resolve_app_paths()
        self.paths.create()
        self.credentials = CredentialStore()
        self.history = HistoryService(
            self.paths.data / "easy_language_learning_tool.sqlite3", self.paths.history
        )
        self.flashcard_service = FlashcardService(
            self.paths.data / "easy_language_learning_tool.sqlite3"
        )
        self._flashcard_session: FlashcardSession | None = None
        self._flashcard_source_id: int | None = None
        self._flashcard_row_count = 0
        self._flashcard_languages = (Language.EUROPEAN_SPANISH, Language.US_ENGLISH)
        self._flashcard_audio = FlashcardAudioService(self.paths.cache, self._backend())
        self._flashcard_player = FlashcardAudioPlayer()
        self.frequency_path = frequency_data_path()
        self.frequency_repository = FrequencyRepository.from_jsonl(self.frequency_path)
        self.frequency_is_production = self.frequency_path.parent.name == "production"
        self._threads: set[TaskThread] = set()
        self._provider_adapter: Any = None
        self._tts_service: TtsService | None = None
        self._generation_resume: tuple[GenerationSettings, Path, Path, str, str] | None = None
        self.setWindowTitle("Easy Language Learning Tool")
        icon_name = "logo.png" if sys.platform == "darwin" else "logo.ico"
        self.setWindowIcon(QIcon(str(resource_path("assets", "icons", icon_name))))
        self.setMinimumSize(720, 405)
        view = self.menuBar().addMenu("View")
        theme = QAction("Use dark theme", self, checkable=True)
        theme.toggled.connect(lambda on: self.setStyleSheet(DARK_THEME if on else LIGHT_THEME))
        view.addAction(theme)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._sentence_tab(), "Sentence Creation")
        self.tabs.addTab(self._flashcards_tab(), "Flashcards")
        self.tabs.addTab(self._tts_tab(), "TTS")
        self.tabs.addTab(self._history_tab(), "History")
        self.tabs.addTab(self._information_tab(), "Information")
        self.setCentralWidget(self.tabs)
        self.setStyleSheet(LIGHT_THEME)
        self.refresh_history()
        self._resume_flashcards()

    def size_and_center(self) -> None:
        screen = self.screen().availableGeometry()
        self.resize(
            max(self.minimumWidth(), round(screen.width() * 0.5)),
            max(self.minimumHeight(), round(screen.height() * 0.5)),
        )
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def _start_task(
        self,
        task: Any,
        success: Any,
        failure: Any | None = None,
        progress: Any | None = None,
    ) -> None:
        if progress is None:
            thread = TaskThread(task)
        else:
            thread = TaskThread(lambda: task(thread.progress.emit))
            thread.progress.connect(progress)
        self._threads.add(thread)
        thread.succeeded.connect(success)
        thread.failed.connect(failure or self._show_error)
        thread.finished.connect(lambda: self._threads.discard(thread))
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _sentence_tab(self) -> QWidget:
        root = ScrollPage()
        layout = QVBoxLayout(root)
        row_limit_notice = QLabel(
            "Output is limited to 5,000 rows. Each base word creates one original row plus the "
            "selected extra-form rows. Maximum base words = 5,000 ÷ (1 + extra forms): for "
            "example, 1 extra form allows 2,500 base words. Extra forms adapt to the word type "
            "(for example be/was, tool/tools, or adjective agreement)."
        )
        row_limit_notice.setWordWrap(True)
        row_limit_notice.setObjectName("rowLimitNotice")
        layout.addWidget(row_limit_notice)
        provider_group = QGroupBox("AI provider")
        provider_form = QFormLayout(provider_group)
        self.provider_combo = QComboBox()
        for provider in Provider:
            self.provider_combo.addItem(provider.value, provider)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Not required for Ollama")
        self.remember_key = QCheckBox(f"Remember securely in {secure_store_name()}")
        self.endpoint = QLineEdit()
        self.endpoint.setPlaceholderText("Required only for custom endpoints")
        self.model_combo = QComboBox()
        connect = QPushButton("Test connection and load models")
        connect.clicked.connect(self.connect_provider)
        more = QPushButton("Show more setup instructions")
        more.clicked.connect(self.show_provider_help)
        for label, widget in (
            ("Provider", self.provider_combo),
            ("API key", self.api_key),
            ("", self.remember_key),
            ("Custom/Ollama URL", self.endpoint),
            ("Model", self.model_combo),
            ("", connect),
            ("", more),
        ):
            provider_form.addRow(label, widget)
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)

        settings_group = QGroupBox("Sentence settings")
        form = QFormLayout(settings_group)
        self.sentence_settings_form = form
        self.learning = self._language_combo()
        self.translation = self._language_combo()
        self.learning.setCurrentIndex(self.learning.findData(Language.EUROPEAN_SPANISH))
        self.translation.setCurrentIndex(self.translation.findData(Language.US_ENGLISH))
        self.base_count = QSpinBox()
        self.base_count.setRange(1, 5_000)
        self.base_count.setValue(100)
        self.extra_forms = QComboBox()
        self.extra_forms.addItems([str(value) for value in range(5)])
        self.cefr_mode = QComboBox()
        self.cefr_mode.addItem("Single level", CefrMode.SINGLE)
        self.cefr_mode.addItem("Gradual increase", CefrMode.GRADUAL)
        self.single_cefr, self.start_cefr, self.end_cefr = QComboBox(), QComboBox(), QComboBox()
        for level in CefrLevel:
            for combo in (self.single_cefr, self.start_cefr, self.end_cefr):
                combo.addItem(level.value, level)
        self.end_cefr.setCurrentIndex(3)
        range_widget = QWidget()
        range_row = QHBoxLayout(range_widget)
        range_row.setContentsMargins(0, 0, 0, 0)
        range_row.addWidget(self.start_cefr)
        range_row.addWidget(QLabel("to"))
        range_row.addWidget(self.end_cefr)
        percentages = QWidget()
        percent_layout = QGridLayout(percentages)
        self.cefr_percentages: dict[CefrLevel, QSpinBox] = {}
        for index, level in enumerate(CefrLevel):
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setSuffix("%")
            self.cefr_percentages[level] = spin
            percent_layout.addWidget(QLabel(level.value), 0, index)
            percent_layout.addWidget(spin, 1, index)
            spin.valueChanged.connect(self.refresh_sentence_state)
        self.cefr_total = QLabel()
        self.question_slider, question_row = self._labelled_slider(0, 100, 20, "%")
        self.pronouns = QComboBox()
        self.pronouns.addItems([str(value) for value in range(6)])
        self.pronoun_explanation = QLabel()
        self.pronoun_explanation.setWordWrap(True)
        self.final_rows = QLabel()
        self.frequency_status = QLabel()
        self.frequency_status.setWordWrap(True)
        self.output_path = QLineEdit(str(Path.home() / "Documents" / "Language Sentences.xlsx"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.choose_generation_output)
        output_widget = QWidget()
        output_row = QHBoxLayout(output_widget)
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.addWidget(self.output_path)
        output_row.addWidget(browse)
        self.generate_button = QPushButton("Generate workbook")
        self.generate_button.clicked.connect(self.generate_workbook)
        self.generation_progress = QProgressBar()
        for label, settings_widget in (
            ("Learning language (foreign)", self.learning),
            ("Translation language", self.translation),
            ("Base words", self.base_count),
            ("Extra word forms (0–4)", self.extra_forms),
            ("Calculated output", self.final_rows),
            ("CEFR mode", self.cefr_mode),
            ("Single level", self.single_cefr),
            ("Gradual range", range_widget),
            ("Level percentages", percentages),
            ("Percentage total", self.cefr_total),
            ("Questions / statements", question_row),
            ("Pronoun-change scale (0–5)", self.pronouns),
            ("", self.pronoun_explanation),
            ("Word dataset", self.frequency_status),
            ("Workbook", output_widget),
            ("", self.generate_button),
            ("Progress", self.generation_progress),
        ):
            form.addRow(label, settings_widget)

        costs = QGroupBox("Estimated API cost")
        costs_layout = QVBoxLayout(costs)
        self.cost_label = QLabel()
        self.cost_label.setWordWrap(True)
        costs_layout.addWidget(self.cost_label)
        self.model_combo.currentIndexChanged.connect(self.refresh_costs)
        for signal in (
            self.base_count.valueChanged,
            self.extra_forms.currentIndexChanged,
            self.learning.currentIndexChanged,
            self.translation.currentIndexChanged,
            self.cefr_mode.currentIndexChanged,
            self.start_cefr.currentIndexChanged,
            self.end_cefr.currentIndexChanged,
            self.pronouns.currentIndexChanged,
        ):
            signal.connect(self.refresh_sentence_state)
        for signal in (
            self.cefr_mode.currentIndexChanged,
            self.start_cefr.currentIndexChanged,
            self.end_cefr.currentIndexChanged,
        ):
            signal.connect(self._reset_percentages)
        layout.addWidget(provider_group)
        layout.addWidget(settings_group)
        layout.addWidget(costs)
        layout.addStretch()
        self._reset_percentages()
        self._provider_changed()
        return self._scroll(root)

    def _flashcards_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        controls_frame = QFrame()
        controls_frame.setObjectName("flashcardControls")
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        self.flashcard_workbook = QLineEdit()
        self.flashcard_workbook.setReadOnly(True)
        self.flashcard_workbook.setPlaceholderText(
            "Load an app-generated four-column .xlsx workbook"
        )
        load_history = QPushButton("Load from History")
        load_history.clicked.connect(self.choose_flashcard_history)
        browse = QPushButton("Load from Desktop")
        browse.clicked.connect(self.choose_flashcard_workbook)
        controls_layout.addWidget(load_history, 0, 0)
        controls_layout.addWidget(browse, 0, 1)
        controls_layout.addWidget(self.flashcard_workbook, 0, 2, 1, 6)
        self.flashcard_mode = QComboBox()
        for mode in FlashcardMode:
            self.flashcard_mode.addItem(mode.label, mode)
        self.flashcard_mode.setCurrentIndex(self.flashcard_mode.findData(FlashcardMode.BOTH))
        self.flashcard_mode.currentIndexChanged.connect(self._flashcard_mode_changed)
        self.flashcard_selected_rows = QCheckBox("Selected rows only")
        self.flashcard_selected_rows.toggled.connect(self._flashcard_range_toggled)
        self.flashcard_from_rank = QLineEdit()
        self.flashcard_to_rank = QLineEdit()
        for field, placeholder in (
            (self.flashcard_from_rank, "From rank"),
            (self.flashcard_to_rank, "To rank"),
        ):
            field.setValidator(QIntValidator(1, 5_000, field))
            field.setPlaceholderText(placeholder)
            field.setEnabled(False)
        self.flashcard_apply_range = QPushButton("Apply rows")
        self.flashcard_apply_range.setEnabled(False)
        self.flashcard_apply_range.clicked.connect(self._apply_flashcard_range)
        controls_layout.addWidget(QLabel("Cards"), 1, 0)
        controls_layout.addWidget(self.flashcard_mode, 1, 1)
        controls_layout.addWidget(self.flashcard_selected_rows, 1, 2)
        controls_layout.addWidget(QLabel("From"), 1, 3)
        controls_layout.addWidget(self.flashcard_from_rank, 1, 4)
        controls_layout.addWidget(QLabel("To"), 1, 5)
        controls_layout.addWidget(self.flashcard_to_rank, 1, 6)
        controls_layout.addWidget(self.flashcard_apply_range, 1, 7)
        self.flashcard_source_status = QLabel("No workbook loaded.")
        self.flashcard_source_status.setWordWrap(True)
        controls_layout.addWidget(self.flashcard_source_status, 2, 0, 1, 8)
        controls_layout.setColumnStretch(2, 1)

        badge_row = QHBoxLayout()
        badge_row.addStretch()
        self.flashcard_language = QLabel("ES  →  EN")
        self.flashcard_language.setObjectName("flashcardLanguage")
        self.flashcard_language.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_row.addWidget(self.flashcard_language)

        self.flashcard_surface = ClickableFrame()
        self.flashcard_surface.setObjectName("flashcardSurface")
        self.flashcard_surface.setMinimumHeight(300)
        self.flashcard_surface.setCursor(Qt.CursorShape.PointingHandCursor)
        self.flashcard_surface.setToolTip("Click to flip the card")
        self.flashcard_surface.clicked.connect(self.flip_flashcard)
        card_layout = QVBoxLayout(self.flashcard_surface)
        card_layout.setContentsMargins(48, 24, 48, 24)
        card_layout.addStretch()
        self.flashcard_word = QLabel("Load a workbook to begin")
        self.flashcard_word.setObjectName("flashcardWord")
        self.flashcard_word.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flashcard_word.setWordWrap(True)
        self.flashcard_word.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        word_font = self.flashcard_word.font()
        word_font.setPointSize(34)
        word_font.setBold(True)
        self.flashcard_word.setFont(word_font)
        self.flashcard_sentence = QLabel()
        self.flashcard_sentence.setObjectName("flashcardSentence")
        self.flashcard_sentence.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flashcard_sentence.setWordWrap(True)
        self.flashcard_sentence.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        sentence_font = self.flashcard_sentence.font()
        sentence_font.setPointSize(20)
        self.flashcard_sentence.setFont(sentence_font)
        card_layout.addWidget(self.flashcard_word)
        card_layout.addSpacing(28)
        card_layout.addWidget(self.flashcard_sentence)
        card_layout.addSpacing(22)
        self.flashcard_sound = QPushButton("🔊")
        self.flashcard_sound.setObjectName("flashcardSound")
        self.flashcard_sound.setFixedSize(44, 44)
        self.flashcard_sound.setToolTip("Play this side")
        self.flashcard_sound.setEnabled(False)
        self.flashcard_sound.clicked.connect(self.play_flashcard_audio)
        card_layout.addWidget(self.flashcard_sound, alignment=Qt.AlignmentFlag.AlignHCenter)
        card_layout.addStretch()

        self.flashcard_progress = QLabel("No active deck")
        self.flashcard_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flashcard_progress_bar = QProgressBar()
        self.flashcard_progress_bar.setTextVisible(False)
        self.flashcard_progress_bar.setRange(0, 1)
        self.flashcard_progress_bar.setValue(0)
        self.flashcard_progress_bar.setMaximumHeight(7)
        navigation = QHBoxLayout()
        navigation.addStretch()
        self.flashcard_previous = QPushButton("← Previous")
        self.flashcard_flip = QPushButton("Reveal")
        self.flashcard_next = QPushButton("Next →")
        self.flashcard_shuffle = QPushButton("↻  Reshuffle")
        self.flashcard_previous.clicked.connect(self.previous_flashcard)
        self.flashcard_flip.clicked.connect(self.flip_flashcard)
        self.flashcard_next.clicked.connect(self.next_flashcard)
        self.flashcard_shuffle.clicked.connect(self.shuffle_flashcards)
        for button in (self.flashcard_previous, self.flashcard_flip, self.flashcard_next):
            button.setEnabled(False)
            navigation.addWidget(button)
        navigation.addStretch()
        self.flashcard_shuffle.setEnabled(False)
        shuffle_row = QHBoxLayout()
        shuffle_row.addStretch()
        shuffle_row.addWidget(self.flashcard_shuffle)
        shuffle_row.addStretch()

        layout.addWidget(controls_frame)
        layout.addLayout(badge_row)
        layout.addWidget(self.flashcard_surface, 1)
        layout.addWidget(self.flashcard_progress)
        layout.addWidget(self.flashcard_progress_bar)
        layout.addLayout(navigation)
        layout.addLayout(shuffle_row)
        return root

    def _tts_tab(self) -> QWidget:
        root = ScrollPage()
        layout = QVBoxLayout(root)
        source_group = QGroupBox("Workbook input")
        source_form = QFormLayout(source_group)
        self.tts_workbook = QLineEdit()
        history = QPushButton("Load from History")
        history.clicked.connect(self.choose_tts_history)
        browse = QPushButton("Load from Desktop")
        browse.clicked.connect(self.choose_tts_workbook)
        source_widget = QWidget()
        source_row = QHBoxLayout(source_widget)
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.tts_workbook)
        source_row.addWidget(history)
        source_row.addWidget(browse)
        source_form.addRow("Four-column .xlsx", source_widget)

        voices = QGroupBox("Languages and natural Edge voices")
        voice_form = QFormLayout(voices)
        self.foreign_language, self.translation_language = (
            self._language_combo(),
            self._language_combo(),
        )
        self.foreign_language.setCurrentIndex(
            self.foreign_language.findData(Language.EUROPEAN_SPANISH)
        )
        self.translation_language.setCurrentIndex(
            self.translation_language.findData(Language.US_ENGLISH)
        )
        self.foreign_voice, self.translation_voice = QComboBox(), QComboBox()
        self.foreign_language.currentIndexChanged.connect(self._refresh_voices)
        self.translation_language.currentIndexChanged.connect(self._refresh_voices)
        self.foreign_rate, self.foreign_pitch, self.foreign_volume = (
            self._signed_spin("%"),
            self._signed_spin(" Hz"),
            self._signed_spin("%"),
        )
        self.translation_rate, self.translation_pitch, self.translation_volume = (
            self._signed_spin("%"),
            self._signed_spin(" Hz"),
            self._signed_spin("%"),
        )
        for label, widget in (
            ("Language 1 — foreign columns", self.foreign_language),
            ("Foreign voice", self.foreign_voice),
            ("Language 2 — translation columns", self.translation_language),
            ("Translation voice", self.translation_voice),
            ("Foreign speed", self.foreign_rate),
            ("Foreign pitch", self.foreign_pitch),
            ("Foreign volume", self.foreign_volume),
            ("Translation speed", self.translation_rate),
            ("Translation pitch", self.translation_pitch),
            ("Translation volume", self.translation_volume),
        ):
            voice_form.addRow(label, widget)
        refresh_voices = QPushButton("Refresh available Edge voices")
        refresh_voices.clicked.connect(self.refresh_edge_voices)
        voice_form.addRow("", refresh_voices)

        pauses = QGroupBox("Break duration (1–10 seconds)")
        pause_form = QFormLayout(pauses)
        self.pause_sliders: list[QSlider] = []
        names = (
            "Foreign word → word translation",
            "Word translation → foreign sentence",
            "Foreign sentence → sentence translation",
            "Sentence translation → next row",
        )
        for index, name in enumerate(names):
            slider, row = self._labelled_slider(1, 10, 2 if index > 1 else 1, " s")
            self.pause_sliders.append(slider)
            pause_form.addRow(name, row)
        controls = QHBoxLayout()
        for label, callback in (
            ("Preview 2 rows", self.preview_tts),
            ("Create MP3", self.generate_tts),
            ("Pause", self.pause_tts),
            ("Resume", self.resume_tts),
            ("Cancel", self.cancel_tts),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        self.tts_progress = QProgressBar()
        self._refresh_voices()
        layout.addWidget(source_group)
        layout.addWidget(voices)
        layout.addWidget(pauses)
        layout.addLayout(controls)
        layout.addWidget(self.tts_progress)
        layout.addStretch()
        return self._scroll(root)

    def _history_tab(self) -> QWidget:
        root = ScrollPage()
        layout = QVBoxLayout(root)
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Created", "Status", "Location"]
        )
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        controls = QHBoxLayout()
        for label, callback in (
            ("Refresh", self.refresh_history),
            ("Use in Flashcards", self.history_to_flashcards),
            ("Use in TTS", self.history_to_tts),
            ("Rename", self.rename_history),
            (f"Delete to {trash_name()}", self.delete_history),
            ("Re-export", self.export_history),
            ("Regenerate", self.regenerate_history),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addWidget(
            QLabel("Latest 20 app-owned spreadsheets and latest 20 app-owned MP3 files.")
        )
        layout.addWidget(self.history_table)
        layout.addLayout(controls)
        return self._scroll(root)

    def _information_tab(self) -> QWidget:
        browser = QTextBrowser()
        browser.setObjectName("informationBrowser")
        browser.setOpenExternalLinks(True)
        manual = resource_path("resources", "USER_MANUAL.md").read_text(encoding="utf-8")
        browser.setMarkdown(manual)
        browser.document().setDocumentMargin(24)
        return browser

    def _provider_changed(self) -> None:
        provider = Provider(str(self.provider_combo.currentData()))
        self.api_key.setText(self.credentials.get(provider.value) or "")
        self.endpoint.setEnabled(provider in {Provider.OLLAMA, Provider.CUSTOM_COMPATIBLE})
        if provider is Provider.OLLAMA and not self.endpoint.text():
            self.endpoint.setText("http://localhost:11434")
        self._provider_adapter = None
        self.model_combo.clear()
        self.model_combo.addItem("Connect provider to load models")
        self.refresh_sentence_state()

    def connect_provider(self) -> None:
        provider = Provider(str(self.provider_combo.currentData()))
        adapter = create_provider(
            provider, api_key=self.api_key.text().strip(), base_url=self.endpoint.text().strip()
        )
        self.model_combo.clear()
        self.model_combo.addItem("Connecting…")

        def success(models: Any) -> None:
            if not models:
                self._show_error("Connection succeeded, but no usable models were returned.")
                return
            self._provider_adapter = adapter
            self.credentials.set(
                provider.value, self.api_key.text().strip(), remember=self.remember_key.isChecked()
            )
            self.model_combo.clear()
            for model in models:
                self.model_combo.addItem(model.display_name, model.id)
            self.refresh_sentence_state()

        self._start_task(adapter.list_models, success)

    def show_provider_help(self) -> None:
        QMessageBox.information(
            self,
            "Provider setup",
            "Choose OpenAI, Anthropic, Google Gemini, DeepSeek, Ollama, or a custom OpenAI-compatible endpoint. "
            f"Cloud providers require your own API key. Remembered keys use {secure_store_name()}.\n\n"
            "No cloud key? Install Ollama, run ‘ollama pull qwen3:8b’, keep http://localhost:11434, and test the connection.",
        )

    def _selected_levels(self) -> list[CefrLevel]:
        levels = list(CefrLevel)
        start, end = (
            levels.index(CefrLevel(str(self.start_cefr.currentData()))),
            levels.index(CefrLevel(str(self.end_cefr.currentData()))),
        )
        return levels[start : end + 1] if start <= end else []

    def _reset_percentages(self) -> None:
        selected = self._selected_levels()
        for spin in self.cefr_percentages.values():
            spin.blockSignals(True)
            spin.setValue(0)
            spin.blockSignals(False)
        if selected:
            quotient, remainder = divmod(100, len(selected))
            for index, level in enumerate(selected):
                self.cefr_percentages[level].setValue(quotient + (index < remainder))
        self.refresh_sentence_state()

    def refresh_sentence_state(self) -> None:
        learning = Language(str(self.learning.currentData()))
        translation = Language(str(self.translation.currentData()))
        available = self.frequency_repository.available_count(learning, translation)
        form_multiplier = 1 + int(self.extra_forms.currentText())
        allowed = min(5_000 // form_multiplier, available)
        self.base_count.setMaximum(max(1, allowed))
        dataset_label = (
            "Production dataset" if self.frequency_is_production else "Demonstration dataset"
        )
        self.frequency_status.setText(
            f"{dataset_label}: {available:,} ranked {learning.label} words. Examples will be AI "
            f"generated in {learning.label} and translated into {translation.label}. Missing word "
            f"translations will also be AI generated in {translation.label}."
        )
        base = self.base_count.value()
        self.extra_forms.setEnabled(True)
        total = base * form_multiplier
        self.final_rows.setText(
            f"{total:,} final rows (base limit {allowed:,} at {form_multiplier}×; maximum 5,000)"
        )
        self.pronoun_explanation.setText(
            PRONOUN_SCALE_EXPLANATIONS[int(self.pronouns.currentText())]
        )
        gradual = CefrMode(str(self.cefr_mode.currentData())) is CefrMode.GRADUAL
        self.single_cefr.setEnabled(not gradual)
        self.start_cefr.setEnabled(gradual)
        self.end_cefr.setEnabled(gradual)
        selected = self._selected_levels() if gradual else []
        for level, spin in self.cefr_percentages.items():
            spin.setEnabled(gradual and level in selected)
        total_percent = sum(self.cefr_percentages[level].value() for level in selected)
        self.cefr_total.setText(f"{total_percent}%" if gradual else "Single-level mode")
        valid = (
            available > 0
            and base <= available
            and total <= 5_000
            and self.learning.currentData() != self.translation.currentData()
        )
        valid = valid and (not gradual or total_percent == 100)
        valid = (
            valid and self._provider_adapter is not None and bool(self.model_combo.currentData())
        )
        self.generate_button.setEnabled(valid)
        self.refresh_costs()

    def _settings(self) -> GenerationSettings:
        mode = CefrMode(str(self.cefr_mode.currentData()))
        cefr = (
            CefrSelection(
                mode=mode,
                single_level=CefrLevel(str(self.single_cefr.currentData())),
            )
            if mode is CefrMode.SINGLE
            else CefrSelection(
                mode=mode,
                start_level=CefrLevel(str(self.start_cefr.currentData())),
                end_level=CefrLevel(str(self.end_cefr.currentData())),
                percentages={
                    level: Decimal(self.cefr_percentages[level].value())
                    for level in self._selected_levels()
                },
            )
        )
        return GenerationSettings(
            learning_language=Language(str(self.learning.currentData())),
            translation_language=Language(str(self.translation.currentData())),
            base_sentences=self.base_count.value(),
            extra_forms=int(self.extra_forms.currentText()),
            question_percentage=Decimal(self.question_slider.value()),
            pronoun_change=int(self.pronouns.currentText()),
            cefr=cefr,
            seed=random.SystemRandom().randrange(1, 2**31),
        )

    def generate_workbook(self) -> None:
        candidate, model, provider = (
            self._settings(),
            str(self.model_combo.currentData()),
            self._provider_adapter,
        )
        output = Path(self.output_path.text()).expanduser().with_suffix(".xlsx")
        saved_resume = self._generation_resume
        if (
            saved_resume is not None
            and saved_resume[2] == output
            and saved_resume[3] == provider.provider_name
            and saved_resume[4] == model
            and saved_resume[0].model_dump(exclude={"seed"})
            == candidate.model_dump(exclude={"seed"})
        ):
            settings, checkpoint = saved_resume[0], saved_resume[1]
        else:
            settings = candidate
            checkpoint = self.paths.cache / "generation" / f"{uuid.uuid4().hex}.json"
            self._generation_resume = (settings, checkpoint, output, provider.provider_name, model)
        self.generate_button.setEnabled(False)
        self.generation_progress.setValue(0)

        async def task(report: Any) -> Path:
            words = self.frequency_repository.select(
                settings.learning_language, settings.translation_language, settings.base_sentences
            )
            plan = build_generation_plan(settings, words)
            result = await GenerationService(provider).generate(
                settings=settings,
                plan=plan,
                model=model,
                checkpoint_path=checkpoint,
                progress=report,
            )
            pricing = PricingRegistry.from_json(
                resource_path("resources", "pricing", "registry.json")
            )
            estimated = pricing.estimate(provider.provider_name, model, len(plan)).usd
            actual = pricing.actual_from_usage(
                provider.provider_name,
                model,
                result.input_tokens,
                result.output_tokens,
            )
            export_xlsx(
                output,
                result.completed_rows,
                plan,
                settings,
                provider=provider.provider_name,
                model=model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost_usd="Unknown" if estimated is None else str(estimated),
                actual_cost_usd="Unknown" if actual is None else str(actual),
            )
            saved = settings.model_dump(mode="json") | {
                "provider": provider.provider_name,
                "model": model,
            }
            self.history.add(output, "workbook", settings=saved)
            return output

        def success(path: Path) -> None:
            self._generation_resume = None
            self.generate_button.setEnabled(True)
            self.generation_progress.setValue(100)
            self.refresh_history()
            QMessageBox.information(self, "Workbook complete", f"Created:\n{path}")

        def failure(message: str) -> None:
            self.generate_button.setEnabled(True)
            self._show_error(message)

        self._start_task(
            task,
            success,
            failure,
            lambda done, total: self.generation_progress.setValue(round(done * 100 / total)),
        )

    def refresh_costs(self) -> None:
        model = self.model_combo.currentData()
        provider_data = self.provider_combo.currentData()
        if not model or not provider_data:
            self.cost_label.setText("Choose a connected model to see estimates.")
            return
        provider = Provider(str(provider_data))
        try:
            registry = PricingRegistry.from_json(
                resource_path("resources", "pricing", "registry.json")
            )
            lines = []
            counts = [1_000, 2_000, 3_000, 4_000, 5_000]
            current = self.base_count.value() * (1 + int(self.extra_forms.currentText()))
            if current not in counts:
                counts.append(current)
            for count in counts:
                estimate = registry.estimate(provider.value, str(model), count)
                display = "Unknown" if estimate.usd is None else f"${estimate.usd}"
                prefix = "Current" if count == current else f"{count:,} rows"
                lines.append(f"{prefix}: {display}")
            self.cost_label.setText(
                "  •  ".join(lines) + "\nEstimates only; provider billing is authoritative."
            )
        except Exception:
            self.cost_label.setText(
                "Pricing unknown for this model. Check the provider before generating."
            )

    def choose_generation_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save workbook", self.output_path.text(), "Excel workbook (*.xlsx)"
        )
        if path:
            self.output_path.setText(path)

    def _choose_workbook_from_history(self, title: str) -> Path | None:
        items = [item for item in self.history.list("workbook") if item.path.is_file()]
        if not items:
            self._show_error("History does not contain an available workbook yet.")
            return None
        labels = [f"{item.display_name}  —  {item.created_at}" for item in items]
        selected, accepted = QInputDialog.getItem(self, title, "Workbook", labels, 0, False)
        if not accepted:
            return None
        return items[labels.index(selected)].path

    def choose_flashcard_history(self) -> None:
        path = self._choose_workbook_from_history("Load flashcards from History")
        if path is not None:
            try:
                self._load_flashcard_workbook(path)
            except Exception as error:
                self._show_error(str(error))

    def choose_flashcard_workbook(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load flashcard workbook", str(Path.home()), "Excel workbook (*.xlsx)"
        )
        if path:
            try:
                self._load_flashcard_workbook(Path(path))
            except Exception as error:
                self._show_error(str(error))

    def _load_flashcard_workbook(self, path: Path) -> None:
        source_id, row_count = self.flashcard_service.import_workbook(path)
        self._flashcard_languages = import_language_pair(path) or (
            Language.EUROPEAN_SPANISH,
            Language.US_ENGLISH,
        )
        self._flashcard_source_id = source_id
        self._flashcard_row_count = row_count
        self.flashcard_workbook.setText(str(path.expanduser().resolve()))
        self.flashcard_selected_rows.setChecked(False)
        self.flashcard_from_rank.clear()
        self.flashcard_to_rank.clear()
        self.flashcard_source_status.setText(
            f"Loaded {row_count:,} ranked data rows. The first row below the header is rank 1."
        )
        self._start_flashcard_session(1, row_count)

    def _resume_flashcards(self) -> None:
        try:
            session = self.flashcard_service.resume()
        except Exception:
            return
        if session is None:
            return
        self._flashcard_session = session
        self._flashcard_source_id = session.source_id
        self._flashcard_row_count = session.source_row_count
        self._flashcard_languages = import_language_pair(Path(session.source_path)) or (
            Language.EUROPEAN_SPANISH,
            Language.US_ENGLISH,
        )
        self.flashcard_workbook.setText(session.source_path)
        self.flashcard_mode.blockSignals(True)
        self.flashcard_mode.setCurrentIndex(self.flashcard_mode.findData(session.mode))
        self.flashcard_mode.blockSignals(False)
        restricted = session.from_rank != 1 or session.to_rank != session.source_row_count
        self.flashcard_selected_rows.blockSignals(True)
        self.flashcard_selected_rows.setChecked(restricted)
        self.flashcard_selected_rows.blockSignals(False)
        self.flashcard_from_rank.setEnabled(restricted)
        self.flashcard_to_rank.setEnabled(restricted)
        self.flashcard_apply_range.setEnabled(restricted)
        if restricted:
            self.flashcard_from_rank.setText(str(session.from_rank))
            self.flashcard_to_rank.setText(str(session.to_rank))
        self.flashcard_source_status.setText(
            f"Restored {session.source_name}: {session.source_row_count:,} ranked data rows."
        )
        self._display_flashcard()

    def _flashcard_mode_changed(self) -> None:
        if self._flashcard_source_id is None:
            return
        rank_range = self._current_flashcard_range(show_errors=False)
        if rank_range is not None:
            self._start_flashcard_session(*rank_range)

    def _flashcard_range_toggled(self, selected_only: bool) -> None:
        self.flashcard_from_rank.setEnabled(selected_only)
        self.flashcard_to_rank.setEnabled(selected_only)
        self.flashcard_apply_range.setEnabled(
            selected_only and self._flashcard_source_id is not None
        )
        if selected_only:
            self.flashcard_from_rank.clear()
            self.flashcard_to_rank.clear()
            self.flashcard_source_status.setText(
                "Enter an inclusive From rank and To rank, then apply the selection."
            )
        elif self._flashcard_source_id is not None:
            self._start_flashcard_session(1, self._flashcard_row_count)

    def _current_flashcard_range(self, *, show_errors: bool) -> tuple[int, int] | None:
        if self._flashcard_source_id is None:
            if show_errors:
                self._show_error("Load a compatible .xlsx workbook first.")
            return None
        if not self.flashcard_selected_rows.isChecked():
            return 1, self._flashcard_row_count
        if not self.flashcard_from_rank.text() or not self.flashcard_to_rank.text():
            if show_errors:
                self._show_error("Enter both the From rank and To rank.")
            return None
        from_rank = int(self.flashcard_from_rank.text())
        to_rank = int(self.flashcard_to_rank.text())
        if not 1 <= from_rank <= to_rank <= self._flashcard_row_count:
            if show_errors:
                self._show_error(
                    f"Choose an inclusive range from 1 to {self._flashcard_row_count:,}."
                )
            return None
        return from_rank, to_rank

    def _apply_flashcard_range(self) -> None:
        rank_range = self._current_flashcard_range(show_errors=True)
        if rank_range is not None:
            self._start_flashcard_session(*rank_range)

    def _start_flashcard_session(self, from_rank: int, to_rank: int) -> None:
        assert self._flashcard_source_id is not None
        mode = FlashcardMode(str(self.flashcard_mode.currentData()))
        self._flashcard_session = self.flashcard_service.start_session(
            self._flashcard_source_id, mode, from_rank, to_rank
        )
        self.flashcard_source_status.setText(
            f"Studying ranks {from_rank:,}–{to_rank:,}. Cards will not repeat before this shuffled selection is exhausted."
        )
        self._display_flashcard()

    def _display_flashcard(self) -> None:
        session = self._flashcard_session
        if session is None:
            return
        self._flashcard_player.stop()
        row = session.current_row
        back = session.showing_back
        mode = session.mode
        word = row.word_translation if back else row.foreign_word
        sentence = row.sentence_translation if back else row.foreign_sentence
        self.flashcard_word.setText(
            word if mode in {FlashcardMode.WORDS, FlashcardMode.BOTH} else ""
        )
        self.flashcard_sentence.setText(
            sentence if mode in {FlashcardMode.SENTENCES, FlashcardMode.BOTH} else ""
        )
        self.flashcard_word.setVisible(mode in {FlashcardMode.WORDS, FlashcardMode.BOTH})
        self.flashcard_sentence.setVisible(mode in {FlashcardMode.SENTENCES, FlashcardMode.BOTH})
        self.flashcard_progress.setText(
            f"Workbook rank {session.current_rank:,}  •  Card {session.position + 1:,} of "
            f"{len(session.order):,}  •  {'Back' if back else 'Front'}"
        )
        learning, translation = self._flashcard_languages
        self.flashcard_language.setText(
            f"{LANGUAGE_BADGES[learning]}  →  {LANGUAGE_BADGES[translation]}"
        )
        self.flashcard_progress_bar.setRange(0, len(session.order))
        self.flashcard_progress_bar.setValue(session.position + 1)
        self.flashcard_previous.setEnabled(session.can_previous)
        self.flashcard_next.setEnabled(session.can_next)
        self.flashcard_flip.setEnabled(True)
        self.flashcard_shuffle.setEnabled(True)
        self.flashcard_sound.setEnabled(True)
        self.flashcard_flip.setText("Show learning side" if back else "Reveal")

    def previous_flashcard(self) -> None:
        if self._flashcard_session and self._flashcard_session.previous():
            self.flashcard_service.save(self._flashcard_session)
            self._display_flashcard()

    def next_flashcard(self) -> None:
        if self._flashcard_session and self._flashcard_session.next():
            self.flashcard_service.save(self._flashcard_session)
            self._display_flashcard()

    def flip_flashcard(self) -> None:
        if self._flashcard_session is None:
            return
        self._flashcard_session.flip()
        self.flashcard_service.save(self._flashcard_session)
        self._display_flashcard()

    def shuffle_flashcards(self) -> None:
        if self._flashcard_session is None:
            return
        self._flashcard_session.shuffle_again()
        self.flashcard_service.save(self._flashcard_session)
        self._display_flashcard()

    def play_flashcard_audio(self) -> None:
        session = self._flashcard_session
        if session is None:
            return
        row = session.current_row
        back = session.showing_back
        mode = session.mode
        if back:
            language = self._flashcard_languages[1]
            values = ((2, row.word_translation), (4, row.sentence_translation))
        else:
            language = self._flashcard_languages[0]
            values = ((1, row.foreign_word), (3, row.foreign_sentence))
        cells: tuple[tuple[int, str], ...]
        if mode is FlashcardMode.WORDS:
            cells = (values[0],)
        elif mode is FlashcardMode.SENTENCES:
            cells = (values[1],)
        else:
            cells = values
        voice = VoiceSettings(language=language, voice=VOICE_DEFAULTS[language][0])
        self.flashcard_sound.setEnabled(False)
        self.flashcard_sound.setText("…")

        async def task() -> Path:
            return await self._flashcard_audio.prepare_playback(
                Path(session.source_path), session.current_rank, cells, voice
            )

        def success(path: Path) -> None:
            self.flashcard_sound.setText("🔊")
            self.flashcard_sound.setEnabled(True)
            try:
                self._flashcard_player.play(path)
            except Exception as error:
                failure(str(error))

        def failure(message: str) -> None:
            self.flashcard_sound.setText("🔊")
            self.flashcard_sound.setEnabled(True)
            self._show_error(message)

        self._start_task(task, success, failure)

    def choose_tts_history(self) -> None:
        path = self._choose_workbook_from_history("Load TTS workbook from History")
        if path is not None:
            try:
                import_xlsx(path)
                self.tts_workbook.setText(str(path))
            except Exception as error:
                self._show_error(str(error))

    def choose_tts_workbook(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose workbook", str(Path.home()), "Excel workbook (*.xlsx)"
        )
        if path:
            try:
                import_xlsx(Path(path))
                self.tts_workbook.setText(path)
            except Exception as error:
                self._show_error(str(error))

    def _tts_settings(self) -> TtsSettings:
        return TtsSettings(
            foreign=VoiceSettings(
                language=self.foreign_language.currentData(),
                voice=self.foreign_voice.currentText(),
                rate=self.foreign_rate.value(),
                pitch_hz=self.foreign_pitch.value(),
                volume=self.foreign_volume.value(),
            ),
            translation=VoiceSettings(
                language=self.translation_language.currentData(),
                voice=self.translation_voice.currentText(),
                rate=self.translation_rate.value(),
                pitch_hz=self.translation_pitch.value(),
                volume=self.translation_volume.value(),
            ),
            pause_after_foreign_verb=self.pause_sliders[0].value(),
            pause_after_verb_translation=self.pause_sliders[1].value(),
            pause_after_foreign_sentence=self.pause_sliders[2].value(),
            pause_after_sentence_translation=self.pause_sliders[3].value(),
        )

    def _backend(self) -> EdgeFfmpegBackend:
        bundled = resource_path("installer", "bundled", "ffmpeg")
        suffix = ".exe" if sys.platform == "win32" else ""
        ffmpeg, ffprobe = bundled / f"ffmpeg{suffix}", bundled / f"ffprobe{suffix}"
        return EdgeFfmpegBackend(
            str(ffmpeg) if ffmpeg.exists() else "ffmpeg",
            str(ffprobe) if ffprobe.exists() else "ffprobe",
        )

    def preview_tts(self) -> None:
        workbook = Path(self.tts_workbook.text())
        if not workbook.is_file():
            self._show_error("Choose a valid .xlsx workbook first.")
            return
        output = self.paths.cache / "tts" / "preview.mp3"
        service = TtsService(self._backend())
        self._start_task(
            lambda: service.preview(workbook, self._tts_settings(), output),
            lambda path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))),
        )

    def pause_tts(self) -> None:
        if self._tts_service is not None:
            self._tts_service.pause()

    def resume_tts(self) -> None:
        if self._tts_service is not None:
            self._tts_service.resume()

    def cancel_tts(self) -> None:
        if self._tts_service is not None:
            self._tts_service.cancel()

    def generate_tts(self) -> None:
        workbook = Path(self.tts_workbook.text())
        if not workbook.is_file():
            self._show_error("Choose a valid .xlsx workbook first.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self, "Save MP3", str(Path.home() / "Documents" / f"{workbook.stem}.mp3"), "MP3 (*.mp3)"
        )
        if not output:
            return
        output_path, settings = Path(output).with_suffix(".mp3"), self._tts_settings()
        job_key = f"{file_checksum(workbook)[:12]}-{settings_checksum(settings)[:12]}"
        job = self.paths.cache / "tts" / "jobs" / job_key
        self._tts_service = TtsService(self._backend())
        self.tts_progress.setValue(0)

        async def task(report: Any) -> Any:
            assert self._tts_service is not None
            return await self._tts_service.generate(
                workbook,
                settings,
                job,
                output_path,
                progress=report,
            )

        def success(manifest: Any) -> None:
            if manifest.state == "complete":
                self.history.add(output_path, "audio", settings=settings.model_dump(mode="json"))
                self.tts_progress.setValue(100)
                self.refresh_history()
                QMessageBox.information(self, "Audio complete", f"Created:\n{output_path}")
            else:
                if manifest.partial_mp3 and Path(manifest.partial_mp3).is_file():
                    self.history.add(
                        Path(manifest.partial_mp3),
                        "audio",
                        settings=settings.model_dump(mode="json"),
                        status=manifest.state,
                    )
                    self.refresh_history()
                QMessageBox.warning(
                    self,
                    "Audio incomplete",
                    f"State: {manifest.state}\n"
                    f"Last completed row: {len(manifest.completed_rows)}\n"
                    "The partial MP3 is available in History for export. Run Create MP3 "
                    "again with the same workbook and settings to continue safely.",
                )

        self._start_task(
            task,
            success,
            progress=lambda done, total: self.tts_progress.setValue(round(done * 100 / total)),
        )

    def refresh_history(self) -> None:
        if not hasattr(self, "history_table"):
            return
        items = self.history.list()
        self.history_table.setRowCount(len(items))
        for row, item in enumerate(items):
            for column, value in enumerate(
                (item.display_name, item.file_type, item.created_at, item.status, str(item.path))
            ):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item.id)
                self.history_table.setItem(row, column, cell)

    def _selected_history(self) -> HistoryItem | None:
        row = self.history_table.currentRow()
        if row < 0:
            self._show_error("Select one History row first.")
            return None
        cell = self.history_table.item(row, 0)
        if cell is None:
            self._show_error("The selected History row is invalid.")
            return None
        return self.history.get(int(cell.data(Qt.ItemDataRole.UserRole)))

    def history_to_tts(self) -> None:
        item = self._selected_history()
        if item and item.file_type == "workbook":
            self.tts_workbook.setText(str(item.path))
            self.tabs.setCurrentIndex(2)
        elif item:
            self._show_error("Select a workbook History item.")

    def history_to_flashcards(self) -> None:
        item = self._selected_history()
        if item and item.file_type == "workbook":
            try:
                self._load_flashcard_workbook(item.path)
                self.tabs.setCurrentIndex(1)
            except Exception as error:
                self._show_error(str(error))
        elif item:
            self._show_error("Select a workbook History item.")

    def rename_history(self) -> None:
        item = self._selected_history()
        if not item:
            return
        from PySide6.QtWidgets import QInputDialog

        name, accepted = QInputDialog.getText(
            self, "Rename History item", "New file name", text=item.display_name
        )
        if accepted:
            try:
                self.history.rename(item.id, name)
                self.refresh_history()
            except Exception as error:
                self._show_error(str(error))

    def delete_history(self) -> None:
        item = self._selected_history()
        if (
            item
            and QMessageBox.question(
                self,
                f"Move to {trash_name()}",
                f"Move this app-owned file to the {trash_name()}?\n{item.display_name}",
            )
            == QMessageBox.StandardButton.Yes
        ):
            try:
                self.history.delete(item.id)
                self.refresh_history()
            except Exception as error:
                self._show_error(str(error))

    def export_history(self) -> None:
        item = self._selected_history()
        if not item:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Export copy", item.display_name)
        if destination:
            try:
                self.history.export(item.id, Path(destination))
            except Exception as error:
                self._show_error(str(error))

    def regenerate_history(self) -> None:
        item = self._selected_history()
        if not item:
            return
        try:
            raw = self.history.regeneration_settings(item.id)
            settings = GenerationSettings.model_validate(raw)
            self.learning.setCurrentIndex(self.learning.findData(settings.learning_language))
            self.translation.setCurrentIndex(
                self.translation.findData(settings.translation_language)
            )
            self.base_count.setValue(settings.base_sentences)
            self.extra_forms.setCurrentText(str(settings.extra_forms))
            self.question_slider.setValue(int(settings.question_percentage))
            self.pronouns.setCurrentText(str(settings.pronoun_change))
            self.cefr_mode.setCurrentIndex(self.cefr_mode.findData(settings.cefr.mode))
            if settings.cefr.mode is CefrMode.SINGLE:
                self.single_cefr.setCurrentIndex(
                    self.single_cefr.findData(settings.cefr.single_level)
                )
            else:
                self.start_cefr.setCurrentIndex(self.start_cefr.findData(settings.cefr.start_level))
                self.end_cefr.setCurrentIndex(self.end_cefr.findData(settings.cefr.end_level))
                for level, value in settings.cefr.percentages.items():
                    self.cefr_percentages[level].setValue(int(value))
            provider_index = self.provider_combo.findText(str(raw.get("provider", "")))
            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
            self.output_path.setText(
                str(Path.home() / "Documents" / f"{item.path.stem} Regenerated.xlsx")
            )
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(
                self,
                "Settings restored",
                "The original is unchanged. Settings were restored with a new random seed; connect the provider and generate a new file.",
            )
        except Exception as error:
            self._show_error(f"This item cannot be regenerated: {error}")

    def _refresh_voices(self) -> None:
        if not hasattr(self, "foreign_voice"):
            return
        for language_combo, voice_combo in (
            (self.foreign_language, self.foreign_voice),
            (self.translation_language, self.translation_voice),
        ):
            voice_combo.clear()
            language = Language(str(language_combo.currentData()))
            voice_combo.addItems(VOICE_DEFAULTS[language])

    def refresh_edge_voices(self) -> None:
        foreign = Language(str(self.foreign_language.currentData()))
        translation = Language(str(self.translation_language.currentData()))

        async def task() -> tuple[list[str], list[str]]:
            return (
                await list_edge_voices(foreign.speech_locale),
                await list_edge_voices(translation.speech_locale),
            )

        def success(voices: tuple[list[str], list[str]]) -> None:
            for combo, available in zip(
                (self.foreign_voice, self.translation_voice), voices, strict=True
            ):
                if available:
                    combo.clear()
                    combo.addItems(available)

        self._start_task(task, success)

    @staticmethod
    def _language_combo() -> QComboBox:
        combo = QComboBox()
        for language in Language:
            combo.addItem(language.label, language)
        return combo

    @staticmethod
    def _scroll(content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _signed_spin(suffix: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(-100, 100)
        spin.setSuffix(suffix)
        return spin

    @staticmethod
    def _labelled_slider(
        minimum: int, maximum: int, value: int, suffix: str
    ) -> tuple[QSlider, QWidget]:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        label = QLabel(f"{value}{suffix}")
        slider.valueChanged.connect(lambda new: label.setText(f"{new}{suffix}"))
        row.addWidget(slider)
        row.addWidget(label)
        return slider, widget

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Easy Language Learning Tool", message)
