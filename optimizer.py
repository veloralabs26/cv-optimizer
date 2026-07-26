import re
import json
import subprocess

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

Be strict. If total_score >= 97, feedback should be empty list."""


def call_claude(system: str, prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--system-prompt", system, "--model", MODEL],
        capture_output=True,
        text=True,
        timeout=120
    )
    return result.stdout.strip()


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
            "seniority_fit": 50, "language_alignment": 50, "feedback": []}


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
    """Yields status dicts so the caller can send Telegram updates."""

    yield {"step": "status", "message": "📊 Scoring your original CV..."}
    original_score = score_cv(cv, jd)
    yield {"step": "status", "message": f"📊 Original score: *{original_score['total_score']}%*"}

    yield {"step": "status", "message": "✍️ Rewriting CV for this role..."}
    optimized = optimize_cv(cv, jd)

    final_score = None
    for attempt in range(1, max_loops + 1):
        yield {"step": "status", "message": f"🔍 Scoring optimized CV \\(attempt {attempt}\\)\\.\\.\\."}
        score = score_cv(optimized, jd)
        final_score = score
        total = score.get("total_score", 0)

        if total >= target:
            yield {"step": "status", "message": f"✅ Target reached: *{total}%*"}
            break

        if attempt < max_loops:
            feedback = score.get("feedback", [])
            yield {"step": "status", "message": f"⚡ Score {total}% — refining \\({len(feedback)} issues\\)\\.\\.\\."}
            optimized = optimize_cv(cv, jd, feedback)

    yield {
        "step": "done",
        "optimized_cv": optimized,
        "final_score": final_score,
        "original_score": original_score
    }
