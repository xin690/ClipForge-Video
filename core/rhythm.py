from core.config import get as _config_get


class RhythmAnalyzer:

    @staticmethod
    def available() -> bool:
        try:
            import librosa  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def detect_bpm(audio_path: str) -> float:
        import librosa
        y, sr = librosa.load(audio_path, sr=None)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, "item"):
            tempo = float(tempo.item())
        else:
            tempo = float(tempo)
        return tempo

    @staticmethod
    def get_beat_frames(audio_path: str, sr: int = 22050) -> list[float]:
        import librosa
        y, sr_actual = librosa.load(audio_path, sr=sr)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr_actual)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr_actual)
        return [float(t) for t in beat_times]

    @staticmethod
    def align_transitions(
        segment_durations: list[float],
        beats: list[float],
        tolerance: float = 0.15,
    ) -> list[float]:
        events: list[float] = []
        current = 0.0
        for dur in segment_durations:
            target = current + dur
            best_time = target
            best_dist = tolerance + 0.01
            for beat in beats:
                if abs(beat - target) < best_dist:
                    best_dist = abs(beat - target)
                    best_time = beat
            events.append(best_time)
            current = best_time
        return events

    @staticmethod
    def is_strong_beat(beat_idx: int, beats_per_bar: int = 4) -> bool:
        if beats_per_bar <= 0:
            return True
        return (beat_idx % beats_per_bar) == 0

    @staticmethod
    def get_transition_for_beat(
        beat_idx: int,
        beats_per_bar: int = 4,
        strong_trans: str = "circleopen",
        weak_trans: str = "dissolve",
    ) -> str:
        import random
        strong_transitions = ["circleopen", "radial", "zoomin"]
        weak_transitions = ["dissolve", "fade", "smoothleft", "fadeblack"]
        if beat_idx % beats_per_bar == 0:
            if strong_trans in XFADE_MAP:
                return strong_trans
            return random.choice(strong_transitions)
        else:
            if weak_trans in XFADE_MAP:
                return weak_trans
            return random.choice(weak_transitions)


XFADE_MAP = {
    "circleopen", "radial", "zoomin", "dissolve", "fade", "fadeblack",
    "smoothleft", "fadegrays", "horzopen", "vertopen", "rectcrop",
    "wipedown", "wipeleft", "wiperight", "wipeup",
    "coverleft", "coverup", "coverright", "coverdown",
    "revealleft", "revealup", "revealright", "revealdown",
}
