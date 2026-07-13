"""
Stage 2 — BlueprintValidator

Pure function: no DB, no LLM.
Converts a RawBlueprint into a ValidatedBlueprint, raising
BlueprintValidationError for any inconsistency.

All cross-field logic lives here so that NaturalQueryParser stays thin
and SyllabusResolver can trust its input is consistent.
"""
from __future__ import annotations

from app.services.natural_query.exceptions import BlueprintValidationError
from app.services.natural_query.schemas import RawBlueprint, ValidatedBlueprint


class BlueprintValidator:
    """Validates a RawBlueprint and returns a ValidatedBlueprint."""

    def validate(self, raw: RawBlueprint) -> ValidatedBlueprint:
        """
        Raises BlueprintValidationError on the first inconsistency found.
        Returns a ValidatedBlueprint if all checks pass.
        """
        try:
            validated = ValidatedBlueprint.model_validate(raw.model_dump())
        except Exception as exc:
            # Pydantic validation errors from ValidatedBlueprint's validators
            first_error = str(exc)
            # Extract a clean message from pydantic's error chain
            if hasattr(exc, "errors"):
                errors = exc.errors()
                if errors:
                    loc = " → ".join(str(l) for l in errors[0].get("loc", []))
                    msg = errors[0].get("msg", str(exc))
                    first_error = f"{loc}: {msg}" if loc else msg

            raise BlueprintValidationError(
                field="blueprint",
                reason=first_error,
            ) from exc

        # Extra checks not covered by Pydantic validators
        self._check_distribution_vs_difficulty(validated)

        return validated

    # ── Extra cross-field checks ──────────────────────────────────────────────

    def _check_distribution_vs_difficulty(
        self, b: ValidatedBlueprint
    ) -> None:
        """
        If both `difficulty` and `difficulty_distribution` are set,
        they would conflict. Raise rather than silently drop one.
        """
        if b.difficulty and b.difficulty_distribution:
            raise BlueprintValidationError(
                field="difficulty / difficulty_distribution",
                reason=(
                    "Provide either a single 'difficulty' filter "
                    "OR a 'difficulty_distribution' breakdown, not both."
                ),
            )
