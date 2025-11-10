"""
Helper functions for building and managing event participants.
"""
from typing import Literal, Any
import structlog

from app.domain.entities.participant import ParticipantItemDTO

logger = structlog.get_logger()


def build_participants(
    raw_data: dict[str, Any],
    participant_mode: Literal["duel", "solo", "field", "unknown"]
) -> list[ParticipantItemDTO]:
    """
    Build participant list from raw event data based on participant mode.

    Args:
        raw_data: Raw event data containing participant information
        participant_mode: Mode determining how to interpret participants

    Returns:
        List of ParticipantItemDTO objects
    """
    participants = []

    try:
        if participant_mode == "duel":
            # Duel mode: home vs away
            home_name = raw_data.get("home_team")
            away_name = raw_data.get("away_team")

            if home_name:
                participants.append(ParticipantItemDTO(
                    role="home",
                    name=home_name,
                    provider_alias=home_name,
                    team_id=None  # Will be filled by normalization if enabled
                ))

            if away_name:
                participants.append(ParticipantItemDTO(
                    role="away",
                    name=away_name,
                    provider_alias=away_name,
                    team_id=None  # Will be filled by normalization if enabled
                ))

        elif participant_mode == "solo":
            # Solo mode: single participant
            participant_name = raw_data.get("participant") or raw_data.get("home_team")
            if participant_name:
                participants.append(ParticipantItemDTO(
                    role="solo",
                    name=participant_name,
                    provider_alias=participant_name,
                    team_id=None
                ))

        elif participant_mode == "field":
            # Field mode: multiple participants in a field
            field_participants = raw_data.get("participants", [])
            if isinstance(field_participants, list):
                for idx, p in enumerate(field_participants):
                    if isinstance(p, str):
                        name = p
                    elif isinstance(p, dict):
                        name = p.get("name", f"Participant {idx+1}")
                    else:
                        continue

                    participants.append(ParticipantItemDTO(
                        role="field",
                        name=name,
                        provider_alias=name,
                        team_id=None
                    ))
            elif not field_participants:
                # Fallback to home_team if available
                home_name = raw_data.get("home_team")
                if home_name:
                    participants.append(ParticipantItemDTO(
                        role="field",
                        name=home_name,
                        provider_alias=home_name,
                        team_id=None
                    ))

        else:  # unknown
            # Best effort: try to extract any participant info
            home_name = raw_data.get("home_team")
            away_name = raw_data.get("away_team")

            if home_name:
                participants.append(ParticipantItemDTO(
                    role="home",
                    name=home_name,
                    provider_alias=home_name,
                    team_id=None
                ))

            if away_name:
                participants.append(ParticipantItemDTO(
                    role="away",
                    name=away_name,
                    provider_alias=away_name,
                    team_id=None
                ))

        logger.debug(
            "participants_built",
            mode=participant_mode,
            count=len(participants)
        )

    except Exception as e:
        logger.error(
            "build_participants_error",
            mode=participant_mode,
            error=str(e),
            exc_info=True
        )

    return participants
