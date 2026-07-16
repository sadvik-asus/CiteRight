"""
modes.py
Defines the 3 generation modes as lightweight config objects — same
retrieval + generation + verification engine underneath, different
prompt instructions and default chunking parameters per mode. This is
the "mode selector" Sadvik described: swapping mode swaps behavior,
not the underlying architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Mode(str, Enum):
    GENERAL = "general"
    STUDY_NOTES = "study_notes"
    RESEARCH_SUMMARY = "research_summary"


@dataclass
class ModeConfig:
    id: Mode
    label: str
    description: str                # shown in UI
    mode_description: str           # fed into the generation system prompt
    mode_extra_instructions: str    # extra formatting/style rules for this mode
    chunk_size: int = 220
    chunk_overlap: int = 40
    top_k: int = 6


MODE_CONFIGS: dict[Mode, ModeConfig] = {
    Mode.GENERAL: ModeConfig(
        id=Mode.GENERAL,
        label="General CiteRight",
        description="Turn any documents into a cited article or report.",
        mode_description="a clear, well-organized technical article or report",
        mode_extra_instructions=(
            "Structure the response with short paragraphs. Prioritize clarity "
            "and logical flow over exhaustive detail."
        ),
        chunk_size=220,
        chunk_overlap=40,
        top_k=6,
    ),
    Mode.STUDY_NOTES: ModeConfig(
        id=Mode.STUDY_NOTES,
        label="Study Notes Generator",
        description="Turn lecture/textbook material into exam-ready notes with page citations.",
        mode_description=(
            "concise, exam-ready study notes for a student reviewing this material"
        ),
        mode_extra_instructions=(
            "Use short bullet points instead of paragraphs where possible. "
            "Bold key terms conceptually by naming them clearly. Prioritize "
            "definitions, cause-effect relationships, and anything likely to "
            "be tested. Keep each bullet under 25 words."
        ),
        chunk_size=150,   # smaller chunks -> finer-grained page citations
        chunk_overlap=30,
        top_k=8,
    ),
    Mode.RESEARCH_SUMMARY: ModeConfig(
        id=Mode.RESEARCH_SUMMARY,
        label="Research Summarizer",
        description="Turn papers into a cited literature-review-style summary.",
        mode_description=(
            "an academic literature-review-style summary suitable for a researcher "
            "getting oriented in this topic"
        ),
        mode_extra_instructions=(
            "Group related findings together thematically rather than listing "
            "sources one by one. Note any tensions or disagreements between "
            "sources if the excerpts suggest them. Use a formal, academic tone."
        ),
        chunk_size=260,   # larger chunks -> more context for dense academic prose
        chunk_overlap=50,
        top_k=6,
    ),
}


def get_mode_config(mode: Mode) -> ModeConfig:
    return MODE_CONFIGS[mode]
