"""Pure feedback loop for measured improvement without hidden mutation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Trial:
    proposal: str
    before: float
    after: float

    @property
    def improved(self) -> bool:
        return self.after > self.before

def next_signal(trial: Trial) -> str:
    return "CONTINUE" if trial.improved else "REVISE"
