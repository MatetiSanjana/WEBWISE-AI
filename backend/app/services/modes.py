"""Quick vs Deep research configuration. These values genuinely change backend behaviour."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModeConfig:
    name: str
    num_queries: int
    results_per_query: int
    max_sources: int
    max_per_domain: int
    search_depth: str  # Tavily: "basic" | "advanced"
    include_raw_content: bool
    chars_per_source: int  # text per source given to Gemini
    prompt_char_budget: int  # hard cap on total evidence text per LLM call
    two_pass_analysis: bool  # Deep: per-source extraction, then cross-source synthesis
    report_style: str
    max_output_tokens: int


MODES: dict[str, ModeConfig] = {
    "quick": ModeConfig(
        name="quick",
        num_queries=3,
        results_per_query=5,
        max_sources=8,
        max_per_domain=2,
        search_depth="basic",
        include_raw_content=False,
        chars_per_source=1500,
        prompt_char_budget=40_000,
        two_pass_analysis=False,
        report_style=(
            "Concise: 3-5 key findings, 1-2 detailed analysis sections, brief comparison."
        ),
        max_output_tokens=24576,
    ),
    "deep": ModeConfig(
        name="deep",
        num_queries=7,
        results_per_query=7,
        max_sources=18,
        max_per_domain=3,
        search_depth="advanced",
        include_raw_content=True,
        chars_per_source=4000,
        prompt_char_budget=140_000,
        two_pass_analysis=True,
        report_style=(
            "Detailed: 6-10 key findings, 3-6 detailed analysis sections, a thorough "
            "cross-source comparison, and an explicit search for conflicts and outdated claims."
        ),
        max_output_tokens=48000,
    ),
}


def get_mode(name: str) -> ModeConfig:
    return MODES[name]
