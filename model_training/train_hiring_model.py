"""
train_hiring_model.py — Prompt 10

Generates a bias-injected synthetic hiring dataset of 50,000 applicants,
trains LogReg + XGBoost, evaluates both with Fairlearn to prove they
reproduce the bias, then uploads XGBoost to Vertex AI Model Registry.

Ground truth: should_hire is determined ONLY by skills + years_experience.
Historical bias: female-coded names and minority-coded ethnicity have a
20% lower historical hire rate even when qualified — simulating real biased data.
"""

from __future__ import annotations

import os
import json
import random
import string
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import xgboost as xgb
from fairlearn.metrics import (
    MetricFrame,
    demographic_parity_difference,
    equalized_odds_difference,
    demographic_parity_ratio,
)
import joblib

# ──────────────────────────────────────────────
# 1. DATASET GENERATION
# ──────────────────────────────────────────────

N = 50_000
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

GENDERS = ["male", "female"]
ETHNICITIES = ["white", "black", "asian", "hispanic"]
EDUCATIONS = ["high_school", "bachelor", "master", "phd"]
SKILL_POOL = [
    "python", "java", "sql", "machine_learning", "project_management",
    "data_analysis", "communication", "leadership", "cloud", "javascript",
    "devops", "statistics", "excel", "tableau", "agile",
]

MINORITY_GROUPS = {
    "gender": ["female"],
    "ethnicity": ["black", "hispanic"],
}

BIAS_PENALTY = 0.20  # 20% lower hire rate for minority-coded applicants


def _generate_name(gender: str, ethnicity: str) -> str:
    first_names = {
        ("male", "white"): ["James", "John", "Robert", "William", "David"],
        ("female", "white"): ["Mary", "Patricia", "Jennifer", "Linda", "Susan"],
        ("male", "black"): ["Jamal", "DeShawn", "Malik", "Darius", "Marcus"],
        ("female", "black"): ["Lakisha", "Tanisha", "Aaliyah", "Keisha", "Imani"],
        ("male", "asian"): ["Wei", "Min-jun", "Hiroshi", "Raj", "Arjun"],
        ("female", "asian"): ["Priya", "Yuki", "Mei", "Ananya", "Soo-jin"],
        ("male", "hispanic"): ["Carlos", "Luis", "Miguel", "Jose", "Ricardo"],
        ("female", "hispanic"): ["Maria", "Carmen", "Isabel", "Valentina", "Sofia"],
    }
    last_names = {
        "white": ["Smith", "Johnson", "Williams", "Brown", "Jones"],
        "black": ["Williams", "Brown", "Jones", "Davis", "Wilson"],
        "asian": ["Zhang", "Patel", "Kim", "Lee", "Singh"],
        "hispanic": ["Garcia", "Rodriguez", "Martinez", "Lopez", "Hernandez"],
    }
    first = random.choice(first_names.get((gender, ethnicity), ["Alex"]))
    last = random.choice(last_names.get(ethnicity, ["Taylor"]))
    return f"{first} {last}"


def generate_dataset(n: int = N) -> pd.DataFrame:
    genders = rng.choice(GENDERS, size=n)
    ethnicities = rng.choice(ETHNICITIES, size=n)
    ages = rng.integers(22, 65, size=n)
    educations = rng.choice(EDUCATIONS, size=n, p=[0.15, 0.45, 0.30, 0.10])
    years_exp = rng.integers(0, 30, size=n)
    skills_count = rng.integers(1, 10, size=n)

    edu_score = {"high_school": 0.0, "bachelor": 0.3, "master": 0.5, "phd": 0.7}
    edu_arr = np.array([edu_score[e] for e in educations])
    skills_norm = skills_count / 10.0
    exp_norm = np.clip(years_exp / 15.0, 0, 1)

    # Ground truth — purely merit-based
    merit_score = 0.4 * skills_norm + 0.4 * exp_norm + 0.2 * edu_arr
    should_hire_true = (merit_score + rng.normal(0, 0.05, size=n) >= 0.5).astype(int)

    # Biased historical label
    is_minority_gender = np.array([g in MINORITY_GROUPS["gender"] for g in genders])
    is_minority_eth = np.array([e in MINORITY_GROUPS["ethnicity"] for e in ethnicities])
    is_minority = is_minority_gender | is_minority_eth

    # Apply 20% suppression for minority applicants who are qualified
    hired_biased = should_hire_true.copy()
    minority_qualified = is_minority & (should_hire_true == 1)
    suppress_mask = minority_qualified & (rng.random(size=n) < BIAS_PENALTY)
    hired_biased[suppress_mask] = 0

    names = [_generate_name(g, e) for g, e in zip(genders, ethnicities)]
    skills_list = [
        ",".join(random.sample(SKILL_POOL, int(k))) for k in skills_count
    ]

    df = pd.DataFrame({
        "name": names,
        "gender": genders,
        "ethnicity": ethnicities,
        "age": ages,
        "education": educations,
        "years_experience": years_exp,
        "skills_count": skills_count,
        "skills": skills_list,
        "merit_score": merit_score.round(4),
        "should_hire_true": should_hire_true,   # ground truth (unbiased)
        "hired": hired_biased,                  # biased historical label
    })
    return df


# ──────────────────────────────────────────────
# 2. PREPROCESSING
# ──────────────────────────────────────────────

def preprocess(df: pd.DataFrame):
    le_gender = LabelEncoder()
    le_eth = LabelEncoder()
    le_edu = LabelEncoder()

    X = pd.DataFrame({
        "gender_enc": le_gender.fit_transform(df["gender"]),
        "ethnicity_enc": le_eth.fit_transform(df["ethnicity"]),
        "age": df["age"],
        "education_enc": le_edu.fit_transform(df["education"]),
        "years_experience": df["years_experience"],
        "skills_count": df["skills_count"],
    })
    y = df["hired"]
    sensitive = pd.DataFrame({
        "gender": df["gender"],
        "ethnicity": df["ethnicity"],
    })
    return X, y, sensitive


# ──────────────────────────────────────────────
# 3. FAIRNESS EVALUATION
# ──────────────────────────────────────────────

def evaluate_fairness(y_true, y_pred, sensitive_features, model_name: str):
    print(f"\n{'='*60}")
    print(f"Fairness Report: {model_name}")
    print("="*60)
    print(classification_report(y_true, y_pred))

    for attr in ["gender", "ethnicity"]:
        sf = sensitive_features[attr]
        dp_diff = demographic_parity_difference(y_true, y_pred, sensitive_features=sf)
        eo_diff = equalized_odds_difference(y_true, y_pred, sensitive_features=sf)
        di = demographic_parity_ratio(y_true, y_pred, sensitive_features=sf)
        print(f"\n[{attr}]")
        print(f"  Demographic Parity Difference : {dp_diff:.4f}  (|val|>{0.1} = biased)")
        print(f"  Equalized Odds Difference     : {eo_diff:.4f}")
        print(f"  Disparate Impact Ratio        : {di:.4f}  (outside 0.8–1.25 = biased)")

        frame = MetricFrame(
            metrics={"selection_rate": lambda yt, yp: yp.mean()},
            y_true=y_true,
            y_pred=y_pred,
            sensitive_features=sf,
        )
        print(f"  Selection rate by {attr}:")
        print(frame.by_group.to_string(index=True))


def plot_bias(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Gender hire rate: truth vs biased
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, label, col in zip(axes, ["Ground Truth", "Biased Historical"], ["should_hire_true", "hired"]):
        rates = df.groupby("gender")[col].mean()
        rates.plot(kind="bar", ax=ax, color=["#1f77b4", "#ff7f0e"])
        ax.set_title(f"Hire Rate by Gender ({label})")
        ax.set_ylabel("Hire Rate")
        ax.set_ylim(0, 1)
        ax.axhline(0.5, ls="--", color="red", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_dir / "gender_hire_rate.png", dpi=120)
    plt.close()

    # Ethnicity hire rate
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, label, col in zip(axes, ["Ground Truth", "Biased Historical"], ["should_hire_true", "hired"]):
        rates = df.groupby("ethnicity")[col].mean()
        rates.plot(kind="bar", ax=ax)
        ax.set_title(f"Hire Rate by Ethnicity ({label})")
        ax.set_ylabel("Hire Rate")
        ax.set_ylim(0, 1)
        ax.axhline(0.5, ls="--", color="red", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_dir / "ethnicity_hire_rate.png", dpi=120)
    plt.close()

    print(f"Plots saved to {out_dir}")


# ──────────────────────────────────────────────
# 4. TRAINING
# ──────────────────────────────────────────────

def train_models(X_train, X_test, y_train, y_test, sensitive_test):
    print("\n[Training Logistic Regression]")
    logreg = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
    logreg.fit(X_train, y_train)
    y_pred_lr = logreg.predict(X_test)
    evaluate_fairness(y_test, y_pred_lr, sensitive_test, "Logistic Regression")

    print("\n[Training XGBoost]")
    xgb_model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=RANDOM_SEED,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    y_pred_xgb = xgb_model.predict(X_test)
    evaluate_fairness(y_test, y_pred_xgb, sensitive_test, "XGBoost")

    return logreg, xgb_model


# ──────────────────────────────────────────────
# 5. VERTEX AI UPLOAD (optional)
# ──────────────────────────────────────────────

def upload_to_vertex(model_path: Path):
    try:
        from google.cloud import aiplatform
        project = os.environ.get("GCP_PROJECT_ID")
        region = os.environ.get("GCP_REGION", "us-central1")
        if not project:
            print("GCP_PROJECT_ID not set — skipping Vertex AI upload.")
            return

        aiplatform.init(project=project, location=region)
        model = aiplatform.Model.upload(
            display_name="pof-ai-hiring-xgboost-biased",
            artifact_uri=str(model_path.parent),
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-3:latest",
        )
        print(f"Model uploaded: {model.resource_name}")

        endpoint = aiplatform.Endpoint.create(display_name="pof-ai-hiring-endpoint")
        endpoint.deploy(
            model=model,
            machine_type="n1-standard-2",
            min_replica_count=1,
            max_replica_count=3,
        )
        print(f"Endpoint: {endpoint.resource_name}")
        print(f"\nSet VERTEX_ENDPOINT_ID={endpoint.name} in your .env")
    except Exception as exc:
        print(f"Vertex AI upload skipped: {exc}")


# ──────────────────────────────────────────────
# 6. MAIN
# ──────────────────────────────────────────────

def main():
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)

    print("Generating synthetic hiring dataset…")
    df = generate_dataset()
    df.to_csv(out_dir / "hiring_dataset.csv", index=False)
    print(f"Dataset saved: {len(df):,} rows → {out_dir / 'hiring_dataset.csv'}")

    plot_bias(df, out_dir / "plots")

    X, y, sensitive = preprocess(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED)
    sensitive_test = sensitive.iloc[X_test.index]

    logreg, xgb_model = train_models(X_train, X_test, y_train, y_test, sensitive_test)

    logreg_path = out_dir / "logreg_model.joblib"
    xgb_path = out_dir / "xgb_model.joblib"
    joblib.dump(logreg, logreg_path)
    joblib.dump(xgb_model, xgb_path)
    print(f"\nModels saved:\n  {logreg_path}\n  {xgb_path}")

    upload_to_vertex(xgb_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
