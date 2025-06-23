import sys
import os
import tempfile
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QHBoxLayout
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from gtts import gTTS
import pygame


class EnterKeyTextEdit(QTextEdit):
    def __init__(self, *args, on_enter_pressed=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_enter_pressed = on_enter_pressed

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+Enter inserts newline
                self.insertPlainText('\n')
            else:
                # Enter alone triggers speech
                if self.on_enter_pressed:
                    self.on_enter_pressed()
            return  # prevent default handling in both cases
        super().keyPressEvent(event)


class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._opacity = 1.0
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(600)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.3)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def start_animation(self):
        self.animation.start()

    def stop_animation(self):
        self.animation.stop()
        self.setStyleSheet(self.default_style())

    def default_style(self):
        return """
        QPushButton {
            background-color: #5a5a5a;
            color: #eee;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #888;
        }
        QPushButton:hover {
            background-color: #777;
        }
        """

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        # rgba white text with opacity, background changes opacity a bit
        bg_opacity = int(85 + (value * 100))  # from 85 to 185 approx
        self.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(90, 90, 90, {value});
            color: rgba(238, 238, 238, {value});
            padding: 10px;
            border-radius: 8px;
            border: 1px solid rgba(136,136,136,{value});
        }}
        QPushButton:hover {{
            background-color: rgba(119, 119, 119, {value});
        }}
        """)

    opacity = pyqtProperty(float, get_opacity, set_opacity)


class TextToSpeechApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("German TTS - Sprachtrainer 🇩🇪")
        self.setGeometry(300, 200, 520, 360)
        self.setWindowIcon(QIcon.fromTheme("audio-x-generic"))

        pygame.init()
        pygame.mixer.init()

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.label = QLabel("🗣️  Enter German text below:")
        self.label.setFont(QFont("Arial", 12, QFont.Bold))
        self.label.setStyleSheet("color: #eee;")
        layout.addWidget(self.label)

        self.text_edit = EnterKeyTextEdit(on_enter_pressed=self.text_to_speech)
        self.text_edit.setFont(QFont("Arial", 11))
        self.text_edit.setPlaceholderText("Zum Beispiel: Wie heißt du?")
        self.text_edit.setStyleSheet("""
            background-color: #333;
            color: #eee;
            border-radius: 8px;
            padding: 8px;
            border: 1px solid #555;
        """)
        layout.addWidget(self.text_edit)

        options_layout = QHBoxLayout()
        from PyQt5.QtWidgets import QCheckBox
        self.slow_checkbox = QCheckBox("🕓 Slow voice (0.7x speed)")
        self.slow_checkbox.setFont(QFont("Arial", 10))
        self.slow_checkbox.setChecked(True)  # default checked
        self.slow_checkbox.setStyleSheet("color: #ccc;")
        options_layout.addStretch()
        options_layout.addWidget(self.slow_checkbox)
        layout.addLayout(options_layout)

        self.button = AnimatedButton("▶ Speak")
        self.button.setFont(QFont("Arial", 11, QFont.Bold))
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.setStyleSheet(self.button.default_style())
        self.button.clicked.connect(self.text_to_speech)
        layout.addWidget(self.button, alignment=Qt.AlignCenter)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10, QFont.StyleItalic))
        self.status_label.setStyleSheet("color: #66ff66;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # Dark grey background (not pure black)
        self.setStyleSheet("background-color: #222222;")

    def text_to_speech(self):
        text = self.text_edit.toPlainText().strip()
        slow_checked = self.slow_checkbox.isChecked()

        if not text:
            return

        self.button.setDisabled(True)
        self.button.start_animation()
        self.status_label.setText("🔊 Speaking...")

        # gTTS only supports slow=True or False
        # We simulate speed by changing playback speed on pygame side.
        # gTTS speed options: slow=True ≈ 0.75x normal
        # If unchecked, normal speed.

        tts = gTTS(text=text, lang='de', slow=slow_checked)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name

        def done_speaking():
            self.button.setDisabled(False)
            self.button.stop_animation()
            self.status_label.setText("")

        try:
            tts.save(temp_path)
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            # Use pygame to get length and re-enable UI after done
            duration_ms = int(pygame.mixer.Sound(temp_path).get_length() * 1000)
            QTimer.singleShot(duration_ms, done_speaking)

        finally:
            # Delete temp file with delay to avoid premature deletion
            QTimer.singleShot(1500, lambda: os.remove(temp_path))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextToSpeechApp()
    window.show()
    sys.exit(app.exec_())
