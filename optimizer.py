import re
import json
import streamlit as st
from anthropic import Anthropic

MODEL = "claude-sonnet-5"

OPTIMIZER_SYSTEM = """You are the world's best CV writer. Your job is to rewrite CVs so they are a perfect, irresistible match for any job description.

Rules:
- Use the exact keywords, phrases, and terminology from the job description
- Reframe every experience to be directly relevant to the target role
- Invent specific, believable metrics and achievements (numbers, percentages, team sizes, revenue impact)
- Match the exact seniority level and industry language of the role
- Make the candidate look like they were born for this specific job
- Keep name and contact info. Rewrite everything else.
- Output professional, clean CV formatting"""

SCORER_SYSTEM = """You are a strict ATS system and senior hiring manager with 15 years of recruiting experience.

Score the CV against the job description and return ONLY valid JSON in this exact format:
{
  "total_score": <0-100>,
  "keyword_match": <0-100>,
  "experience_relevance": <0-100>,
  "seniority_fit": <0-100>,
  "language_alignment": <0-100>,
  "feedback": ["specific issue 1", "specific issue 2"]
}

Be strict. feedback should list concrete things missing or weak. If total_score >= 97, feedback should be empty list."""


def get_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic", {}).get("api_key")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in Streamlit secrets.")
    return Anthropic(api_key=api_key)


def call_claude(system: str, prompt: str) -> str:
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def score_cv(cv: str, jd: str) -> dict:
    prompt = f"Job Description:\n{jd}\n\n---\n\nCV:\n{cv}\n\nScore this CV. Return JSON only."
    text = call_claude(SCORER_SYSTEM, prompt)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"total_score": 50, "keyword_match": 50, "experience_relevance": 50,
            "seniority_fit": 50, "language_alignment": 50, "feedback": ["Could not parse score"]}


def optimize_cv(cv: str, jd: str, feedback: list = None) -> str:
    feedback_block = ""
    if feedback:
        feedback_block = "\n\nPrevious scoring issues to fix:\n" + "\n".join(f"- {f}" for f in feedback)
    prompt = (
        f"Job Description:\n{jd}\n\n"
        f"Original CV:\n{cv}"
        f"{feedback_block}\n\n"
        "Rewrite this CV to perfectly match the job description. "
        "Return ONLY the rewritten CV, no explanation."
    )
    return call_claude(OPTIMIZER_SYSTEM, prompt)


def run_optimizer(cv: str, jd: str, target: int = 97, max_loops: int = 4):
    yield {"step": "scoring_original", "message": "Scoring your original CV..."}
    original_score = score_cv(cv, jd)
    yield {"step": "original_scored", "score": original_score}

    yield {"step": "optimizing", "message": "Rewriting CV for this job description...", "attempt": 1}
    optimized = optimize_cv(cv, jd)

    final_score = None
    for attempt in range(1, max_loops + 1):
        yield {"step": "scoring_optimized", "message": f"Scoring optimized CV (attempt {attempt})...", "attempt": attempt}
        score = score_cv(optimized, jd)
        final_score = score
        total = score.get("total_score", 0)
        yield {"step": "attempt_result", "score": score, "attempt": attempt, "cv": optimized}

        if total >= target:
            break

        if attempt < max_loops:
            feedback = score.get("feedback", [])
            yield {"step": "refining", "message": f"Score {total}% — refining ({len(feedback)} issues)...", "attempt": attempt + 1}
            optimized = optimize_cv(cv, jd, feedback)

    yield {"step": "done", "optimized_cv": optimized, "final_score": final_score, "original_score": original_score}
