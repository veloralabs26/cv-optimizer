import re
import json
import subprocess

MODEL = "claude-sonnet-5"

OPTIMIZER_SYSTEM = """You are the world's best CV writer and career strategist. Your job is to surface and reframe a person's REAL experience so it speaks the exact language of the job they're applying for.

Core principle: Never invent experience, companies, or roles. Only reframe what is already there.

What you DO:
- Identify which parts of the person's real experience map to the job requirements, even if they don't realize it themselves
- Rewrite their bullet points using the exact keywords, verbs, and terminology from the job description
- Surface hidden value — responsibilities they mentioned casually that are actually highly relevant
- Strengthen weak, vague bullet points into specific, metric-driven achievements using reasonable estimates based on what they described
- Reorder sections and bullets so the most relevant experience appears first
- Rewrite the summary to position them perfectly for this specific role

What you NEVER do:
- Add companies, job titles, or roles that don't exist in the original CV
- Invent achievements that have no basis in what they described
- Change dates or tenure

FORMAT — NON-NEGOTIABLE:
- Exactly ONE full page — dense, no empty space, no padding
- Structure:

  [FULL NAME]
  [Email] | [Phone] | [Location or LinkedIn]

  PROFESSIONAL SUMMARY
  2-3 punchy lines that position the candidate for this exact role using the JD's language

  EXPERIENCE
  Job Title — Company | Date Range
  • Strong action verb + what they did + measurable result
  • Strong action verb + what they did + measurable result
  • Strong action verb + what they did + measurable result
  (2-3 roles max, 3 bullets each — prioritize most relevant roles)

  EDUCATION
  Degree — Institution | Year

  SKILLS
  Exact keywords from the JD that the candidate genuinely has

- Every bullet: action verb + specific detail + number or outcome
- Output plain text only, no markdown"""

SCORER_SYSTEM = """You are a senior ATS system and hiring manager with 15 years of recruiting experience.

Score how well the CV is positioned for the job description — based on how the experience is framed, not whether it's fabricated.

Return ONLY valid JSON in this exact format:
{
  "total_score": <0-100>,
  "keyword_match": <0-100>,
  "experience_relevance": <0-100>,
  "seniority_fit": <0-100>,
  "language_alignment": <0-100>,
  "feedback": ["specific improvement needed", "another specific improvement"]
}

Scoring criteria:
- keyword_match: does the CV use the exact terms, tools, and phrases from the JD?
- experience_relevance: does the described experience map to what the role needs?
- seniority_fit: does the level of responsibility match the role's seniority?
- language_alignment: does the tone, style, and vocabulary match the company/industry?

Be strict and specific in feedback. If total_score >= 97, feedback should be an empty list."""


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
