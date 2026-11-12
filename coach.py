
"""
coach.py
--------
Core AI functions for the AI Interview Coach application.

Functions:
1. analyze_profile()
2. generate_questions()
3. evaluate_answers()
4. final_report()

This module uses ask_ai_json() from llm.py.
"""

import json
from typing import Any

from llm import ask_ai_json


# =========================================================
# 1. HELPER FUNCTIONS
# =========================================================

def _safe_list(value: Any) -> list:
    """Return a list even if the AI returns an unexpected value."""

    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def _safe_text(value: Any, default: str = "") -> str:
    """Convert a value to clean text."""

    if value is None:
        return default

    return str(value).strip()


def _safe_score(value: Any, default: float = 0.0) -> float:
    """Convert a value into a score between 0 and 10."""

    try:
        score = float(value)
        return max(0.0, min(10.0, score))
    except (TypeError, ValueError):
        return default


def _parse_json_response(response: Any) -> dict:
    """
    Normalize a JSON response returned by the LLM helper.

    ask_ai_json() should normally return a Python dictionary.
    This function also supports JSON strings and fenced JSON.
    """

    if isinstance(response, dict):
        return response

    if isinstance(response, str):
        cleaned = response.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "The AI returned invalid JSON. Please try again."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "The AI response must be a JSON object."
            )

        return parsed

    raise ValueError(
        "Unexpected response from the AI. Expected a dictionary or JSON string."
    )


def _normalize_skill_list(value: Any) -> list[str]:
    """Normalize skills into a list of unique, non-empty strings."""

    items = _safe_list(value)
    result = []
    seen = set()

    for item in items:
        if isinstance(item, dict):
            item = item.get("name", item.get("skill", ""))

        skill = _safe_text(item)

        if skill and skill.lower() not in seen:
            result.append(skill)
            seen.add(skill.lower())

    return result


# =========================================================
# 2. ANALYZE RESUME AND JOB DESCRIPTION
# =========================================================

def analyze_profile(resume_text: str, job_description: str) -> dict:
    """
    Compare a candidate's resume with the supplied job description.

    Returns:
        {
            "candidate_name": str,
            "role": str,
            "matching_skills": list,
            "missing_skills": list,
            "match_score": float,  # 0 to 100
            "summary": str
        }
    """

    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text cannot be empty.")

    if not job_description or not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    prompt = f"""
You are an experienced technical recruiter and resume analyst.

Analyze the resume against the job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY a valid JSON object with exactly these fields:

{{
    "candidate_name": "Candidate name if available, otherwise Unknown",
    "role": "Target job title inferred from the job description",
    "matching_skills": ["skills supported by the resume"],
    "missing_skills": ["important job requirements not clearly supported by the resume"],
    "match_score": 75,
    "summary": "A concise and honest assessment of the candidate's fit"
}}

Rules:
- match_score must be a number between 0 and 100.
- Do not invent skills, experience, education, or certifications.
- A skill should be listed as matching only when the resume provides evidence.
- Missing skills means requirements that are absent or not clearly demonstrated.
- Be constructive and specific.
- Do not include Markdown or text outside the JSON object.
"""

    response = ask_ai_json(prompt)
    result = _parse_json_response(response)

    match_score = result.get("match_score", 0)

    try:
        match_score = float(match_score)
    except (TypeError, ValueError):
        match_score = 0.0

    # The profile match score is a percentage, not a score out of 10.
    match_score = max(0.0, min(100.0, match_score))

    return {
        "candidate_name": _safe_text(
            result.get("candidate_name"),
            "Candidate",
        ),
        "role": _safe_text(
            result.get("role"),
            "Target Role",
        ),
        "matching_skills": _normalize_skill_list(
            result.get("matching_skills")
        ),
        "missing_skills": _normalize_skill_list(
            result.get("missing_skills")
        ),
        "match_score": round(match_score, 2),
        "summary": _safe_text(
            result.get("summary"),
            "No summary was generated.",
        ),
    }


# =========================================================
# 3. GENERATE INTERVIEW QUESTIONS
# =========================================================

def generate_questions(
    analysis: dict,
    resume_text: str,
    job_description: str,
    num_questions: int = 5,
) -> dict:
    """
    Generate interview questions personalized to the candidate.

    Returns:
        {
            "questions": [
                {
                    "question": str,
                    "type": str,
                    "skill": str
                }
            ]
        }
    """

    if not isinstance(analysis, dict):
        raise ValueError("Profile analysis must be a dictionary.")

    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text cannot be empty.")

    if not job_description or not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    try:
        num_questions = int(num_questions)
    except (TypeError, ValueError):
        num_questions = 5

    num_questions = max(1, min(15, num_questions))

    prompt = f"""
You are an experienced interviewer conducting a realistic job interview.

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

PROFILE ANALYSIS:
{json.dumps(analysis, ensure_ascii=False)}

Generate exactly {num_questions} useful interview questions.

Cover a balanced selection of:
- Technical knowledge required for the role
- Skills identified in the resume
- Projects and practical experience
- Behavioural and problem-solving situations
- Important skills missing from the resume, when relevant

Return ONLY a valid JSON object in this format:

{{
    "questions": [
        {{
            "question": "Explain the concept and give an example.",
            "type": "technical",
            "skill": "Python"
        }}
    ]
}}

Rules:
- Each question must be clear and answerable.
- Do not repeat the same question.
- Use only these types: technical, behavioural, project, missing_skill.
- The skill field should identify the main topic.
- Tailor the questions to the target role and candidate's actual resume.
- Do not provide answers to the questions.
- Do not include Markdown or text outside the JSON object.
"""

    response = ask_ai_json(prompt)
    result = _parse_json_response(response)

    raw_questions = result.get("questions", [])

    if not isinstance(raw_questions, list):
        raise ValueError(
            "The AI did not return a valid questions list."
        )

    allowed_types = {
        "technical",
        "behavioural",
        "project",
        "missing_skill",
    }

    questions = []

    for item in raw_questions:
        if isinstance(item, str):
            question_text = item.strip()
            question_type = "technical"
            skill = "General"

        elif isinstance(item, dict):
            question_text = _safe_text(item.get("question"))
            question_type = _safe_text(
                item.get("type"),
                "technical",
            ).lower()
            skill = _safe_text(
                item.get("skill"),
                "General",
            )

        else:
            continue

        if not question_text:
            continue

        if question_type not in allowed_types:
            question_type = "technical"

        questions.append({
            "question": question_text,
            "type": question_type,
            "skill": skill,
        })

    # Return only the requested number of valid questions.
    questions = questions[:num_questions]

    if not questions:
        raise ValueError(
            "No valid interview questions were generated."
        )

    return {"questions": questions}


# =========================================================
# 4. EVALUATE CANDIDATE ANSWERS
# =========================================================

def evaluate_answers(answers: list, role: str) -> dict:
    """
    Evaluate submitted interview answers.

    Each answer should contain:
        question, answer, type, skill

    Returns:
        {
            "evaluations": [
                {
                    "score": 8,
                    "relevance": 8,
                    "depth": 7,
                    "clarity": 9,
                    "examples": 8,
                    "feedback": "...",
                    "better_answer_tip": "..."
                }
            ]
        }
    """

    if not isinstance(answers, list) or not answers:
        raise ValueError("No interview answers were provided.")

    normalized_answers = []

    for index, item in enumerate(answers, start=1):
        if not isinstance(item, dict):
            continue

        question = _safe_text(item.get("question"))
        answer = _safe_text(item.get("answer"))

        if not question:
            continue

        normalized_answers.append({
            "question": question,
            "answer": answer,
            "type": _safe_text(item.get("type"), "technical"),
            "skill": _safe_text(item.get("skill"), "General"),
        })

    if not normalized_answers:
        raise ValueError("No valid interview answers were found.")

    prompt = f"""
You are a fair, constructive technical interview evaluator.

Target role: {role}

Evaluate each submitted answer independently.

ANSWERS:
{json.dumps(normalized_answers, ensure_ascii=False)}

Return ONLY a valid JSON object in this format:

{{
    "evaluations": [
        {{
            "score": 7.5,
            "relevance": 8,
            "depth": 7,
            "clarity": 8,
            "examples": 7,
            "feedback": "The answer is relevant but needs more detail.",
            "better_answer_tip": "Add a practical example and explain the result."
        }}
    ]
}}

Scoring:
- score: overall answer score from 0 to 10.
- relevance: how directly the answer addresses the question, 0 to 10.
- depth: correctness and depth of explanation, 0 to 10.
- clarity: organization and ease of understanding, 0 to 10.
- examples: use of relevant examples or evidence, 0 to 10.

Rules:
- Return one evaluation for every answer, in the same order.
- Keep each score between 0 and 10.
- Judge the actual answer, not the candidate's personality.
- Do not assume facts or experience the candidate did not state.
- Empty answers should receive a score of 0 and constructive feedback.
- Be specific about what was good and what should improve.
- Do not provide the same generic feedback for every answer.
- Do not include Markdown or text outside the JSON object.
"""

    response = ask_ai_json(prompt)
    result = _parse_json_response(response)

    raw_evaluations = result.get("evaluations", [])

    if not isinstance(raw_evaluations, list):
        raise ValueError(
            "The AI did not return a valid evaluations list."
        )

    evaluations = []

    for item in raw_evaluations[:len(normalized_answers)]:
        if not isinstance(item, dict):
            item = {}

        evaluations.append({
            "score": _safe_score(
                item.get("score", item.get("overall_score", 0))
            ),
            "relevance": _safe_score(item.get("relevance", 0)),
            "depth": _safe_score(item.get("depth", 0)),
            "clarity": _safe_score(item.get("clarity", 0)),
            "examples": _safe_score(item.get("examples", 0)),
            "feedback": _safe_text(
                item.get("feedback"),
                "No feedback was provided.",
            ),
            "better_answer_tip": _safe_text(
                item.get(
                    "better_answer_tip",
                    item.get("suggestion", ""),
                ),
                "Add specific details and a relevant example.",
            ),
        })

    # Fill any missing evaluations so results remain aligned with answers.
    while len(evaluations) < len(normalized_answers):
        evaluations.append({
            "score": 0.0,
            "relevance": 0.0,
            "depth": 0.0,
            "clarity": 0.0,
            "examples": 0.0,
            "feedback": "No evaluation was returned for this answer.",
            "better_answer_tip": (
                "Review the question and provide a clear, relevant example."
            ),
        })

    return {"evaluations": evaluations}


# =========================================================
# 5. GENERATE FINAL REPORT
# =========================================================

def final_report(
    analysis: dict,
    answers: list,
    evaluations: dict,
) -> dict:
    """
    Generate an overall performance report and study plan.

    Returns:
        {
            "strengths": list,
            "improvements": list,
            "study_plan": list,
            "message": str
        }
    """

    if not isinstance(analysis, dict):
        raise ValueError("Profile analysis must be a dictionary.")

    if not isinstance(answers, list) or not answers:
        raise ValueError("No interview answers are available.")

    if not isinstance(evaluations, dict):
        raise ValueError("Evaluations must be a dictionary.")

    evaluation_list = evaluations.get("evaluations", [])

    if not isinstance(evaluation_list, list) or not evaluation_list:
        raise ValueError("No answer evaluations are available.")

    valid_scores = []

    for item in evaluation_list:
        if isinstance(item, dict):
            valid_scores.append(
                _safe_score(
                    item.get("score", item.get("overall_score", 0))
                )
            )

    average_score = (
        sum(valid_scores) / len(valid_scores)
        if valid_scores
        else 0.0
    )

    prompt = f"""
You are an experienced interview coach.

Create a personalized final report using the actual interview results.

TARGET ROLE:
{analysis.get("role", "General")}

PROFILE ANALYSIS:
{json.dumps(analysis, ensure_ascii=False)}

ANSWERS:
{json.dumps(answers, ensure_ascii=False)}

EVALUATIONS:
{json.dumps(evaluations, ensure_ascii=False)}

Average answer score: {average_score:.2f}/10

Return ONLY a valid JSON object in this format:

{{
    "strengths": [
        "Explains core concepts clearly"
    ],
    "improvements": [
        "Include more practical examples"
    ],
    "study_plan": [
        "Day 1: Revise the most important technical concepts",
        "Day 2: Practise project-based questions",
        "Day 3: Practise behavioural questions using STAR"
    ],
    "message": "A short, encouraging, realistic summary of the candidate's performance."
}}

Rules:
- Base the report on the supplied answers and evaluations.
- Identify specific strengths and areas for improvement.
- Make the study plan practical and relevant to the target role.
- Do not invent experience, skills, or certifications.
- Do not guarantee selection or employment.
- Use clear, encouraging language.
- Do not include Markdown or text outside the JSON object.
"""

    response = ask_ai_json(prompt)
    result = _parse_json_response(response)

    return {
        "strengths": _normalize_skill_list(
            result.get("strengths")
        ),
        "improvements": _normalize_skill_list(
            result.get("improvements")
        ),
        "study_plan": _normalize_skill_list(
            result.get("study_plan")
        ),
        "message": _safe_text(
            result.get("message"),
            (
                f"You completed the interview with an average answer "
                f"score of {average_score:.1f}/10. Review the feedback "
                "and practise the recommended topics."
            ),
        ),
    }
