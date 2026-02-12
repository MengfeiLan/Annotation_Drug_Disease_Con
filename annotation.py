import streamlit as st
import pandas as pd
from pathlib import Path
import re
import os
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
from github import Github
import base64

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]  # replace with a secret in Streamlit secrets
REPO_NAME = "MengfeiLan/Annotation_Drug_Disease_Con"
st.set_page_config(
    page_title="Drug–Disease Annotation",   # The tab title
    page_icon="💊",                          # Can be an emoji, or a local image file path
    layout="wide",
    initial_sidebar_state="expanded"
)
st.set_page_config(
    page_title="Drug–Disease Annotation",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def load_annotations_from_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    try:
        file = repo.get_contents(GITHUB_FILE_PATH)
        content = file.decoded_content.decode()
        return pd.read_csv(pd.compat.StringIO(content))
    except:
        return pd.DataFrame()


# -----------------------
# Configuration
# -----------------------
DATA_PATH = "annotation_file.csv"

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

ANNOTATION_DIR = Path("annotations")
ANNOTATION_DIR.mkdir(exist_ok=True)

OUTPUT_PATH = ANNOTATION_DIR / f"{st.session_state.username}.csv"

def push_annotations_to_github(local_file_path, commit_msg="Update annotations"):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    local_file_path = local_file_path.as_posix()
    # Read local CSV content
    with open(local_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    print(local_file_path)
    try:
        # Try to get the file from repo
        file = repo.get_contents(local_file_path)
        repo.update_file(file.path, commit_msg, content, file.sha)
    except:
        # If file doesn't exist, create it
        repo.create_file(local_file_path, commit_msg, content)

# -----------------------
# Helpers
# -----------------------
def scroll_to_top():
    st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

# -----------------------
# Load data
# -----------------------


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


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)[:50]

df = load_data()

# -----------------------
# Load per-user annotations
# -----------------------
USER_CSV = ANNOTATION_DIR / f"{st.session_state.username}.csv"
if USER_CSV.exists():
    annotations = pd.read_csv(USER_CSV)
else:
    annotations = pd.DataFrame(columns=[
        "id", "label", "contextual_agreement", "contextual_factors",
        "contextual_explanation", "annotator"
    ])

# -----------------------
# Sidebar: Progress & Traceback
# -----------------------
with st.sidebar:
    st.header("📌 Annotation Trace-back")
    user_annotations = annotations

    total = len(df)
    done = user_annotations["id"].nunique()
    st.metric("Progress", f"{done} / {total}")

    st.markdown("---")
    annotated_ids = user_annotations["id"].tolist()
    if annotated_ids:
        # selected_id = st.selectbox("Jump to annotated example", options=annotated_ids)
        # if st.button("🔎 Go to selected example"):
        #     idx = df.index[df["id"] == selected_id][0]
        #     st.session_state.current_idx = idx
        #     st.stop()

        # store selected annotated example
        if "selected_example_id" not in st.session_state:
            st.session_state.selected_example_id = None
        
        selected_id = st.selectbox(
            "Jump to annotated example", options=annotated_ids,
            index=annotated_ids.index(st.session_state.selected_example_id) if st.session_state.selected_example_id in annotated_ids else 0
        )
        
        st.session_state.selected_example_id = selected_id
        
        if st.button("🔎 Go to selected example"):
            # find index of the selected example in the main dataframe
            idx = df.index[df["id"] == st.session_state.selected_example_id][0]
            st.session_state.current_idx = idx
            st.rerun()  # rerun so UI updates to the selected example

        r = user_annotations[user_annotations["id"] == selected_id].iloc[0]
        st.markdown("### 🧾 Saved Annotation Preview")
        st.write(f"**Label:** {r['label']}")
        st.write(f"**Contextual agreement:** {r['contextual_agreement']}")
        st.write(f"**Contextual factors:** {r['contextual_factors']}")
        if r["contextual_explanation"]:
            st.write(f"**Explanation for \"Other\":** {r['contextual_explanation']}")
    else:
        st.info("No annotations yet for your account.")




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
    # No need to filter by annotator
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

with st.expander("Annotation Guideline"):
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


if "annotator" not in annotations.columns:
    annotations["annotator"] = ""


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
# Helper: Load existing annotation
# -----------------------
def load_existing_annotation(example_id):
    match = annotations[(annotations["id"] == example_id) &
                        (annotations["annotator"] == st.session_state.username)]
    if not match.empty:
        r = match.iloc[0]
        st.session_state.label_radio = next((k for k, v in LABELS.items() if v == r["label"]), None)
        st.session_state.selected_label = r["label"]
        st.session_state.contextual_agreement = r["contextual_agreement"] or None
        st.session_state.contextual_factors = r["contextual_factors"].split("; ") if pd.notna(r["contextual_factors"]) and r["contextual_factors"] not in ["", "Agree"] else []
        st.session_state.contextual_explanation = r["contextual_explanation"] or ""
    else:
        st.session_state.label_radio = None
        st.session_state.selected_label = None
        st.session_state.contextual_agreement = None
        st.session_state.contextual_factors = []
        st.session_state.contextual_explanation = ""

# Clamp index
st.session_state.current_idx = max(0, min(st.session_state.current_idx, len(df) - 1))
row = df.iloc[st.session_state.current_idx]

if st.session_state.loaded_id != row["id"]:
    load_existing_annotation(row["id"])
    st.session_state.loaded_id = row["id"]

# -----------------------
# 🤖 Task 1: Annotation for Contradiction Detection
# -----------------------
st.subheader("🤖 Task 1: Annotation for Contradiction Detection")

with st.container(border=True):

    # =====================================================
    # 1. Structured Extraction
    # =====================================================
    st.markdown("### Structured Claim Summary")

    col_se_l, col_se_r = st.columns(2)

    with col_se_l:
        st.write(f"**Drug:** {row.get('drug', 'N/A')}")
        st.write(f"**Disease:** {row.get('disease', 'N/A')}")

    with col_se_r:
        st.markdown("**Claim 1 Relation:**")
        st.code(str(row.get("claim_1_dd_relation", "")))
        st.markdown("**Claim 2 Relation:**")
        st.code(str(row.get("claim_2_dd_relation", "")))

    st.markdown("---")

    # =====================================================
    # 2. Claims
    # =====================================================
    st.markdown("### Claims Under Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Claim 1**")
        with st.container(border=True):
            st.markdown(
                re.sub(r"\.(?=[A-Z])", ". ", row["claim_1"])
            )
        with st.expander("Claim 1 – Full Abstract"):
            st.write(f"**PMID:** {row['pmid_1']}")
            st.write(row["claims_abs_1"])

    with col2:
        st.markdown("**Claim 2**")
        with st.container(border=True):
            st.markdown(
                re.sub(r"\.(?=[A-Z])", ". ", row["claim_2"])
            )
        with st.expander("Claim 2 – Full Abstract"):
            st.write(f"**PMID:** {row['pmid_2']}")
            st.write(
                re.sub(r"\.(?=[A-Z])", ". ", row["claims_abs_2"])
            )

    st.markdown("---")

    # =====================================================
    # 3. LLM Explanation
    # =====================================================

    st.markdown("### Model Reasoning")
    
    raw_explanation = str(row.get("reasoning", "")).strip()
    
    cleaned_explanation = (
        raw_explanation
        .replace("Task(1):", "")
        .replace("Task(2):", "")
        .strip()
    )
    
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="
                background-color: #f9f9f9;
                padding: 14px;
                border-radius: 6px;
                line-height: 1.6;
                white-space: pre-wrap;
                max-height: 150px;
                overflow-y: auto;
            ">
            {cleaned_explanation}
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown("---")


    # =====================================================
    # 4. LLM Decision
    # =====================================================
    st.markdown("### LLM Decision")
    st.write(f"**{row.get('prediction', 'N/A')}**")

# -----------------------
# Task 1: Contradiction Detection
# -----------------------
st.markdown("<p style='color:red; font-size:22px; font-weight:600;'>Is the LLM correct?</p>", unsafe_allow_html=True)
st.radio("", options=list(LABELS.keys()), key="label_radio")
st.session_state.selected_label = LABELS.get(st.session_state.label_radio)



if st.session_state.selected_label == "correct":
    st.markdown("---")
    st.subheader("🧩 Task 2: Contextual Resolution")
    st.markdown("### 🤖 LLM Contextual Judgment")
    st.write(f"**{row.get('contextual_factor', 'N/A')}**")
    if row.get("contextual_factor_explanation"):
        st.markdown(
            f"""
            <div style="
                max-height: 180px;
                overflow-y: auto;
                padding: 10px;
                border-radius: 6px;
                border: 1px solid #ddd;
                background-color: transparent;
                white-space: pre-wrap;
            ">
                {row["contextual_factor_explanation"]}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -----------------------
    # Task 2: Contextual Resolution
    # -----------------------
    
    # ======================
    # Internal-to-the-patient
    # ======================
    with st.expander("🧬 Species", expanded=False):
        st.markdown("""
    Contradictions in drug–effect associations may result from cross-species differences  
    (Ioannidis et al., 2005; van der Worp et al., 2010; Rosemblat et al., 2019).
    
    > *PMID 1595111:*  
    > **Wistar rats** (experiment 1)…  
    > **Claim 1:** Tirilazad reduces cortical infarction in transient but not permanent ischemia, an effect not related to improvement in regional cerebral blood flow. Tirilazad might prove to be useful as an adjuvant therapy after successful thrombolysis in acute stroke patients.
    >
    > *PMID 11687138:*  
    > **Claim 2:** Tirilazad mesylate increased the combined end-point of “death or disability” by about one-fifth when given to **patients** with acute ischaemic stroke.
    
    These claims appear contradictory at first glance. However, Claim 1 is based on preclinical experiments in rats, whereas Claim 2 reports results from human clinical trials. Differences in disease manifestation and pharmacokinetics across species limit direct comparability. Therefore, the claims reflect **species-specific effects rather than a true contradiction**.
    """)
    
    with st.expander("👥 Population", expanded=False):
        st.markdown("""
    Claims may target different demographic or genetic subpopulations (e.g., age, sex, or location).
    
    > *PMID 1595111:*  
    > **Claim 1:** A full course of 8-aminoquinolines should be added to mass drug administration to eliminate malaria in **four villages of the Lao PDR**.
    >
    > **Claim 2:** G6PD deficiency is common in **African patients**, making 8-aminoquinoline use problematic.
    
    The apparent contradiction arises from population differences. The prevalence of G6PD deficiency differs across regions, allowing these claims to coexist when population context is considered.
    """)
    
    with st.expander("⚡ Transient Physiological Context", expanded=False):
        st.markdown("""
    Different results may arise when the same intervention is evaluated under different transient physiological conditions.
    
    > *PMID 3942723:*  
    > **Claim 1:** Caffeine reduced reaction time and delayed fatigue during **successive taekwondo combats**.
    >
    > *PMID 5306327:*  
    > **Claim 2:** Caffeine improved endurance during **high-intensity cycling under hypoxia** without reducing fatigue.
    
    Differences in exercise modality and physiological environment explain these findings. We therefore extend prior taxonomies to explicitly include **transient physiological context**.
    """)
    
    
    
    with st.expander("💊 Dosage and Exposure Duration", expanded=False):
        st.markdown("""
    Different doses or exposure durations may produce different biological effects.
    
    > *PMID 27795670:*  
    > **Claim 1:** 10 mg intravenous dexamethasone showed no impact on postoperative pain.
    >
    > *PMID 34749994:*  
    > **Claim 2:** Dexamethasone 1 mg/kg reduced pain and improved recovery.
    
    Differences in dosage and administration timing explain the divergent outcomes.
    """)
    
    with st.expander("💉 Route of Administration", expanded=False):
        st.markdown("""
    Different delivery routes may change tissue targeting or absorption.
    
    > **Intravaginal misoprostol** was reported as safe and effective.  
    > **Sublingual misoprostol** showed higher rates of tachysystole.
    
    Route of administration explains the differing safety profiles.
    """)
    
    with st.expander("📈 Evolving Scientific Evidence", expanded=False):
        st.markdown("""
    Early hypotheses may be revised by later trials.
    
    > **Claim 1:** Adjunctive rifampicin was hypothesized to improve outcomes.  
    > **Claim 2:** Later trials showed no overall benefit.
    
    These findings represent different stages of scientific understanding.
    """)
    
    with st.expander("⚠️ Known Controversy", expanded=False):
        st.markdown("""
    Some claims explicitly acknowledge uncertainty.
    
    > **Claim 1:** Fluoroquinolone treatment failure is associated with *S. Typhi*-H58.  
    > **Claim 2:** Fluoroquinolones are still recommended, but policies should change.
    
    The claims reflect an acknowledged controversy rather than a contradiction.
    """)
    
    with st.expander("🧪 Combined Drug Effects", expanded=False):
        st.markdown("""
    Drug–drug interactions may yield different outcomes.
    
    > **Claim 1:** Gemcitabine combined with HF10 and erlotinib was safe.  
    > **Claim 2:** Gemcitabine combined with dual EGFR therapy increased toxicity.
    
    Different combination regimens explain the apparent contradiction.
    """)

    with st.expander("❓Other", expanded=False):
        st.markdown("""None of the listed factors explain the contradiction. If choosing 'Other', explain the other potiential contextual factors that may apply to the scenario
    """)

    st.markdown("<p style='color:red; font-size:22px; font-weight:600;'>Do you agree with the LLM’s contextual judgment?</p>", unsafe_allow_html=True)
    st.radio("", options=["Agree", "Disagree"], key="contextual_agreement", horizontal=True)

    if st.session_state.contextual_agreement == "Disagree":
        st.multiselect("Which contextual factors explain the contradiction?", options=CONTEXTUAL_FACTORS, key="contextual_factors")
        st.text_area("If choosing 'Other', explain:", key="contextual_explanation", height=120)
    elif st.session_state.contextual_agreement == "Agree":
        st.session_state.contextual_factors = []
        st.session_state.contextual_explanation = ""


    st.markdown("<p style='color:red; font-size:22px; font-weight:600;'>Do you agree with the LLM’s contextual judgment?</p>", unsafe_allow_html=True)
    st.radio("", options=["Agree", "Disagree"], key="contextual_agreement", horizontal=True)

    if st.session_state.contextual_agreement == "Disagree":
        st.multiselect("Which contextual factors explain the contradiction?", options=CONTEXTUAL_FACTORS, key="contextual_factors")
        st.text_area("If choosing 'Other', explain:", key="contextual_explanation", height=120)
    elif st.session_state.contextual_agreement == "Agree":
        st.session_state.contextual_factors = []
        st.session_state.contextual_explanation = ""
        
# -----------------------
# Save annotation
# -----------------------
# def save_annotation():
#     global annotations
#     new_row = {
#         "id": row["id"],
#         "label": st.session_state.selected_label,
#         "contextual_agreement": st.session_state.contextual_agreement or "",
#         "contextual_factors": "Agree" if st.session_state.contextual_agreement == "Agree" else "; ".join(st.session_state.contextual_factors),
#         "contextual_explanation": "" if st.session_state.contextual_agreement == "Agree" else st.session_state.contextual_explanation.strip(),
#         "annotator": st.session_state.username,
#     }
#
#     # Remove old annotation for this example
#     annotations = annotations[~((annotations["id"] == row["id"]) & (annotations["annotator"] == st.session_state.username))]
#     annotations = pd.concat([annotations, pd.DataFrame([new_row])], ignore_index=True)
#     annotations.to_csv(USER_CSV, index=False)

def save_annotation():
    global annotations
    new_row = {
        "id": row["id"],
        "label": st.session_state.selected_label,
        "contextual_agreement": st.session_state.contextual_agreement or "",
        "contextual_factors": "Agree" if st.session_state.contextual_agreement == "Agree" else "; ".join(st.session_state.contextual_factors),
        "contextual_explanation": "" if st.session_state.contextual_agreement == "Agree" else st.session_state.contextual_explanation.strip(),
        "annotator": st.session_state.username,
    }

    # Remove old annotation for this example
    annotations = annotations[~((annotations["id"] == row["id"]) & (annotations["annotator"] == st.session_state.username))]
    annotations = pd.concat([annotations, pd.DataFrame([new_row])], ignore_index=True)

    # Save locally
    USER_CSV.parent.mkdir(exist_ok=True)
    annotations.to_csv(USER_CSV, index=False)

    # Push to GitHub
    push_annotations_to_github(USER_CSV)


# -----------------------
# Navigation + Save buttons
# -----------------------
st.markdown("---")
col_prev, col_save, col_next = st.columns([1, 2, 1])

# -----------------------
# Helper: Validate before navigating
# -----------------------
def validate_and_save():
    """
    Validate required fields before moving to another example.
    Automatically saves annotation if validation passes.
    Returns True if navigation can proceed.
    """
    # Task 1 validation
    if st.session_state.selected_label is None:
        st.warning("Please select whether the LLM is correct.")
        return False

    # Task 2 validation
    if st.session_state.selected_label == "correct":
        if st.session_state.contextual_agreement is None:
            st.warning("Please indicate agreement with the LLM’s contextual judgment.")
            return False
        if st.session_state.contextual_agreement == "Disagree" and not st.session_state.contextual_factors:
            st.warning("Please select at least one contextual factor.")
            return False

    # If validation passes, save
    save_annotation()
    return True

# -----------------------
# Navigation + Save buttons
# -----------------------
st.markdown("---")
col_prev, col_save, col_next = st.columns([1, 2, 1])

with col_prev:
    if st.button("⬅ Previous", disabled=st.session_state.current_idx == 0):
        if validate_and_save():
            st.session_state.current_idx -= 1
            st.rerun()

with col_save:
    if st.button("💾 Save annotation"):
        if validate_and_save():
            st.success("Annotation saved.")

with col_next:
    if st.button("Next ➡", disabled=st.session_state.current_idx == len(df) - 1):
        if validate_and_save():
            st.session_state.current_idx += 1
            st.rerun()














