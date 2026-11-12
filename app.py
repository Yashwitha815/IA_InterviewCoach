
import streamlit as st
import json
import pandas as pd
from io import BytesIO
from pypdf import PdfReader

from coach import (
    analyze_profile,
    generate_questions,
    evaluate_answers,
    final_report,
)


# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AI Interview Coach",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 2. SESSION STATE INITIALIZATION
# =========================================================

def initialize_session_state():
    """Initialize session variables used throughout the application."""

    defaults = {
        "resume_text": "",
        "resume_name": "",
        "job_description": "",
        "analysis": None,
        "questions": [],
        "answers": [],
        "evaluations": None,
        "report": None,
        "current_question": 0,
        "interview_started": False,
        "interview_completed": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()


# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

def reset_interview():
    """Clear interview progress and generated results."""

    st.session_state.questions = []
    st.session_state.answers = []
    st.session_state.evaluations = None
    st.session_state.report = None
    st.session_state.current_question = 0
    st.session_state.interview_started = False
    st.session_state.interview_completed = False


def extract_resume_text(uploaded_file):
    """Extract readable text from an uploaded PDF resume."""

    try:
        pdf_reader = PdfReader(BytesIO(uploaded_file.getvalue()))

        if pdf_reader.is_encrypted:
            raise ValueError(
                "The PDF is password-protected. Upload an unlocked PDF."
            )

        pages = []

        for page in pdf_reader.pages:
            pages.append(page.extract_text() or "")

        text = "\n".join(pages).strip()

        if not text:
            raise ValueError(
                "No readable text was found. Please upload a text-based PDF."
            )

        return text

    except Exception as exc:
        if isinstance(exc, ValueError):
            raise

        raise ValueError(
            f"Could not read the PDF: {exc}"
        ) from exc


def normalize_questions(raw_questions):
    """Convert generated questions into a consistent list of dictionaries."""

    if isinstance(raw_questions, dict):
        raw_questions = raw_questions.get("questions", [])

    if not isinstance(raw_questions, list):
        return []

    normalized = []

    for item in raw_questions:
        if isinstance(item, str):
            question = item.strip()

            if question:
                normalized.append({
                    "question": question,
                    "type": "technical",
                    "skill": "General",
                })

        elif isinstance(item, dict):
            question = str(item.get("question", "")).strip()

            if question:
                normalized.append({
                    "question": question,
                    "type": str(item.get("type", "technical")),
                    "skill": str(item.get("skill", "General")),
                })

    return normalized


def get_numeric_score(value):
    """Safely convert an AI-generated score to a number between 0 and 10."""

    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def make_downloadable_json(data):
    """Convert a Python object into downloadable JSON bytes."""

    return json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


# =========================================================
# 4. SIDEBAR
# =========================================================

with st.sidebar:
    st.title("🎯 AI Interview Coach")

    st.write(
        "Prepare for interviews using your resume, "
        "job description, and AI-powered feedback."
    )

    st.divider()

    st.subheader("📌 Workflow")

    st.markdown(
        """
        1. Upload your resume
        2. Enter the job description
        3. Analyze your profile
        4. Generate interview questions
        5. Answer the questions
        6. Review your scorecard
        """
    )

    st.divider()

    if st.button("🔄 Reset Interview", use_container_width=True):
        reset_interview()
        st.rerun()


# =========================================================
# 5. MAIN HEADER
# =========================================================

st.title("🎯 AI-Powered Interview Coach")

st.write(
    "Upload your resume, compare it with a job description, "
    "practice personalized interview questions, and receive "
    "AI-generated feedback."
)

st.divider()


# =========================================================
# 6. RESUME UPLOAD
# =========================================================

st.header("📄 Step 1: Upload Your Resume")

uploaded_file = st.file_uploader(
    "Choose your resume in PDF format",
    type=["pdf"],
    help="Upload a text-based PDF resume.",
)

if uploaded_file is not None:
    if (
        st.session_state.resume_name != uploaded_file.name
        or not st.session_state.resume_text
    ):
        try:
            extracted_text = extract_resume_text(uploaded_file)

            st.session_state.resume_text = extracted_text
            st.session_state.resume_name = uploaded_file.name

            # A new resume invalidates previously generated results.
            st.session_state.analysis = None
            st.session_state.job_description = ""
            reset_interview()

            st.success("Resume uploaded and text extracted successfully!")

        except ValueError as exc:
            st.error(str(exc))

    if st.session_state.resume_text:
        with st.expander("👀 Preview extracted resume text"):
            st.text_area(
                "Resume content",
                value=st.session_state.resume_text,
                height=220,
                disabled=True,
            )


# =========================================================
# 7. JOB DESCRIPTION
# =========================================================

st.header("💼 Step 2: Enter the Job Description")

job_description = st.text_area(
    "Paste the job description here",
    value=st.session_state.job_description,
    height=220,
    placeholder=(
        "Example: We are looking for a Python developer "
        "with knowledge of Python, SQL, APIs, and problem-solving..."
    ),
)

if job_description != st.session_state.job_description:
    st.session_state.job_description = job_description.strip()

    # Clear results if the target role changes.
    st.session_state.analysis = None
    reset_interview()


# =========================================================
# 8. RESUME AND JOB DESCRIPTION ANALYSIS
# =========================================================

st.header("🔍 Step 3: Analyze Your Profile")

if st.button(
    "Analyze My Profile",
    type="primary",
    use_container_width=True,
):
    if not st.session_state.resume_text:
        st.warning("Please upload a readable PDF resume first.")

    elif not st.session_state.job_description.strip():
        st.warning("Please enter a job description first.")

    else:
        try:
            with st.spinner("Analyzing your resume and job description..."):
                analysis_result = analyze_profile(
                    st.session_state.resume_text,
                    st.session_state.job_description,
                )

            if not isinstance(analysis_result, dict):
                raise ValueError(
                    "Profile analysis must return a dictionary."
                )

            st.session_state.analysis = analysis_result
            reset_interview()

            st.success("Profile analysis completed!")

        except Exception as exc:
            st.error(f"Profile analysis failed: {exc}")


# =========================================================
# 9. DISPLAY PROFILE ANALYSIS
# =========================================================

analysis = st.session_state.analysis

if analysis:
    st.divider()
    st.header("📊 Your Profile Analysis")

    candidate_name = analysis.get(
        "candidate_name", "Candidate"
    )
    role = analysis.get(
        "role", "Target Role"
    )
    match_score = get_numeric_score(
        analysis.get("match_score", 0)
    )

    # Match score is expected to be a percentage.
    match_score = max(0.0, min(100.0, match_score * 10
        if 0 <= match_score <= 10 and
        isinstance(analysis.get("match_score"), float)
        else match_score
    )) if False else max(0.0, min(
        100.0, float(analysis.get("match_score", 0) or 0)
    ))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Candidate", str(candidate_name))

    with col2:
        st.metric("Target Role", str(role))

    with col3:
        st.metric("Resume Match", f"{match_score:.0f}%")

    st.progress(int(match_score))

    st.subheader("📝 Summary")
    st.write(
        analysis.get(
            "summary",
            "No summary was provided by the analysis function.",
        )
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("✅ Matching Skills")

        matching_skills = analysis.get("matching_skills", [])

        if matching_skills:
            for skill in matching_skills:
                st.markdown(f"- {skill}")
        else:
            st.info("No matching skills were returned.")

    with col2:
        st.subheader("📚 Skills to Improve")

        missing_skills = analysis.get("missing_skills", [])

        if missing_skills:
            for skill in missing_skills:
                st.markdown(f"- {skill}")
        else:
            st.success("No missing skills were identified.")

    with st.expander("View complete analysis"):
        st.json(analysis)


# =========================================================
# 10. GENERATE INTERVIEW QUESTIONS
# =========================================================

if analysis:
    st.divider()
    st.header("❓ Step 4: Generate Interview Questions")

    number_of_questions = st.slider(
        "Number of interview questions",
        min_value=3,
        max_value=10,
        value=5,
    )

    if st.button(
        "Generate Questions",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Generating personalized questions..."):
                raw_questions = generate_questions(
                    analysis,
                    st.session_state.resume_text,
                    st.session_state.job_description,
                    num_questions=number_of_questions,
                )

            questions = normalize_questions(raw_questions)

            if not questions:
                raise ValueError(
                    "No valid questions were generated. Try again."
                )

            st.session_state.questions = questions
            st.session_state.answers = []
            st.session_state.evaluations = None
            st.session_state.report = None
            st.session_state.current_question = 0
            st.session_state.interview_started = False
            st.session_state.interview_completed = False

            st.success(
                f"Generated {len(questions)} interview questions!"
            )

        except Exception as exc:
            st.error(f"Question generation failed: {exc}")


# =========================================================
# 11. DISPLAY GENERATED QUESTIONS
# =========================================================

questions = st.session_state.questions

if questions:
    st.subheader("Your Personalized Questions")

    for index, question_data in enumerate(questions, start=1):
        with st.expander(f"Question {index}"):
            st.write(question_data["question"])
            st.caption(
                f"Type: {question_data['type']} | "
                f"Skill: {question_data['skill']}"
            )


# =========================================================
# 12. INTERACTIVE MOCK INTERVIEW
# =========================================================

if questions:
    st.divider()
    st.header("🎤 Step 5: Mock Interview")

    if not st.session_state.interview_started:
        st.write(
            "Answer each question in your own words. "
            "Your answers will be evaluated after you finish."
        )

        if st.button(
            "Start Interview",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.interview_started = True
            st.session_state.current_question = 0
            st.session_state.answers = []
            st.session_state.interview_completed = False
            st.rerun()

    if (
        st.session_state.interview_started
        and not st.session_state.interview_completed
    ):
        current_index = st.session_state.current_question

        if current_index < len(questions):
            question_data = questions[current_index]

            st.progress(
                (current_index + 1) / len(questions)
            )

            st.caption(
                f"Question {current_index + 1} "
                f"of {len(questions)}"
            )

            st.subheader(question_data["question"])

            st.caption(
                f"Category: {question_data['type']} | "
                f"Skill: {question_data['skill']}"
            )

            answer_key = f"answer_{current_index}"

            answer_text = st.text_area(
                "Your answer",
                key=answer_key,
                height=180,
                placeholder="Write your interview answer here...",
            )

            if st.button(
                "Submit Answer",
                type="primary",
                key=f"submit_{current_index}",
            ):
                if not answer_text.strip():
                    st.warning(
                        "Please enter an answer before continuing."
                    )
                else:
                    st.session_state.answers.append({
                        "question": question_data["question"],
                        "type": question_data["type"],
                        "skill": question_data["skill"],
                        "answer": answer_text.strip(),
                    })

                    if current_index + 1 < len(questions):
                        st.session_state.current_question += 1
                        st.rerun()
                    else:
                        st.session_state.interview_completed = True
                        st.session_state.interview_started = False
                        st.success(
                            "🎉 You have answered all the questions!"
                        )
                        st.rerun()

        else:
            st.session_state.interview_completed = True
            st.session_state.interview_started = False
            st.rerun()


# =========================================================
# 13. EVALUATE ANSWERS
# =========================================================

if (
    st.session_state.interview_completed
    and st.session_state.answers
):
    st.divider()
    st.header("🧠 Step 6: Evaluate Your Answers")

    st.write(
        "The AI will evaluate relevance, depth, clarity, "
        "examples, and opportunities for improvement."
    )

    if st.button(
        "Evaluate My Answers",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Evaluating your interview answers..."):
                evaluation_result = evaluate_answers(
                    st.session_state.answers,
                    st.session_state.analysis.get(
                        "role", "General"
                    ),
                )

            if isinstance(evaluation_result, list):
                evaluation_result = {
                    "evaluations": evaluation_result
                }

            if not isinstance(evaluation_result, dict):
                raise ValueError(
                    "Answer evaluation must return a dictionary or list."
                )

            evaluations = evaluation_result.get("evaluations", [])

            if not isinstance(evaluations, list):
                raise ValueError(
                    "The evaluations field must contain a list."
                )

            if not evaluations:
                raise ValueError(
                    "The AI did not return any answer evaluations."
                )

            st.session_state.evaluations = evaluation_result
            st.session_state.report = None

            st.success("Answer evaluation completed!")

        except Exception as exc:
            st.error(f"Answer evaluation failed: {exc}")


# =========================================================
# 14. DISPLAY EVALUATION RESULTS
# =========================================================

evaluation_result = st.session_state.evaluations

if evaluation_result:
    evaluations = evaluation_result.get("evaluations", [])

    st.subheader("📋 Individual Answer Feedback")

    scores = []

    for index, answer_data in enumerate(
        st.session_state.answers
    ):
        if index >= len(evaluations):
            break

        evaluation = evaluations[index]

        if not isinstance(evaluation, dict):
            continue

        question_text = answer_data["question"]

        score = get_numeric_score(
            evaluation.get(
                "score",
                evaluation.get("overall_score", 0),
            )
        )

        scores.append(score)

        with st.expander(
            f"Question {index + 1} — Score: {score:.1f}/10",
            expanded=(index == 0),
        ):
            st.markdown("**Question**")
            st.write(question_text)

            st.markdown("**Your Answer**")
            st.write(answer_data["answer"])

            st.markdown("**Feedback**")
            st.write(
                evaluation.get(
                    "feedback",
                    "No feedback provided.",
                )
            )

            score_fields = [
                ("Relevance", "relevance"),
                ("Depth", "depth"),
                ("Clarity", "clarity"),
                ("Examples", "examples"),
            ]

            cols = st.columns(4)

            for col, (label, field) in zip(cols, score_fields):
                with col:
                    value = evaluation.get(field)

                    if value is not None:
                        st.metric(
                            label,
                            f"{get_numeric_score(value):.1f}/10",
                        )

            tip = evaluation.get(
                "better_answer_tip",
                evaluation.get("suggestion", ""),
            )

            if tip:
                st.markdown("**💡 How to Improve**")
                st.write(tip)

    if scores:
        average_score = sum(scores) / len(scores)

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Average Answer Score",
                f"{average_score:.1f}/10",
            )

        with col2:
            st.metric(
                "Evaluated Answers",
                len(scores),
            )


# =========================================================
# 15. FINAL SCORECARD AND IMPROVEMENT PLAN
# =========================================================

if st.session_state.evaluations:
    st.divider()
    st.header("🏆 Step 7: Final Scorecard")

    if st.button(
        "Generate Final Report",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Preparing your final scorecard..."):
                report = final_report(
                    st.session_state.analysis,
                    st.session_state.answers,
                    st.session_state.evaluations,
                )

            if not isinstance(report, dict):
                raise ValueError(
                    "The final report must be a dictionary."
                )

            st.session_state.report = report
            st.success("Your final report is ready!")

        except Exception as exc:
            st.error(f"Could not generate the final report: {exc}")


# =========================================================
# 16. DISPLAY FINAL REPORT AND DOWNLOAD
# =========================================================

report = st.session_state.report

if report:
    st.subheader("🌟 Overall Performance")

    strengths = report.get("strengths", [])
    improvements = report.get("improvements", [])
    study_plan = report.get("study_plan", [])
    message = report.get("message", "")

    if message:
        st.info(message)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ Strengths")

        if isinstance(strengths, list) and strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        elif strengths:
            st.write(strengths)
        else:
            st.write("No strengths were returned.")

    with col2:
        st.markdown("### 📈 Areas to Improve")

        if isinstance(improvements, list) and improvements:
            for item in improvements:
                st.markdown(f"- {item}")
        elif improvements:
            st.write(improvements)
        else:
            st.write("No improvement areas were returned.")

    st.markdown("### 📚 Personalized Study Plan")

    if isinstance(study_plan, list) and study_plan:
        for index, item in enumerate(study_plan, start=1):
            st.markdown(f"{index}. {item}")
    elif study_plan:
        st.write(study_plan)
    else:
        st.write("No study plan was returned.")

    st.subheader("📥 Download Your Scorecard")

    download_data = {
        "profile_analysis": st.session_state.analysis,
        "questions_and_answers": st.session_state.answers,
        "evaluations": st.session_state.evaluations,
        "final_report": report,
    }

    st.download_button(
        label="Download Scorecard (JSON)",
        data=make_downloadable_json(download_data),
        file_name="ai_interview_scorecard.json",
        mime="application/json",
        use_container_width=True,
    )

    # Create an Excel-friendly table of answers and feedback.
    evaluation_list = st.session_state.evaluations.get(
        "evaluations", []
    )

    rows = []

    for index, answer_data in enumerate(
        st.session_state.answers
    ):
        evaluation = (
            evaluation_list[index]
            if index < len(evaluation_list)
            and isinstance(evaluation_list[index], dict)
            else {}
        )

        rows.append({
            "Question": answer_data["question"],
            "Type": answer_data["type"],
            "Skill": answer_data["skill"],
            "Your Answer": answer_data["answer"],
            "Score": evaluation.get(
                "score",
                evaluation.get("overall_score", ""),
            ),
            "Relevance": evaluation.get("relevance", ""),
            "Depth": evaluation.get("depth", ""),
            "Clarity": evaluation.get("clarity", ""),
            "Examples": evaluation.get("examples", ""),
            "Feedback": evaluation.get("feedback", ""),
            "Improvement Tip": evaluation.get(
                "better_answer_tip",
                evaluation.get("suggestion", ""),
            ),
        })

    if rows:
        excel_buffer = BytesIO()

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl",
        ) as writer:
            pd.DataFrame(rows).to_excel(
                writer,
                index=False,
                sheet_name="Interview Scorecard",
            )

        st.download_button(
            label="Download Scorecard (Excel)",
            data=excel_buffer.getvalue(),
            file_name="ai_interview_scorecard.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    st.success(
        "🎉 Great job! Review your feedback and use the study plan "
        "to prepare for your next interview."
    )


# =========================================================
# 17. FOOTER
# =========================================================

st.divider()

st.caption(
    "AI Interview Coach | Practice, evaluate, and improve. "
    "AI-generated scores and suggestions are estimates, "
    "not guarantees of interview performance."
)
