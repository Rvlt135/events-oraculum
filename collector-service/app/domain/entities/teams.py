from pydantic import BaseModel

# {"created": created, "updated": updated, "team_slugs": list(collected_slugs), "errors": 0}

class SyncTeamsResult(BaseModel):
    created: int
    updated: int
    team_slugs: list[str] = []
    errors: int