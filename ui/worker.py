import traceback
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from core.pipeline import Pipeline, PipelineProgress, PipelineStep


class PipelineWorker(QThread):
    progress_updated = pyqtSignal(PipelineProgress)
    step_changed = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, config: dict, script_path: str, output_path: str):
        super().__init__()
        self.config = config
        self.script_path = script_path
        self.output_path = output_path
        self._pipeline: Pipeline | None = None

    def run(self):
        self._pipeline = Pipeline(self.config)
        try:
            result = self._pipeline.run(
                self.script_path,
                self.output_path,
                progress_callback=self._on_progress,
            )
            self.finished.emit(result)
        except Exception as e:
            logging.getLogger("worker").error(
                "管线执行异常:\n%s", traceback.format_exc()
            )
            self.error.emit(str(e))

    def cancel(self):
        if self._pipeline:
            self._pipeline.cancel()

    def _on_progress(self, progress: PipelineProgress):
        self.progress_updated.emit(progress)
        self.step_changed.emit(progress.message)


class BatchWorker(QThread):
    progress_updated = pyqtSignal(PipelineProgress)
    item_finished = pyqtSignal(str, bool, str)
    all_finished = pyqtSignal(list)

    def __init__(self, config: dict, script_paths: list[str], output_dir: str):
        super().__init__()
        self.config = config
        self.script_paths = script_paths
        self.output_dir = output_dir
        self._pipeline: Pipeline | None = None

    def run(self):
        self._pipeline = Pipeline(self.config)
        total = len(self.script_paths)
        results = []

        for i, script_path in enumerate(self.script_paths):
            import os
            from pathlib import Path
            script_name = Path(script_path).stem
            output_path = os.path.join(self.output_dir, f"{script_name}.mp4")

            try:
                result = self._pipeline.run(
                    script_path, output_path,
                    progress_callback=self._on_progress,
                )
                results.append((script_path, True, result))
                self.item_finished.emit(script_path, True, result)
            except Exception as e:
                results.append((script_path, False, str(e)))
                self.item_finished.emit(script_path, False, str(e))

            self.progress_updated.emit(PipelineProgress(
                PipelineStep.DONE, (i + 1) / total, f"进度 {i+1}/{total}"
            ))

        self.all_finished.emit(results)

    def cancel(self):
        if self._pipeline:
            self._pipeline.cancel()

    def _on_progress(self, progress: PipelineProgress):
        self.progress_updated.emit(progress)
