from __future__ import annotations

import random
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from easy_language_learning_tool.config.paths import AppPaths, resolve_app_paths
from easy_language_learning_tool.domain.enums import CefrLevel, CefrMode, Language, Provider
from easy_language_learning_tool.domain.frequency import FrequencyRepository
from easy_language_learning_tool.domain.models import CefrSelection, GenerationSettings
from easy_language_learning_tool.domain.planner import build_generation_plan
from easy_language_learning_tool.generation.service import GenerationService
from easy_language_learning_tool.history.service import HistoryItem, HistoryService
from easy_language_learning_tool.providers.factory import create_provider
from easy_language_learning_tool.providers.pricing import PricingRegistry
from easy_language_learning_tool.security.credentials import CredentialStore
from easy_language_learning_tool.tts.manifest import file_checksum, settings_checksum
from easy_language_learning_tool.tts.models import TtsSettings, VoiceSettings
from easy_language_learning_tool.tts.service import EdgeFfmpegBackend, TtsService, list_edge_voices
from easy_language_learning_tool.workbook.service import export_xlsx, import_xlsx

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
"""

VOICE_DEFAULTS: dict[Language, tuple[str, str]] = {
    Language.US_ENGLISH: ("en-US-JennyNeural", "en-US-GuyNeural"),
    Language.EUROPEAN_SPANISH: ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
    Language.GERMAN: ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
    Language.EUROPEAN_PORTUGUESE: ("pt-PT-RaquelNeural", "pt-PT-DuarteNeural"),
    Language.FRENCH: ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
}


def resource_path(*parts: str) -> Path:
    packaged = Path(sys.argv[0]).resolve().parent
    if packaged.joinpath(parts[0]).exists():
        return packaged.joinpath(*parts)
    return Path(__file__).resolve().parents[3].joinpath(*parts)


class MainWindow(QMainWindow):
    def __init__(self, paths: AppPaths | None = None) -> None:
        super().__init__()
        self.paths = paths or resolve_app_paths()
        self.paths.create()
        self.credentials = CredentialStore()
        self.history = HistoryService(
            self.paths.data / "easy_language_learning_tool.sqlite3", self.paths.history
        )
        self._threads: set[TaskThread] = set()
        self._provider_adapter: Any = None
        self._tts_service: TtsService | None = None
        self._generation_resume: tuple[GenerationSettings, Path, Path, str, str] | None = None
        self.setWindowTitle("Easy Language Learning Tool")
        self.setWindowIcon(QIcon(str(resource_path("assets", "icons", "logo.svg"))))
        self.setMinimumSize(720, 405)
        view = self.menuBar().addMenu("View")
        theme = QAction("Use dark theme", self, checkable=True)
        theme.toggled.connect(lambda on: self.setStyleSheet(DARK_THEME if on else LIGHT_THEME))
        view.addAction(theme)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._sentence_tab(), "Sentence Creation")
        self.tabs.addTab(self._tts_tab(), "TTS")
        self.tabs.addTab(self._history_tab(), "History")
        self.setCentralWidget(self.tabs)
        self.setStyleSheet(LIGHT_THEME)
        self.refresh_history()

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
        root = QWidget()
        layout = QVBoxLayout(root)
        provider_group = QGroupBox("AI provider")
        provider_form = QFormLayout(provider_group)
        self.provider_combo = QComboBox()
        for provider in Provider:
            self.provider_combo.addItem(provider.value, provider)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Not required for Ollama")
        self.remember_key = QCheckBox("Remember securely in Windows Credential Manager")
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
        self.learning = self._language_combo()
        self.translation = self._language_combo()
        self.translation.setCurrentIndex(1)
        self.base_count = QSpinBox()
        self.base_count.setRange(1, 4_000)
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
        self.pronouns.addItems([str(value) for value in range(1, 6)])
        self.final_rows = QLabel()
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
            ("Base sentences", self.base_count),
            ("Extra forms (0–4)", self.extra_forms),
            ("CEFR mode", self.cefr_mode),
            ("Single level", self.single_cefr),
            ("Gradual range", range_widget),
            ("Level percentages", percentages),
            ("Percentage total", self.cefr_total),
            ("Questions / statements", question_row),
            ("Pronoun-change scale", self.pronouns),
            ("Calculated output", self.final_rows),
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

    def _tts_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        source_group = QGroupBox("Workbook input")
        source_form = QFormLayout(source_group)
        self.tts_workbook = QLineEdit()
        browse = QPushButton("Browse desktop…")
        browse.clicked.connect(self.choose_tts_workbook)
        source_widget = QWidget()
        source_row = QHBoxLayout(source_widget)
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.tts_workbook)
        source_row.addWidget(browse)
        source_form.addRow("Four-column .xlsx", source_widget)

        voices = QGroupBox("Languages and natural Edge voices")
        voice_form = QFormLayout(voices)
        self.foreign_language, self.translation_language = (
            self._language_combo(),
            self._language_combo(),
        )
        self.translation_language.setCurrentIndex(1)
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
            "Foreign verb → verb translation",
            "Verb translation → foreign sentence",
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
        root = QWidget()
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
            ("Use in TTS", self.history_to_tts),
            ("Rename", self.rename_history),
            ("Delete to Recycle Bin", self.delete_history),
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

    def _provider_changed(self) -> None:
        provider: Provider = self.provider_combo.currentData()
        self.api_key.setText(self.credentials.get(provider.value) or "")
        self.endpoint.setEnabled(provider in {Provider.OLLAMA, Provider.CUSTOM_COMPATIBLE})
        if provider is Provider.OLLAMA and not self.endpoint.text():
            self.endpoint.setText("http://localhost:11434")
        self._provider_adapter = None
        self.model_combo.clear()
        self.model_combo.addItem("Connect provider to load models")
        self.refresh_sentence_state()

    def connect_provider(self) -> None:
        provider: Provider = self.provider_combo.currentData()
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
            "Cloud providers require your own API key. Remembered keys use Windows Credential Manager.\n\n"
            "No cloud key? Install Ollama, run ‘ollama pull qwen3:8b’, keep http://localhost:11434, and test the connection.",
        )

    def _selected_levels(self) -> list[CefrLevel]:
        levels = list(CefrLevel)
        start, end = (
            levels.index(self.start_cefr.currentData()),
            levels.index(self.end_cefr.currentData()),
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
        base = self.base_count.value()
        self.extra_forms.setEnabled(base <= 1_000)
        if base > 1_000:
            self.extra_forms.setCurrentIndex(0)
        total = base * (1 + int(self.extra_forms.currentText()))
        self.final_rows.setText(f"{total:,} final rows (maximum 5,000)")
        gradual = self.cefr_mode.currentData() is CefrMode.GRADUAL
        self.single_cefr.setEnabled(not gradual)
        self.start_cefr.setEnabled(gradual)
        self.end_cefr.setEnabled(gradual)
        selected = self._selected_levels() if gradual else []
        for level, spin in self.cefr_percentages.items():
            spin.setEnabled(gradual and level in selected)
        total_percent = sum(self.cefr_percentages[level].value() for level in selected)
        self.cefr_total.setText(f"{total_percent}%" if gradual else "Single-level mode")
        valid = total <= 5_000 and self.learning.currentData() != self.translation.currentData()
        valid = valid and (not gradual or total_percent == 100)
        valid = (
            valid and self._provider_adapter is not None and bool(self.model_combo.currentData())
        )
        self.generate_button.setEnabled(valid)
        self.refresh_costs()

    def _settings(self) -> GenerationSettings:
        mode: CefrMode = self.cefr_mode.currentData()
        cefr = (
            CefrSelection(mode=mode, single_level=self.single_cefr.currentData())
            if mode is CefrMode.SINGLE
            else CefrSelection(
                mode=mode,
                start_level=self.start_cefr.currentData(),
                end_level=self.end_cefr.currentData(),
                percentages={
                    level: Decimal(self.cefr_percentages[level].value())
                    for level in self._selected_levels()
                },
            )
        )
        return GenerationSettings(
            learning_language=self.learning.currentData(),
            translation_language=self.translation.currentData(),
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
            repository = FrequencyRepository.from_jsonl(
                resource_path("resources", "frequency_data", "demo", "verbs.jsonl")
            )
            verbs = repository.select(
                settings.learning_language, settings.translation_language, settings.base_sentences
            )
            plan = build_generation_plan(settings, verbs)
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
        model, provider = self.model_combo.currentData(), self.provider_combo.currentData()
        if not model or not provider:
            self.cost_label.setText("Choose a connected model to see estimates.")
            return
        try:
            registry = PricingRegistry.from_json(
                resource_path("resources", "pricing", "registry.json")
            )
            lines = []
            counts = [1_000, 2_000, 3_000, 4_000]
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
        ffmpeg, ffprobe = bundled / "ffmpeg.exe", bundled / "ffprobe.exe"
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
            self.tabs.setCurrentIndex(1)
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
                "Move to Recycle Bin",
                f"Move this app-owned file to the Recycle Bin?\n{item.display_name}",
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
            voice_combo.addItems(VOICE_DEFAULTS[language_combo.currentData()])

    def refresh_edge_voices(self) -> None:
        foreign = self.foreign_language.currentData()
        translation = self.translation_language.currentData()

        async def task() -> tuple[list[str], list[str]]:
            return (
                await list_edge_voices(foreign.value),
                await list_edge_voices(translation.value),
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
