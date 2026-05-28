import os
from pathlib import Path

_HAS_YAML = False
try:
    import yaml

    _HAS_YAML = True
except ImportError:
    pass


def _levenshtein(s1: str, s2: str) -> int:
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        cur = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            cur.append(min(cur[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = cur
    return prev[-1]


def _is_chinese(c: str) -> bool:
    return "\u4e00" <= c <= "\u9fff"


class SynonymEngine:

    def __init__(self, yaml_path: str = "data/synonyms.yaml"):
        self._dict: dict[str, list[str]] = {}
        self._reverse: dict[str, str] = {}
        if yaml_path:
            self.load_yaml(yaml_path)

    def load_yaml(self, yaml_path: str):
        if not _HAS_YAML:
            return
        resolved = Path(yaml_path)
        if not resolved.exists():
            project_root = self._find_project_root()
            if project_root:
                resolved = project_root / yaml_path
        if not resolved.exists():
            return
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        self._load_dict(data)

    def load_dict(self, synonyms: dict[str, list[str]]):
        self._load_dict(synonyms)

    def _load_dict(self, synonyms: dict[str, list[str]]):
        for key, values in synonyms.items():
            key_lower = key.lower()
            if key_lower not in self._dict:
                self._dict[key_lower] = []
            for v in values:
                v_lower = v.lower()
                if v_lower not in self._dict[key_lower]:
                    self._dict[key_lower].append(v_lower)
                if v_lower not in self._reverse:
                    self._reverse[v_lower] = key_lower

    def expand(self, word: str, limit: int = 5) -> list[str]:
        key = word.lower()
        result = [word]
        if key in self._dict:
            for syn in self._dict[key]:
                if syn not in result:
                    result.append(syn)
                if len(result) >= limit + 1:
                    break
        return result

    def score(self, word: str, candidate: str) -> float:
        w = word.lower()
        c = candidate.lower()
        if w == c:
            return 1.0
        if (w in self._dict and c in self._dict[w]) or (c in self._dict and w in self._dict[c]):
            return 0.8
        dist = _levenshtein(w, c)
        if w and c:
            is_cn = _is_chinese(w[0]) or _is_chinese(c[0])
            max_dist = 2 if is_cn else 3
            ratio = dist / max(len(w), len(c))
            if dist <= max_dist and ratio <= 0.5:
                return 0.4
        return 0.0

    def expand_keywords(self, keywords: list[str]) -> list[str]:
        result = set()
        for kw in keywords:
            result.add(kw.lower())
            for syn in self.expand(kw):
                result.add(syn.lower())
        return list(result)

    @staticmethod
    def _find_project_root() -> Path | None:
        current = Path(__file__).resolve().parent.parent
        if (current / "data").is_dir():
            return current
        if (current / "config.template.yaml").exists():
            return current
        return current if current.name else None
