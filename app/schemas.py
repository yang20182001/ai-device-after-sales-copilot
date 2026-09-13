from __future__ import annotations

from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    device_id: str = Field(min_length=1)
    message: str = Field(min_length=2)


class TicketDraftRequest(BaseModel):
    diagnosis: dict


class Source(BaseModel):
    chunk_id: str
    source_name: str
    source_section: str
    content: str
    score: float


class TicketDraft(BaseModel):
    ticket_id: str
    device_id: str
    title: str
    symptom: str
    priority: str
    status: str
    assignee: str | None = None
    due_at: str | None = None
    investigation_steps: list[str] = Field(default_factory=list)
    parts: list[str] = Field(default_factory=list)
    escalation_condition: str | None = None
    requires_human_confirmation: bool = True
