import streamlit as st
from optimizer import run_optimizer

st.set_page_config(
    page_title="CV Optimizer",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
    .score-big { font-size: 64px; font-weight: 800; line-height: 1; }
    .score-label { font-size: 14px; color: #888; margin-top: 4px; }
    .score-card { background: #0e1117; border-radius: 12px; padding: 24px; text-align: center; border: 1px solid #222; }
    .metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1e1e1e; }
    .status-box { background: #0a1628; border-left: 3px solid #3b82f6; padding: 12px 16px; border-radius: 4px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 CV Optimizer Agent")
st.caption("Paste any CV + job description. The agent rewrites and scores until it hits 97%+.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Your CV")
    cv_input = st.text_area(
        label="Paste CV here",
        placeholder="Paste the full CV text here...",
        height=420,
        label_visibility="collapsed"
    )

with col2:
    st.subheader("Job Description")
    jd_input = st.text_area(
        label="Paste job description here",
        placeholder="Paste the full job description here...",
        height=420,
        label_visibility="collapsed"
    )

target = st.slider("Target score", min_value=90, max_value=99, value=97, step=1)

run_btn = st.button("🚀 Optimize CV", type="primary", use_container_width=True)

if run_btn:
    if not cv_input.strip() or not jd_input.strip():
        st.error("Please paste both a CV and a job description.")
        st.stop()

    st.divider()

    status_area = st.empty()
    results_area = st.empty()

    original_score = None
    final_score = None
    optimized_cv = None

    for update in run_optimizer(cv_input, jd_input, target=target):
        step = update["step"]

        if step == "scoring_original":
            with status_area.container():
                st.markdown(f'<div class="status-box">📊 {update["message"]}</div>', unsafe_allow_html=True)

        elif step == "original_scored":
            original_score = update["score"]
            with status_area.container():
                st.markdown(f'<div class="status-box">📊 Original score: <strong>{original_score["total_score"]}%</strong></div>', unsafe_allow_html=True)

        elif step == "optimizing":
            with status_area.container():
                st.markdown(f'<div class="status-box">✍️ {update["message"]}</div>', unsafe_allow_html=True)

        elif step == "scoring_optimized":
            with status_area.container():
                st.markdown(f'<div class="status-box">🔍 {update["message"]}</div>', unsafe_allow_html=True)

        elif step == "attempt_result":
            score = update["score"]
            total = score["total_score"]
            optimized_cv = update["cv"]
            icon = "✅" if total >= target else "🔄"
            with status_area.container():
                st.markdown(f'<div class="status-box">{icon} Attempt {update["attempt"]}: <strong>{total}%</strong></div>', unsafe_allow_html=True)

        elif step == "refining":
            with status_area.container():
                st.markdown(f'<div class="status-box">⚡ {update["message"]}</div>', unsafe_allow_html=True)

        elif step == "done":
            final_score = update["final_score"]
            optimized_cv = update["optimized_cv"]
            original_score = update["original_score"]

            status_area.empty()

            # ── Score cards ──────────────────────────────────────────
            st.subheader("Results")

            before_score = original_score.get("total_score", 0)
            after_score = final_score.get("total_score", 0)

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("Before", f"{before_score}%", delta=None)

            with c2:
                delta = after_score - before_score
                st.metric("After", f"{after_score}%", delta=f"+{delta}%")

            with c3:
                hire_label = "🟢 Strong hire" if after_score >= 97 else "🟡 Good" if after_score >= 90 else "🔴 Needs work"
                st.metric("Verdict", hire_label)

            # ── Breakdown ─────────────────────────────────────────────
            st.subheader("Score Breakdown")
            breakdown_cols = st.columns(4)
            metrics = [
                ("Keyword Match", "keyword_match"),
                ("Experience Relevance", "experience_relevance"),
                ("Seniority Fit", "seniority_fit"),
                ("Language Alignment", "language_alignment"),
            ]
            for i, (label, key) in enumerate(metrics):
                with breakdown_cols[i]:
                    before_val = original_score.get(key, 0)
                    after_val = final_score.get(key, 0)
                    st.metric(label, f"{after_val}%", delta=f"+{after_val - before_val}%")

            # ── Optimized CV ───────────────────────────────────────────
            st.divider()
            left, right = st.columns(2)

            with left:
                st.subheader("Original CV")
                st.text_area(
                    label="original",
                    value=cv_input,
                    height=600,
                    label_visibility="collapsed",
                    disabled=True
                )

            with right:
                st.subheader(f"Optimized CV — {after_score}%")
                st.text_area(
                    label="optimized",
                    value=optimized_cv,
                    height=600,
                    label_visibility="collapsed"
                )
                st.download_button(
                    label="⬇️ Download Optimized CV",
                    data=optimized_cv,
                    file_name="optimized_cv.txt",
                    mime="text/plain",
                    use_container_width=True
                )
