from dataclasses import dataclass, field

KINDS = ("blue", "pink", "green", "white")
ROLES = ("self", "grandparent_1", "grandparent_2")
WHITE_CATEGORIES = ("skill", "race", "scenario")


@dataclass
class Spark:
    kind: str          # blue | pink | green | white
    name: str
    stars: int         # 1-3
    category: str | None = None  # white only: skill | race | scenario
    skill_id: int | None = None  # game skill id, when known


@dataclass
class SparkBlock:
    role: str          # self | grandparent_1 | grandparent_2
    sparks: list[Spark] = field(default_factory=list)
    character: str | None = None


@dataclass
class Parent:
    name: str
    blocks: list[SparkBlock] = field(default_factory=list)
    outfit: str | None = None
    style: str | None = None   # id of a file in data/styles, e.g. "pace-chaser"
    affinity: int | None = None          # manual affinity score (Phase 4 can compute it)
    affinity_target: str | None = None   # trainee the affinity is for
    custom_weights: dict[str, float] | None = None   # user's own white-spark weights
    custom_blue: dict[str, float] | None = None
    custom_pink: dict[str, float] | None = None
    custom_green_default: float | None = None
    context_weights: dict[str, dict[str, float | None]] | None = None  # per profile id
    auto_zero: bool = True   # zero skills that cannot trigger in this event or style
