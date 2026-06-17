"""
JobAgent AI — Resume Tailor + Cover Letter Generator (Groq)
Selects the MOST RELEVANT subset of your master CV per job and tailors
phrasing — strictly constrained to fit one page. Includes a conditional
Leadership section for leadership/operations-heavy roles.
"""

import os
import logging
import json
from groq import Groq
from config import RESUME_PATH, PROFILE

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------------------------------------------------------------------
# Load master CV
# ---------------------------------------------------------------------------

def load_base_resume() -> dict:
    if not os.path.exists(RESUME_PATH):
        logger.warning("base_resume.json not found at %s — using placeholder", RESUME_PATH)
        return _placeholder_resume()
    with open(RESUME_PATH, "r") as f:
        return json.load(f)


def _placeholder_resume() -> dict:
    return {
        "name": "Your Name",
        "email": "you@email.com",
        "phone": "+91-XXXXXXXXXX",
        "linkedin": "linkedin.com/in/yourprofile",
        "github": "github.com/yourusername",
        "summary": "ML/AI enthusiast with experience building Python-based systems and LLM integrations.",
        "skills": PROFILE["skills"],
        "experience": [],
        "projects": [],
        "leadership": [],
        "education": {"degree": "B.Tech", "institute": "Your University", "year": "2025"}
    }


# ---------------------------------------------------------------------------
# Leadership relevance detector
# ---------------------------------------------------------------------------

LEADERSHIP_SIGNAL_WORDS = [
    "lead", "leadership", "manage", "manager", "management", "operations", "ops",
    "coordinator", "coordinate", "mentor", "mentorship", "head", "founder",
    "stakeholder", "client management", "cross-functional", "team lead",
    "program manager", "project manager", "chapter", "president", "club",
]


def _is_leadership_relevant(job: dict) -> bool:
    """Heuristic pre-check before even asking the LLM — cheap signal on title/desc."""
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(word in text for word in LEADERSHIP_SIGNAL_WORDS)


# ---------------------------------------------------------------------------
# Resume tailor — SELECTIVE, ONE-PAGE CONSTRAINED, 2 BULLETS PER ITEM
# ---------------------------------------------------------------------------

TAILOR_SYSTEM = """You are an expert resume writer specialising in ONE-PAGE tech resumes.

You will be given a MASTER CV (containing ALL of a candidate's experience, projects,
skills, education, leadership — far more content than fits one page) and a JOB DESCRIPTION.

Your task: produce a TAILORED, ONE-PAGE-ONLY resume by SELECTING and REWRITING only the
most relevant subset of the master CV for this specific job. You are curating, not just rephrasing.

STRICT RULES — violating any of these is a failure:
1. ONE PAGE MAX. This means:
   - Summary: 1-2 sentences max.
   - Skills: only the 10-14 most relevant skills for THIS job (drop irrelevant ones entirely).
   - Experience: include ONLY the 1-2 most relevant roles. For EACH role, include EXACTLY 2
     bullets (the most relevant ones, rewritten to highlight JD keywords). Drop irrelevant roles.
   - Projects: include ONLY the 2-3 most relevant projects to this specific job. For EACH
     project, include EXACTLY 2 bullets. Drop everything else.
   - Education: keep as-is, 1 line.
   - Leadership: ONLY include this section if the job description signals a leadership,
     management, operations, client-facing, or cross-functional-coordination component
     (e.g. "team lead", "manage stakeholders", "operations", "client management", "mentor").
     If included, select ONLY the 1-2 most relevant leadership items, each as ONE concise line.
     If the job is purely a technical IC role with no such signal, OMIT leadership entirely —
     do not force it in.
2. Every bullet you keep should be REWRITTEN to mirror the job description's language and
   keywords where truthful — but never fabricate skills, metrics, or experience not in the master CV.
3. Prioritise: relevance to the JD > recency > impact/metrics.
4. EXACTLY 2 bullets per experience entry. EXACTLY 2 bullets per project entry. No more, no fewer
   (unless the master CV genuinely has fewer than 2 for that item — then use what's available).

Return ONLY valid JSON matching this exact schema (no markdown, no explanation, no extra keys):
{
  "name": "...", "email": "...", "phone": "...", "location": "...",
  "linkedin": "...", "github": "...",
  "summary": "...",
  "skills": ["...", "..."],
  "experience": [{"role": "...", "company": "...", "duration": "...", "bullets": ["...", "..."]}],
  "projects": [{"name": "...", "tech": ["...", "..."], "bullets": ["...", "..."]}],
  "leadership": [{"title": "...", "details": "..."}],
  "education": {"degree": "...", "institute": "...", "year": "...", "details": "..."}
}
If leadership is omitted per the rules above, return "leadership": [] (empty array)."""


def tailor_resume(base_resume: dict, job: dict) -> dict:
    jd_text = (
        f"Title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Description: {job.get('description', '')[:2000]}"
    )

    leadership_hint = (
        "NOTE: This job's title/description shows signals of leadership, operations, "
        "or client-facing responsibility — strongly consider including the Leadership section."
        if _is_leadership_relevant(job) else
        "NOTE: This job appears to be a pure technical/IC role with no leadership signal — "
        "leadership section should likely be omitted unless truly exceptional fit exists."
    )

    prompt = (
        f"MASTER CV (select from this — do not use everything):\n{json.dumps(base_resume, indent=2)}\n\n"
        f"JOB DESCRIPTION:\n{jd_text}\n\n"
        f"{leadership_hint}\n\n"
        "Select the most relevant subset and produce a strict ONE-PAGE tailored resume JSON now. "
        "Exactly 2 bullets per experience entry, exactly 2 bullets per project entry."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": TAILOR_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1800,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        tailored = json.loads(raw)

        # Safety net: hard-cap counts even if the model overshoots
        tailored["experience"] = tailored.get("experience", [])[:2]
        for exp in tailored["experience"]:
            exp["bullets"] = exp.get("bullets", [])[:2]
        tailored["projects"] = tailored.get("projects", [])[:3]
        for proj in tailored["projects"]:
            proj["bullets"] = proj.get("bullets", [])[:2]
        tailored["skills"] = tailored.get("skills", [])[:14]
        tailored["leadership"] = tailored.get("leadership", [])[:2]

        logger.info(
            "Resume tailored for: %s @ %s (%d exp, %d projects, %d leadership)",
            job.get("title"), job.get("company"),
            len(tailored["experience"]), len(tailored["projects"]), len(tailored["leadership"])
        )
        return tailored
    except Exception as e:
        logger.error("Resume tailor error: %s", e)
        # Fallback: still cap the base resume so it doesn't overflow
        fallback = dict(base_resume)
        fallback["experience"] = [
            {**e, "bullets": e.get("bullets", [])[:2]} for e in fallback.get("experience", [])[:2]
        ]
        fallback["projects"] = [
            {**p, "bullets": p.get("bullets", [])[:2]} for p in fallback.get("projects", [])[:3]
        ]
        fallback["skills"] = fallback.get("skills", [])[:14]
        fallback["leadership"] = fallback.get("leadership", [])[:2] if _is_leadership_relevant(job) else []
        return fallback


# ---------------------------------------------------------------------------
# Cover letter generator
# ---------------------------------------------------------------------------

COVER_SYSTEM = """You are an expert cover letter writer for tech roles.
Write a concise, enthusiastic, professional cover letter (3 short paragraphs, max 200 words).
Address it to the hiring team. Use the candidate name provided. Return plain text only."""


def generate_cover_letter(resume: dict, job: dict) -> str:
    jd_text = (
        f"Role: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Description: {job.get('description', '')[:1500]}"
    )

    prompt = (
        f"CANDIDATE NAME: {resume.get('name', 'Candidate')}\n"
        f"CANDIDATE SKILLS: {', '.join(resume.get('skills', []))}\n\n"
        f"JOB:\n{jd_text}\n\n"
        "Write the cover letter."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": COVER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.4,
        )
        letter = response.choices[0].message.content.strip()
        logger.info("Cover letter generated for: %s @ %s", job.get("title"), job.get("company"))
        return letter
    except Exception as e:
        logger.error("Cover letter error: %s", e)
        return "Cover letter generation failed. Please write manually."


def prepare_application(job: dict) -> dict:
    base = load_base_resume()
    tailored = tailor_resume(base, job)
    cover_letter = generate_cover_letter(tailored, job)
    return {
        "job": job,
        "tailored_resume": tailored,
        "cover_letter": cover_letter,
    }