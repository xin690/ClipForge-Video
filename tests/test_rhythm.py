from core.rhythm import RhythmAnalyzer


class TestRhythmAnalyzerAvailable:

    def test_librosa_available(self):
        assert RhythmAnalyzer.available() is True


class TestRhythmAnalyzerAlign:

    def test_no_beats_no_change(self):
        durations = [3.0, 5.0, 4.0]
        beats: list[float] = []
        result = RhythmAnalyzer.align_transitions(durations, beats, tolerance=0.15)
        assert len(result) == 3
        assert result == [3.0, 8.0, 12.0]

    def test_exact_beat_align(self):
        durations = [2.0, 3.0]
        beats = [2.0, 5.0, 8.0]
        result = RhythmAnalyzer.align_transitions(durations, beats, tolerance=0.5)
        assert result[0] == 2.0
        assert result[1] == 5.0

    def test_close_beat_clamps(self):
        durations = [2.0, 3.0]
        beats = [2.1, 5.1]
        result = RhythmAnalyzer.align_transitions(durations, beats, tolerance=0.15)
        assert abs(result[0] - 2.1) < 0.01
        assert abs(result[1] - 5.1) < 0.01


class TestRhythmAnalyzerBeatDetection:

    def test_is_strong_first_beat(self):
        assert RhythmAnalyzer.is_strong_beat(0) is True

    def test_is_not_strong_second_beat(self):
        assert RhythmAnalyzer.is_strong_beat(1) is False

    def test_is_strong_every_fourth(self):
        assert RhythmAnalyzer.is_strong_beat(4) is True
        assert RhythmAnalyzer.is_strong_beat(8) is True

    def test_custom_beats_per_bar(self):
        assert RhythmAnalyzer.is_strong_beat(0, beats_per_bar=3) is True
        assert RhythmAnalyzer.is_strong_beat(3, beats_per_bar=3) is True
        assert RhythmAnalyzer.is_strong_beat(1, beats_per_bar=3) is False


class TestRhythmTransitionSelection:

    def test_returns_valid_transitions(self):
        from core.rhythm import XFADE_MAP
        result = RhythmAnalyzer.get_transition_for_beat(0)
        assert result in XFADE_MAP

        result = RhythmAnalyzer.get_transition_for_beat(1)
        assert result in XFADE_MAP
