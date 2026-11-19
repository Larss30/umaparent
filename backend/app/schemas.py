from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .scoring.models import Parent, Spark, SparkBlock


class SparkIn(BaseModel):
    kind: Literal["blue", "pink", "green", "white"]
    name: str
    stars: int = Field(ge=1, le=3)
    category: Literal["skill", "race", "scenario"] | None = None
    skill_id: int | None = None


class BlockIn(BaseModel):
    role: Literal["self", "grandparent_1", "grandparent_2"]
    character: str | None = None
    sparks: list[SparkIn] = Field(max_length=60)


class ParentIn(BaseModel):
    name: str
    outfit: str | None = None
    style: str | None = None
    affinity: int | None = Field(default=None, ge=0, le=1000)
    affinity_target: str | None = None
    blocks: list[BlockIn] = Field(max_length=3)
    custom_weights: dict[str, float] | None = Field(default=None, max_length=400)
    custom_blue: dict[str, float] | None = Field(default=None, max_length=10)
    custom_pink: dict[str, float] | None = Field(default=None, max_length=20)
    auto_zero: bool = True
    custom_green_default: float | None = Field(default=None, ge=0, le=5)
    context_weights: dict[str, dict[str, float | None]] | None = Field(default=None, max_length=20)

    @field_validator("custom_weights", "custom_blue", "custom_pink")
    @classmethod
    def _weights_in_range(cls, v):
        if v and any(not (0 <= w <= 5) or len(k) > 80 for k, w in v.items()):
            raise ValueError("weights must be 0-5 and names under 80 characters")
        return v

    @field_validator("context_weights")
    @classmethod
    def _context_in_range(cls, v):
        for ctx in (v or {}).values():
            if len(ctx) > 400 or any(
                (w is not None and not (0 <= w <= 5)) or len(k) > 80 for k, w in ctx.items()
            ):
                raise ValueError("context weights must be 0-5, names under 80 characters")
        return v

    def to_domain(self) -> Parent:
        return Parent(
            name=self.name,
            outfit=self.outfit,
            style=self.style,
            affinity=self.affinity,
            affinity_target=self.affinity_target,
            custom_weights=self.custom_weights,
            custom_blue=self.custom_blue,
            custom_pink=self.custom_pink,
            custom_green_default=self.custom_green_default,
            auto_zero=self.auto_zero,
            context_weights=self.context_weights,
            blocks=[
                SparkBlock(role=b.role, character=b.character,
                           sparks=[Spark(**s.model_dump()) for s in b.sparks])
                for b in self.blocks
            ],
        )
