# Model Card: PoF-AI Hiring XGBoost (Bias-Injected Demo)

> Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I.D., & Gebru, T. (2019). Model cards for model reporting. *Proceedings of FAT\* 2019*. https://doi.org/10.1145/3287560.3287596

---

## Model Details

| Field | Value |
|-------|-------|
| **Model name** | pof-ai-hiring-xgboost-biased |
| **Version** | 1.0 |
| **Type** | Binary classifier (hire / reject) |
| **Algorithm** | XGBoost (gradient-boosted trees) |
| **Framework** | XGBoost 2.0.3, scikit-learn 1.4.2 |
| **Developed by** | PoF-AI Team — Google Solution Challenge 2026 |
| **Date** | April 2026 |
| **Contact** | sukhmanpreetkaur3108@gmail.com |
| **License** | MIT |

### Architecture
- 200 estimators, max depth 6, learning rate 0.1
- Input: 6 features (gender_enc, ethnicity_enc, age, education_enc, years_experience, skills_count)
- Output: binary probability score ∈ [0, 1]; threshold 0.5 → hire/reject decision

---

## Intended Use

### Primary Use
This model is a **deliberate demonstration artifact** created to prove that PoF-AI catches bias in real AI pipelines. It is intentionally trained on biased historical labels and is deployed **only** so the five PoF-AI fairness engines can audit it and generate Fairness Certificates that flag its discrimination.

**This model should NOT be used to make real hiring decisions.**

### Out-of-Scope Uses
- Any production hiring, HR, or employment screening system
- Any legal, financial, or medical decision-making
- Any system where fairness, equal opportunity, or human rights apply

---

## Training Data

### Dataset
- **Size:** 50,000 synthetic applicants
- **Generation:** Procedurally generated with controlled ground truth and injected bias
- **Source:** Synthetic — no real personal data used

### Features

| Feature | Type | Description |
|---------|------|-------------|
| `gender` | Categorical | Applicant gender (male / female) |
| `ethnicity` | Categorical | Applicant ethnicity (white / black / asian / hispanic) |
| `age` | Integer | Applicant age (22–64) |
| `education` | Categorical | Highest degree (high_school / bachelor / master / phd) |
| `years_experience` | Integer | Years of relevant work experience (0–29) |
| `skills_count` | Integer | Number of listed skills (1–9) |

### Ground Truth vs. Biased Labels

| Label | Description |
|-------|-------------|
| `should_hire_true` | **Fair** — determined only by skills_count + years_experience + education |
| `hired` | **Biased** — female-coded names and minority-coded ethnicities have a 20% lower hire rate even when fully qualified |

The model is trained on `hired` (biased), **not** `should_hire_true` (fair), to simulate a real-world pipeline that learned from discriminatory historical data.

---

## Evaluation

### Overall Performance (test set, 20% hold-out)

| Metric | Logistic Regression | XGBoost |
|--------|--------------------|----|
| Accuracy | ~0.78 | ~0.81 |
| F1 (hire) | ~0.74 | ~0.77 |

### Fairness Metrics (XGBoost, test set)

| Attribute | Demographic Parity Diff | Equalized Odds Diff | Disparate Impact Ratio |
|-----------|------------------------|---------------------|----------------------|
| Gender | ~0.14 ⚠️ | ~0.12 ⚠️ | ~0.78 ⚠️ |
| Ethnicity | ~0.17 ⚠️ | ~0.15 ⚠️ | ~0.74 ⚠️ |

> ⚠️ Values exceeding thresholds (|diff| > 0.1, ratio outside 0.8–1.25) are flagged by the PoF-AI Statistical Engine.

---

## Bias, Risks, and Limitations

### Known Biases (by design)
1. **Gender bias:** Female applicants have a ~20% lower hire rate relative to equally qualified male applicants
2. **Ethnicity bias:** Black and Hispanic applicants have a ~20% lower hire rate relative to equally qualified white applicants
3. **Intersectional bias:** The intersection of female + Black/Hispanic shows compounded discrimination (~36% lower rate), captured by the Intersectional Surface Engine

### Risks
- If deployed in a real system, this model would cause significant harm to underrepresented groups
- The model reproduces and amplifies historical discrimination present in training data
- Confidence calibration is poor for minority subgroups with smaller sample sizes

### Limitations
- Synthetic data — real-world bias patterns are more complex and intersectional
- Only 4 ethnicity categories and 2 gender categories — inadequate for real diversity
- No geographic, disability, or socioeconomic features modelled

---

## PoF-AI Audit Results

When audited by PoF-AI's five engines:

| Engine | Finding |
|--------|---------|
| Statistical | Flags gender.demographic_parity_difference ≈ 0.14 and ethnicity.disparate_impact_ratio ≈ 0.74 |
| Intersectional | Worst subgroup: "Black woman" — 36% lower selection rate than global average |
| Causal | Counterfactual fairness score ≈ 0.65 (35% of gender/ethnicity interventions flip the decision) |
| Adversarial | Flip rate ≈ 28% — Gemini-generated near-twins with same qualifications but minority names are rejected more often |
| Regulatory | Fails EU AI Act Art.10, GDPR Art.22, India DPDP Sec.4 |

---

## Ethical Considerations

This model exists **solely** to demonstrate that PoF-AI can detect, measure, and certify discrimination. By making the bias explicit and measurable, PoF-AI creates accountability that is currently absent in real AI hiring tools deployed globally.

> "The first step to fixing bias is being able to prove it exists — mathematically, ethically, and legally."

---

## References

- Mitchell et al. (2019) — Model Cards for Model Reporting
- Barocas, S., Hardt, M., & Narayanan, A. (2023) — Fairness and Machine Learning
- EU AI Act (2024), GDPR Art. 22, NIST AI RMF 1.0, India DPDP Act 2023
