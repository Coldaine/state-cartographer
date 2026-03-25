from __future__ import annotations

from runtime.teacher.interface import TeacherResponse


class NoopTeacher:
    def escalate(self, payload: dict[str, object]) -> TeacherResponse:
        return TeacherResponse(status="not_configured")
