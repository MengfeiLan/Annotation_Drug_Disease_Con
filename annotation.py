import streamlit as st
import pandas as pd
from pathlib import Path
import re

# -----------------------
# Configuration
# -----------------------
DATA_PATH = "annotation_file.csv"
OUTPUT_PATH = "annotations.csv"

USERS = {
    "halil": "password123",
    "mengfei": "password456",
    "shiwei": "password789",
    "joe": "password101112"

}

LABELS = {
    "LLM is correct: there's a contradiction in the drug-disease association across the claims": "correct",
    "LLM is incorrect: there's no contradiction in the drug-disease association across the claims": "incorrect",
}

CONTEXTUAL_FACTORS = [
    "a. Species: The claims are based on different species that one claim is based on animal while another is based on another kind of animal or human.",
    "b. Population: The claims target different human subpopulations, such as differences in age, sex, genetic background, comorbidities, ethnicity, or risk profiles.",
    "c. Physiological context: The intervention is evaluated under different transient physiological or environmental conditions (e.g., exertion state, hypoxia, fasting status, or acute stress), even within the same species and population.",
    "d. Dosage or exposure duration: The same intervention is administered at different doses, frequencies, or durations.",
    "e. Route or mode of administration: The intervention is delivered via different routes (e.g., oral, intravenous, topical, sublingual, localized).",
    "f. Combined drug effects: The reported effect of a drug depends on its use in combination with other drugs or therapies.",
    "g. Evolving scientific evidence: The claims reflect different stages of scientific understanding.",
    "h. Known controversy or self-qualified claims: One or both claims explicitly acknowledge uncertainty.",
    "i. Ambiguous expression: One or both claims contain grammatical errors or unclear referents.",
    "j. Other: None of the listed factors explain the contradiction.",
]

# -----------------------
# Login
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("🔒 Annotator Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Logged in as {username}")
            # Instead of st.experimental_rerun(), just stop now
            st.stop()
        else:
            st.error("Invalid username or password")
    st.stop()  # Stop execution until login is successful


# -----------------------
# Helpers
# -----------------------
def scroll_to_top():
    st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

# -----------------------
# Load data
# -----------------------
@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)[:50]
df = load_data()

if Path(OUTPUT_PATH).exists():
    annotations = pd.read_csv(OUTPUT_PATH)
else:
    annotations = pd.DataFrame()

# Backward compatibility
for col in [
    "id",
    "label",
    "contextual_agreement",
    "contextual_factors",
    "contextual_explanation",
]:
    if col not in annotations.columns:
        annotations[col] = ""


# =======================
# 🔹 SIDEBAR: TRACE-BACK
# =======================
with st.sidebar:
    st.header("📌 Annotation Trace-back")

    total = len(df)
    done = annotations["id"].nunique()

    st.metric("Progress", f"{done} / {total}")

    st.markdown("---")

    annotated_ids = annotations["id"].tolist()

    if annotated_ids:
        selected_id = st.selectbox(
            "Jump to annotated example",
            options=annotated_ids,
        )

        if st.button("🔎 Go to selected example"):
            idx = df.index[df["id"] == selected_id][0]
            st.session_state.current_idx = idx
            st.rerun()

        st.markdown("### 🧾 Saved Annotation Preview")
        r = annotations[annotations["id"] == selected_id].iloc[0]
        st.write(f"**Label:** {r['label']}")
        st.write(f"**Contextual agreement:** {r['contextual_agreement']}")
        st.write(f"**Contextual factors:** {r['contextual_factors']}")
        if r["contextual_explanation"]:
            st.write(f"**Explaination for \"Other\" category:** {r['contextual_explanation']}")
    else:
        st.info("No annotations yet.")

# -----------------------
# Load / initialize annotations
# -----------------------
if Path(OUTPUT_PATH).exists():
    annotations = pd.read_csv(OUTPUT_PATH)
else:
    annotations = pd.DataFrame(
        columns=["id", "label", "contextual_factors", "contextual_explanation"]
    )

# -----------------------
# Session state
# -----------------------
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

if "label_radio" not in st.session_state:
    st.session_state.label_radio = None

if "selected_label" not in st.session_state:
    st.session_state.selected_label = None

if "contextual_factors" not in st.session_state:
    st.session_state.contextual_factors = []

if "contextual_explanation" not in st.session_state:
    st.session_state.contextual_explanation = ""

# -----------------------
# Load annotation for current example
# -----------------------
def load_existing_annotation(example_id):
    match = annotations[annotations["id"] == example_id]
    if not match.empty:
        r = match.iloc[0]
        st.session_state.label_radio = next(
            (k for k, v in LABELS.items() if v == r["label"]), None
        )
        st.session_state.selected_label = r["label"]
        st.session_state.contextual_factors = (
            r["contextual_factors"].split("; ")
            if pd.notna(r["contextual_factors"]) and r["contextual_factors"]
            else []
        )
        st.session_state.contextual_explanation = (
            r["contextual_explanation"]
            if pd.notna(r["contextual_explanation"])
            else ""
        )
    else:
        st.session_state.label_radio = None
        st.session_state.selected_label = None
        st.session_state.contextual_factors = []
        st.session_state.contextual_explanation = ""

# Clamp index
st.session_state.current_idx = max(
    0, min(st.session_state.current_idx, len(df) - 1)
)

row = df.iloc[st.session_state.current_idx]

if st.session_state.get("loaded_id") != row["id"]:
    load_existing_annotation(row["id"])
    st.session_state.loaded_id = row["id"]

# -----------------------
# UI
# -----------------------
st.set_page_config(layout="wide")
st.title("📝 Annotation for Drug–Disease Contradiction and Resolution")


st.write(f"Example {st.session_state.current_idx + 1} / {len(df)}")

st.markdown(
    """
Randomized controlled trials (RCTs) are the gold standard of biomedical evidence, 
while their findings can sometimes be contradictory. Drug–disease associations are 
especially important because they directly guide clinical decisions, inform drug 
repurposing efforts, and support health policy. Contradictory findings across 
studies can create confusion, hinder reliable evidence synthesis, and slow down 
the translation of research into practice. For example, during the COVID-19 
pandemic, conflicting trial results about treatments like hydroxychloroquine led 
to uncertainty in clinical decision-making. These challenges highlight the 
importance of developing automated systems that can systematically detect and 
resolve contradictory drug–disease claims, providing clinicians and researchers 
with a clearer, more reliable evidence base.

To address this, we developed an LLM-based pipeline designed to identify potential 
contradictions across large-scale RCT articles. The pipeline consists of three 
modules:

1. Claim Extraction – Automatically extracts scientific claims from RCT abstracts.  
2. Related Claim Pairing – Pairs semantically related claims using a combination of rule-based methods and dense embeddings.  
3. Contradiction Detection – Uses LLM prompting to determine whether claims in a pair can coexist or are contradictory.

We collected 224,756 RCT abstracts published between 2016 and 2025. Applying the 
pipeline, we detected 615 potential contradictions in drug–disease associations. 
These detected contradictions need human annotation to verify their accuracy. 
Therefore, the **Task 1** for annotators is to **decide whether the they agree 
with the LLM's contradiction judgment between two drug–disease claims.**

It is often unclear whether the detected contradiction reflects a genuine scientific 
disagreement or whether the claims describe conditionally opposing effects arising 
from different experimental or clinical contexts. Re-conducting biomedical experiments 
to reproduce drug effects is prohibitively time- and resource-intensive, making empirical 
replication infeasible to resolve contradictions at scale. Therefore, we leverage contextual 
interpretation to resolve biomedical contradictions by identifying differences in the contextual 
factors. We develop a taxonomy of contextual factors:

a. Species: Contradictions in drug–effect associations may result from cross-species differences.

b. Population: Claims may target different demographic or genetic subpopulations (e.g., age, sex, or location), leading to variant results.

c. Transient physiological context: Different results may arise when the same intervention is 
evaluated under different transient physiological conditions, even within the same species and 
population. Such contexts include exertion level, environmental conditions, current disease, or 
short-term physiological states.

d. Dosage and exposure duration: Different doses or exposure durations may produce different 
biological effects.

e. Route or mode of administration: Different delivery routes may change tissue targeting or absorption.

f. Evolving scientific evidence: Contradictions may reflect different stages of scientific 
understanding, where early hypotheses are later revised by new work.

g. Known controversy: Some claims explicitly acknowledge uncertainty or limitations, indicating an 
ongoing debate rather than a definitive conclusion.

h. Combined drug effect: Contradictions can arise when the effects of a drug depend on the co-administered 
agents. Drug–drug interactions may produce different outcomes across different combination regimens.

i. Other: Some contradictions may not fit into the above categories, indicating the need for additional contextual factors.

To support scalable and interpretable contradiction resolution, we use LLMs to identify whether 
contradictions can be explained by contextual differences defined in our taxonomy. The LLM is prompted 
to jointly analyze two claims with their context and assess whether their disagreements can be 
attributed to any contextual factor. Therefore, the **Task 2** for annotators is to **decide whether
they agree with the LLM's judgement of contextual factors that lead to disagreement between two claims. If 
disagree, the annotators are asked to select the taxonomy factors that could explain the contradiction.**


    """


)
# -----------------------
# Configuration
# -----------------------
DATA_PATH = "annotation_file.csv"
OUTPUT_PATH = "annotations.csv"

LABELS = {
    "LLM is correct: there's a contradiction in the drug-disease association across the claims": "correct",
    "LLM is incorrect: there's no contradiction in the drug-disease association across the claims": "incorrect",
}

CONTEXTUAL_FACTORS = [
    "a. Species: The claims are based on different species that one claim is based on animal while another is based on another kind of animal or human.",
    "b. Population: The claims target different human subpopulations, such as differences in age, sex, genetic background, comorbidities, ethnicity, or risk profiles.",
    "c. Physiological context: The intervention is evaluated under different transient physiological or environmental conditions (e.g., exertion state, hypoxia, fasting status, or acute stress), even within the same species and population.",
    "d. Dosage or exposure duration: The same intervention is administered at different doses, frequencies, or durations.",
    "e. Route or mode of administration: The intervention is delivered via different routes (e.g., oral, intravenous, topical, sublingual, localized).",
    "f. Combined drug effects: The reported effect of a drug depends on its use in combination with other drugs or therapies.",
    "g. Evolving scientific evidence: The claims reflect different stages of scientific understanding.",
    "h. Known controversy or self-qualified claims: One or both claims explicitly acknowledge uncertainty.",
    "i. Ambiguous expression: One or both claims contain grammatical errors or unclear referents.",
    "j. Other: None of the listed factors explain the contradiction.",
]

# -----------------------
# Helpers
# -----------------------
def scroll_to_top():
    st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

# -----------------------
# Load data
# -----------------------
@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)

df = load_data()

# -----------------------
# Load / initialize annotations
# -----------------------
if Path(OUTPUT_PATH).exists():
    annotations = pd.read_csv(OUTPUT_PATH)
else:
    annotations = pd.DataFrame()

# -----------------------
# Backward compatibility (IMPORTANT)
# -----------------------
for col in [
    "id",
    "label",
    "contextual_agreement",
    "contextual_factors",
    "contextual_explanation",
]:
    if col not in annotations.columns:
        annotations[col] = ""

# -----------------------
# Session state
# -----------------------
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

if "label_radio" not in st.session_state:
    st.session_state.label_radio = None

if "selected_label" not in st.session_state:
    st.session_state.selected_label = None

if "contextual_agreement" not in st.session_state:
    st.session_state.contextual_agreement = None

if "contextual_factors" not in st.session_state:
    st.session_state.contextual_factors = []

if "contextual_explanation" not in st.session_state:
    st.session_state.contextual_explanation = ""

# -----------------------
# Load annotation for current example
# -----------------------
def load_existing_annotation(example_id):
    match = annotations[annotations["id"] == example_id]

    if not match.empty:
        r = match.iloc[0]

        st.session_state.label_radio = next(
            (k for k, v in LABELS.items() if v == r["label"]), None
        )
        st.session_state.selected_label = r["label"] or None

        st.session_state.contextual_agreement = (
            r["contextual_agreement"] if r["contextual_agreement"] else None
        )

        if r["contextual_factors"] and r["contextual_factors"] != "Agree":
            st.session_state.contextual_factors = r["contextual_factors"].split("; ")
        else:
            st.session_state.contextual_factors = []

        st.session_state.contextual_explanation = r["contextual_explanation"] or ""
    else:
        st.session_state.label_radio = None
        st.session_state.selected_label = None
        st.session_state.contextual_agreement = None
        st.session_state.contextual_factors = []
        st.session_state.contextual_explanation = ""

# Clamp index
st.session_state.current_idx = max(
    0, min(st.session_state.current_idx, len(df) - 1)
)

row = df.iloc[st.session_state.current_idx]

if st.session_state.get("loaded_id") != row["id"]:
    load_existing_annotation(row["id"])
    st.session_state.loaded_id = row["id"]

# -----------------------
# Display claims
# -----------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Claim 1")
    st.info(re.sub(r"\.(?=[A-Z])", ". ", row["claim_1"]))
    with st.expander("Claim 1 – Metadata"):
        st.write(f"**PMID:** {row['pmid_1']}")
        st.write(row["claims_abs_1"])

with col2:
    st.subheader("Claim 2")
    st.info(re.sub(r"\.(?=[A-Z])", ". ", row["claim_2"]))
    with st.expander("Claim 2 – Metadata"):
        st.write(f"**PMID:** {row['pmid_2']}")
        st.write(re.sub(r"\.(?=[A-Z])", ". ", row["claims_abs_2"]))


# ----------------------- # LLM reasoning # ----------------------- st.markdown("---")
st.subheader("🤖 Task 1: Annotation for Contradiction Detection")
with st.container(border=True):
    col_l, col_r, col_n = st.columns(3)
    with col_l:
        st.markdown("### Structured Extraction")
        st.write(f"**Drug:** {row.get('drug', 'N/A')}")
        st.write(f"**Disease:** {row.get('disease', 'N/A')}")
        st.markdown("**Claim 1 Relation:**")
        st.code(str(row.get("claim_1_dd_relation", "")))
        st.markdown("**Claim 2 Relation:**")
        st.code(str(row.get("claim_2_dd_relation", "")))
    with col_r:
        st.markdown("### LLM Explanation")
        st.text_area( "", value=str(row.get("reasoning", "")).replace("Task(1): ", "").replace("Task(2): ", ""), height=220, disabled=True, )
    with col_n:
        st.markdown("### LLM Decision")
        st.write(f"**{row.get('prediction', 'N/A')}**")
# -----------------------
# Task 1: Contradiction
# -----------------------

st.markdown(
    "<p style='color:red; font-size:22px; font-weight:600;'>Is the LLM correct?</p>",
    unsafe_allow_html=True,
)

st.radio(
    "",
    options=list(LABELS.keys()),
    key="label_radio",
)

st.session_state.selected_label = LABELS.get(st.session_state.label_radio)

# -----------------------
# Task 2: Contextual Resolution
# -----------------------
if st.session_state.selected_label == "correct":
    st.markdown("---")
    st.subheader("🧩 Task 2: Contextual Resolution")

    with st.container(border=True):
        st.markdown("### 🤖 LLM Contextual Judgment")
        st.write(f"**{row.get('contextual_factor', 'N/A')}**")

        if row.get("contextual_factor_explanation"):
            st.text_area(
                "",
                value=row["contextual_factor_explanation"],
                height=180,
                disabled=True,
            )

    st.markdown(
        "<p style='color:red; font-size:22px; font-weight:600;'>Do you agree with the LLM’s contextual judgment?</p>",
        unsafe_allow_html=True,
    )

    st.radio(
        "",
        options=["Agree", "Disagree"],
        key="contextual_agreement",
        horizontal=True,
    )

    if st.session_state.contextual_agreement == "Disagree":
        st.multiselect(
            "Which contextual factors explain the contradiction?",
            options=CONTEXTUAL_FACTORS,
            key="contextual_factors",
        )

        st.text_area(
            "If choose \"Other - None of the listed factors explain the contradiction\", explain:",
            key="contextual_explanation",
            height=120,
        )

    if st.session_state.contextual_agreement == "Agree":
        st.session_state.contextual_factors = []
        st.session_state.contextual_explanation = ""

# -----------------------
# Save annotation helper
# -----------------------
def save_annotation():
    global annotations

    new_row = {
        "id": row["id"],
        "label": st.session_state.selected_label,
        "contextual_agreement": st.session_state.contextual_agreement or "",
        "contextual_factors": (
            "Agree"
            if st.session_state.contextual_agreement == "Agree"
            else "; ".join(st.session_state.contextual_factors)
        ),
        "contextual_explanation": (
            ""
            if st.session_state.contextual_agreement == "Agree"
            else st.session_state.contextual_explanation.strip()
        ),
        "annotator": st.session_state.username,  # <--- Add user here
    }

    annotations = annotations[annotations["id"] != row["id"]]
    annotations = pd.concat([annotations, pd.DataFrame([new_row])], ignore_index=True)
    annotations.to_csv(OUTPUT_PATH, index=False)

# -----------------------
# Navigation + Submit
# -----------------------
st.markdown("---")
col_prev, col_submit, col_next = st.columns([1, 2, 1])

with col_prev:
    if st.button("⬅ Previous", disabled=st.session_state.current_idx == 0):
        st.session_state.current_idx -= 1
        st.rerun()
        scroll_to_top()

with col_submit:
    if st.button("💾 Save annotation", use_container_width=True):
        if st.session_state.selected_label is None:
            st.warning("Please select whether the LLM is correct.")
        elif (
            st.session_state.selected_label == "correct"
            and st.session_state.contextual_agreement is None
        ):
            st.warning("Please indicate agreement with the LLM’s contextual judgment.")
        elif (
            st.session_state.selected_label == "correct"
            and st.session_state.contextual_agreement == "Disagree"
            and not st.session_state.contextual_factors
        ):
            st.warning("Please select at least one contextual factor.")
        else:
            save_annotation()
            st.success("Annotation saved.")

with col_next:
    if st.button("Next ➡", disabled=st.session_state.current_idx == len(df) - 1):
        save_annotation()
        st.session_state.current_idx += 1
        st.rerun()

        scroll_to_top()
