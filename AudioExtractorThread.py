import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QLabel, QWidget, QProgressBar,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from moviepy import VideoFileClip


class AudioExtractorThread(QThread):
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态消息
    finished_all = pyqtSignal()

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self._is_running = True

    def run(self):
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            if not self._is_running:
                break

            try:
                # 更新进度和当前文件状态
                self.progress_updated.emit(int((i / total_files) * 100),
                                           f"正在处理: {os.path.basename(file_path)}")

                # 构造输出路径
                output_path = os.path.splitext(file_path)[0] + ".mp3"

                # 提取音频
                video = VideoFileClip(file_path)
                video.audio.write_audiofile(output_path)
                video.close()

                self.progress_updated.emit(int((i + 1) / total_files) * 100,
                                               f"完成: {os.path.basename(file_path)}")
            except Exception as e:
                self.progress_updated.emit(int((i / total_files) * 100),
                                           f"错误: {os.path.basename(file_path)} - {str(e)}")

        self.finished_all.emit()

    def stop(self):
        self._is_running = False
        self.wait()


class VideoToAudioConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频转音频工具")
        self.setGeometry(100, 100, 600, 400)

        # 初始化UI
        self.init_ui()

        # 存储文件路径
        self.file_paths = []

        # 线程
        self.extractor_thread = None

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()

        # 标题
        title_label = QLabel("拖放视频文件到下方区域或点击添加按钮")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragEnabled(True)
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        main_layout.addWidget(self.file_list)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 添加文件按钮
        add_button = QPushButton("添加文件")
        add_button.clicked.connect(self.add_files)
        button_layout.addWidget(add_button)

        # 添加文件夹按钮
        add_folder_button = QPushButton("添加文件夹")
        add_folder_button.clicked.connect(self.add_folder)
        button_layout.addWidget(add_folder_button)

        # 移除按钮
        remove_button = QPushButton("移除选中")
        remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(remove_button)

        # 清空按钮
        clear_button = QPushButton("清空列表")
        clear_button.clicked.connect(self.clear_list)
        button_layout.addWidget(clear_button)

        main_layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # 转换按钮
        self.convert_button = QPushButton("开始转换")
        self.convert_button.clicked.connect(self.start_conversion)
        main_layout.addWidget(self.convert_button)

        # 设置中心窗口
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 允许拖放
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if self.is_video_file(file_path) and file_path not in self.file_paths:
                self.file_paths.append(file_path)
                self.file_list.addItem(os.path.basename(file_path))

    def is_video_file(self, file_path):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        return os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in video_extensions

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv);;所有文件 (*.*)")

        for file_path in files:
            if file_path not in self.file_paths:
                self.file_paths.append(file_path)
                self.file_list.addItem(os.path.basename(file_path))

    def add_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_video_file(file_path) and file_path not in self.file_paths:
                        self.file_paths.append(file_path)
                        self.file_list.addItem(os.path.basename(file_path))

    def remove_selected(self):
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            index = self.file_list.row(item)
            self.file_list.takeItem(index)
            del self.file_paths[index]

    def clear_list(self):
        self.file_list.clear()
        self.file_paths = []

    def start_conversion(self):
        if not self.file_paths:
            QMessageBox.warning(self, "警告", "没有可转换的文件!")
            return

        if self.extractor_thread and self.extractor_thread.isRunning():
            QMessageBox.warning(self, "警告", "转换正在进行中!")
            return

        # 创建并启动线程
        self.extractor_thread = AudioExtractorThread(self.file_paths)
        self.extractor_thread.progress_updated.connect(self.update_progress)
        self.extractor_thread.finished_all.connect(self.conversion_finished)
        self.extractor_thread.start()

        # 禁用转换按钮
        self.convert_button.setEnabled(False)

    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def conversion_finished(self):
        self.progress_bar.setValue(100)
        self.status_label.setText("所有文件转换完成!")
        self.convert_button.setEnabled(True)
        QMessageBox.information(self, "完成", "所有文件转换完成!")

    def closeEvent(self, event):
        if self.extractor_thread and self.extractor_thread.isRunning():
            self.extractor_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    converter = VideoToAudioConverter()
    converter.show()
    sys.exit(app.exec_())