"""
JobAgent AI — Resume Tailor + Cover Letter Generator (Groq)
Uses Groq's llama-3.3-70b to customise your resume and write a cover letter per job.
"""

import os
import logging
import json
from groq import Groq
from config import RESUME_PATH, PROFILE

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


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
        "summary": "ML/AI enthusiast with 2 years of experience building Python-based systems and LLM integrations.",
        "skills": PROFILE["skills"],
        "experience": [
            {
                "role": "ML Engineering Intern",
                "company": "Previous Company",
                "duration": "Jun 2023 – Dec 2023",
                "bullets": [
                    "Built a text classification pipeline achieving 94% accuracy on production data.",
                    "Reduced model inference latency by 40% using ONNX export.",
                    "Collaborated with product team to ship ML features to 10K+ users.",
                ]
            }
        ],
        "projects": [
            {
                "name": "JobAgent AI",
                "description": "Autonomous job-hunting pipeline using Groq API, Python scrapers, and Gmail SMTP.",
                "tech": ["Python", "Groq API", "SQLite", "BeautifulSoup", "ReportLab"]
            }
        ],
        "education": {
            "degree": "B.Tech Computer Science",
            "institute": "Your University",
            "year": "2025"
        }
    }


TAILOR_SYSTEM = """You are an expert resume writer. Given a base resume (JSON) and a job description,
rewrite the resume's bullet points and summary to highlight keywords from the JD.
Keep the same JSON structure exactly. Return ONLY valid JSON. No markdown, no explanation."""


def tailor_resume(base_resume: dict, job: dict) -> dict:
    jd_text = (
        f"Title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Description: {job.get('description', '')[:2000]}"
    )

    prompt = (
        f"BASE RESUME:\n{json.dumps(base_resume, indent=2)}\n\n"
        f"JOB DESCRIPTION:\n{jd_text}\n\n"
        "Tailor this resume for the job. Return updated JSON only."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": TAILOR_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        tailored = json.loads(raw)
        logger.info("Resume tailored for: %s @ %s", job.get("title"), job.get("company"))
        return tailored
    except Exception as e:
        logger.error("Resume tailor error: %s", e)
        return base_resume


COVER_SYSTEM = """You are an expert cover letter writer for tech internship roles.
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