from typing import Literal

from pydantic import BaseModel, Field

from .scoring.models import Parent, Spark, SparkBlock


class SparkIn(BaseModel):
    kind: Literal["blue", "pink", "green", "white"]
    name: str
    stars: int = Field(ge=1, le=3)
    category: Literal["skill", "race", "scenario"] | None = None


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

    def to_domain(self) -> Parent:
        return Parent(
            name=self.name,
            outfit=self.outfit,
            style=self.style,
            affinity=self.affinity,
            affinity_target=self.affinity_target,
            blocks=[
                SparkBlock(role=b.role, character=b.character,
                           sparks=[Spark(**s.model_dump()) for s in b.sparks])
                for b in self.blocks
            ],
        )
