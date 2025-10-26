from typing import List

from pydantic import BaseModel

class Sport(BaseModel):
    key: str
    group: str
    title: str
    description: str
    active: bool
    has_outrights: bool


class SportList(BaseModel):
    sports: List[Sport]
