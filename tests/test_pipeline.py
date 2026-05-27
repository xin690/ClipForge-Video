import pytest
import json
import os
from core.pipeline import Pipeline, PipelineError, PipelineStep, PipelineProgress


class TestPipelineInit:
    def test_init_defaults(self):
        pipe = Pipeline()
        assert pipe._cancelled is False

    def test_init_with_config(self):
        cfg = {"logging": {"level": "DEBUG"}}
        pipe = Pipeline(cfg)
        assert pipe._cancelled is False

    def test_cancel(self):
        pipe = Pipeline()
        assert pipe._cancelled is False
        pipe.cancel()
        assert pipe._cancelled is True


class TestPipelineValidation:
    def test_validate_valid_script(self, temp_dir):
        pipe = Pipeline()
        script_path = os.path.join(temp_dir, "valid.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": "测试", "duration": 10,
                "segments": [{"id": 1, "text": "测试", "duration": 5}]
            }, f)
        errors = pipe.validate_script(script_path)
        assert len(errors) == 0

    def test_validate_invalid_json(self, temp_dir):
        pipe = Pipeline()
        script_path = os.path.join(temp_dir, "invalid.json")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        errors = pipe.validate_script(script_path)
        assert len(errors) > 0

    def test_validate_missing_segments(self, temp_dir):
        pipe = Pipeline()
        script_path = os.path.join(temp_dir, "no_seg.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump({"title": "测试", "duration": 5}, f)
        errors = pipe.validate_script(script_path)
        assert len(errors) > 0

    def test_validate_empty_segments(self, temp_dir):
        pipe = Pipeline()
        script_path = os.path.join(temp_dir, "empty_seg.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump({"title": "测试", "duration": 5, "segments": []}, f)
        errors = pipe.validate_script(script_path)
        assert len(errors) > 0

    def test_validate_file_not_found(self):
        pipe = Pipeline()
        errors = pipe.validate_script("/nonexistent/script.json")
        assert len(errors) > 0


class TestPipelineError:
    def test_pipeline_error_creation(self):
        err = PipelineError(PipelineStep.LOAD_SCRIPT, "测试错误")
        assert err.step == PipelineStep.LOAD_SCRIPT
        assert "[load_script]" in str(err)
        assert "测试错误" in str(err)

    def test_pipeline_error_with_cause(self):
        cause = ValueError("原始错误")
        err = PipelineError(PipelineStep.RENDER_VIDEO, "渲染失败", cause)
        assert err.cause is cause

    def test_pipeline_progress_creation(self):
        p = PipelineProgress(step=PipelineStep.RENDER_VIDEO, progress=0.5, message="渲染中")
        assert p.step == PipelineStep.RENDER_VIDEO
        assert p.progress == 0.5
        assert p.message == "渲染中"


class TestPipelineProgress:
    def test_progress_callback_received(self):
        pipe = Pipeline()
        received = []
        cfg = {"logging": {"level": "ERROR"}}

        def cb(progress):
            received.append(progress)

        pipe._report(cb, PipelineStep.INIT, 0.0, "初始化")
        assert len(received) == 1
        assert received[0].step == PipelineStep.INIT
        assert received[0].progress == 0.0

    def test_progress_callback_none(self):
        pipe = Pipeline()
        pipe._report(None, PipelineStep.INIT, 0.5, "test")
        assert True


class TestPipelineSteps:
    def test_step_enum_values(self):
        assert PipelineStep.INIT.value == "init"
        assert PipelineStep.LOAD_SCRIPT.value == "load_script"
        assert PipelineStep.MATCH_ASSETS.value == "match_assets"
        assert PipelineStep.APPLY_RULES.value == "apply_rules"
        assert PipelineStep.BUILD_TIMELINE.value == "build_timeline"
        assert PipelineStep.GENERATE_TTS.value == "generate_tts"
        assert PipelineStep.GENERATE_SUBTITLE.value == "generate_subtitle"
        assert PipelineStep.RENDER_VIDEO.value == "render_video"
        assert PipelineStep.DONE.value == "done"

    def test_step_order(self):
        steps = list(PipelineStep)
        expected = [
            PipelineStep.INIT,
            PipelineStep.LOAD_SCRIPT,
            PipelineStep.MATCH_ASSETS,
            PipelineStep.APPLY_RULES,
            PipelineStep.BUILD_TIMELINE,
            PipelineStep.GENERATE_TTS,
            PipelineStep.GENERATE_SUBTITLE,
            PipelineStep.RENDER_VIDEO,
            PipelineStep.PREVIEW,
            PipelineStep.DONE,
        ]
        assert steps == expected


class TestPipelineScriptLoad:
    def test_load_script_valid_json(self, temp_dir):
        pipe = Pipeline()
        script_path = os.path.join(temp_dir, "script.json")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write('{"title":"t","duration":5,"segments":[{"id":1,"text":"a","duration":5}]}')
        errors = pipe.validate_script(script_path)
        assert len(errors) == 0

    def test_load_script_utf8(self, temp_dir):
        pipe = Pipeline()
        script_path = os.path.join(temp_dir, "chinese.json")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write('{"title":"中文测试","duration":5,"segments":[{"id":1,"text":"中文内容","duration":5}]}')
        errors = pipe.validate_script(script_path)
        assert len(errors) == 0
