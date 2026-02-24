# Downstream Integration Guide

This document explains how developers and operators of **Synthetic Data Generators** can programmatically parse and enforce the standard constraints defined in the schema.

Because the schema acts as a "metadata contract," the `schema-generator` does not enforce these laws itself. It simply validates and passes the properties downstream via `schema.json`. It is the responsibility of the synthetic data generator to implement enforcement strategies to ensure the neural networks do not "hallucinate" physically impossible patients.

---

## 1. Enforcement Strategies

Modern synthetic data simulators typically enforce structured logic using three primary methodologies. You should map the schema constraints to whichever strategy your framework supports.

### A. Rejection Sampling (Post-Generation Filter)
**How it works:** The neural network generates a batch of synthetic patients. A deterministic Python validation layer (like `pandas` or `Great Expectations`) iterates across the rows and immediately destroys any patient who violates the constraints. The model then resamples the missing rows until the quota is filled.
**Best for:** `Inequality`, `FixedCombinations`, `PiecewiseBounds`
**Pros:** Guarantees 100% mathematical fidelity.
**Cons:** If the model hasn't "learned" the rule well, rejection rates can spike, drastically slowing down generation.

### B. Loss Function Penalties (During Training)
**How it works:** The constraint is translated into a differentiable equation and added to the Generator's loss function during the training phase. If the model hallucinates a pregnant male, the loss spikes, heavily penalizing the network's weights.
**Best for:** `CompositionalSum`, `MonotonicOrdering`
**Pros:** Teaches the actual neural network the laws of physics.
**Cons:** Cannot easily guarantee absolute rigidity (might occasionally generate a patient where A is greater than B by 0.001%).

### C. Deterministic Overwrites (Post-Processing Projection)
**How it works:** The model is not allowed to generate the dependent variable at all. Instead, the model generates the core components natively, and a script mathematically computes the remaining column perfectly.
**Best for:** `CompositionalSum` (e.g., model generates `medication_cost` and `procedure_cost`, script creates `total_cost` via addition).
**Pros:** 100% accurate, reduces the complexity burden on the neural network.

---

## 2. Core Tabular Vocabularies

Before running constraint validations, downstream engines must instantiate their core data architectures using the root-level schema vocabularies. Proper interpretation of these keys defines how well your model learns the true distributions without leaking privacy computationally.

### `column_types`
The generator provides strict foundational types mapping the dimensionality logic the target neural application must natively reconstruct:
*   `continuous`: Map this directly to a continuous floating-point evaluation scalar (e.g., Gaussian diffusion heads). 
*   `integer`: Mathematically similar to continuous, but with a critical structural difference: **downstream generators *must* snap or round any generated fuzzy probabilities definitively and exclusively back to whole natural numbers** before validation testing. If a synthetic generator returns an `age` of `45.8`, you must truncate it rigidly to `46` to prevent clinical errors.
*   `categorical`: Route this data strictly into discrete sampling matrices (e.g., Categorical Gumbel-Softmax) or dense one-hot embedding layers.
*   `ordinal`: Technically discrete strings like categoricals, but structurally mapping sequential hierarchies. **Crucially: All simple booleans (e.g., `True/False` or `[0, 1]`) are typed structurally as `ordinal`.** The downstream classifier architecture natively identifying a 2-class `ordinal` should probabilistically push the output across a standard Binomial/Sigmoid activation function.

### `public_bounds` & `public_categories` (The Clipping Limits)
For Differential Privacy (DP) guarantees or simple hallucination prevention, models must *never* dynamically calculate boundaries by scanning the raw dataset. They must use the schema perfectly natively:
*   **Numerical Generators:** Scale numerical data from $0$ to $1$ exclusively using the limits found in `public_bounds`. Any source CSV data exceeding these boundaries must be clipped before training begins.
*   **Categorical Encoders:** Initialize one-hot vector spaces using exactly the arrays defined in `public_categories`. If a source CSV row contains a unique string not found in this array (e.g., due to `--max-categories` truncation), the model must cast it to an `<UNKNOWN>` token. 

### `missing_value_rates` (The Sparsity Injector)
Generative AI models often waste tremendous computational power and privacy budget attempting to natively learn *why* data is completely missing jointly with variable correlation.
*   **Best Practice:** Drop all `NaN`/nulls internally, and train the AI network solely on complete relationships algebraically. After generation, write a deterministic script that deletes synthetic cells probabilistically to match the exact percentages defined comprehensively in `missing_value_rates`. This creates perfect sparsity matrix replication without stressing the AI!

### `datetime_spec` 
The generic tools strictly map time mathematically via large integer values spanning `epoch_ns`.
*   **Usage:** You must train your downstream generative AI strictly against the epoch nanosecond integers (passing them identically as `continuous` scales alongside heart rate or body mass). Do not feed raw strings directly to the neural layers. 

### `target_spec`
Often used for supervised machine learning tasks where researchers are creating synthetic data to train predictive classification algorithms, and for evaluators like SDMetrics or SynthCity to calculate Machine Learning Efficacy (predictive utility).
*   **Usage (`single` / Default):** A downstream tool maps conditional data splitting logic strictly toward `primary_target`, and utility metrics (like F1-score, ROC-AUC, or RMSE) evaluate predictive fidelity of a model trained on synthetic data against real holdout data exclusively for this feature.
*   **Usage (`survival_pair`):** Structurally forces the downstream networks to identify a time-to-event architecture, ensuring utility metrics calculate Concordance Index (C-Index) or Brier Score jointly modeling `event` probability across `time`.
*   **Usage (`multi_target`):** When generating a dataset with multiple clinical outcomes (e.g., predicting `ICU_Admission` and `Mortality` simultaneously), downstream evaluators must compute Machine Learning Efficacy metrics for *every* target listed explicitly in `target_spec["targets"]` independently. The holistic dataset utility score should be reported as the average (or worst-case) aggregate across all targeted predictions to ensure the AI hasn't sacrificed the statistical fidelity of one label to overfit the other.

---

## 3. Implementing Constraint Vocabularies

Here is how to map the `schema.json` constraint vocabularies directly into generator logic:

### `Inequality`
*(e.g., Admission Date $\le$ Discharge Date)*
- **SDV mapping:** Map natively to `<class 'sdv.constraints.Inequality'>`.
- **Rejection Sampler:** `df.drop(df[df[low_col] > df[high_col]].index)`

### `FixedCombinations`
*(e.g., Pregnancy Status vs Biological Sex)*
- **SDV mapping:** Map natively to `<class 'sdv.constraints.FixedCombinations'>`.
- **Rejection Sampler:** Convert the `valid_combinations` array into a Pandas multi-index or hash table. Any generated row whose combined tuple is missing from the table is rejected.

### `CompositionalSum`
*(e.g., Total Cost = A + B + C)*
- **Generator Masking:** Remove `total_column` from the training payload entirely. Train the generative model only on `component_columns`. 
- **Post-Processing Pipeline:** During output synthesis, execute `df[total_column] = df[component_columns].sum(axis=1)`.

### `PiecewiseBounds`
*(e.g., Age-adjusted Heart Rate limits)*
- **Rejection Sampler:** Write a Python evaluation loop parsing the `criteria` strings via `pd.eval()`. 
  ```python
  for condition in constraint["conditions"]:
      mask = pd.eval(f"df.{condition['criteria']}")
      invalid = (df[target] < condition['bounds']['min']) | (df[target] > condition['bounds']['max'])
      df.loc[mask & invalid, 'REJECT'] = True
  ```

### `MonotonicOrdering`
*(e.g., Chronological patient visits)*
- **TimeGAN / DoppelGANger:** Enforce via the recursive temporal node mapping dynamically natively during recurrent generation.
- **Rejection Sampler:** Group by `entity_column`, invoke `.is_monotonic_increasing` on the `sort_column`. Drop the entire journey entity if False.

### `RegexMatch`
*(e.g., ICD-10 Code Syntax)*
- **SDV mapping:** Apply the `RegexGenerator` native column type, which utilizes the `rstr` evaluation library to probabilistically sample valid regex strings.
- **Warning:** Do not place this variable into a continuous diffusion network; standard text vectors must model this parametrically via deterministic string-builder agents.

---

## 4. Parsing the JSON Payload

When loading the `schema.json`, downstream systems should scan the `constraints` object:

```python
import json

with open("schema.json") as f:
    schema = json.load(f)

# 1. Build dictionary rules for regex column formats
for col, rules in schema["constraints"].get("column_constraints", {}).items():
    if rules.get("constraint_class") == "RegexMatch":
        apply_regex_generator(col, rules["pattern"])

# 2. Build multi-variable clinical laws
for cross_rule in schema["constraints"].get("cross_column_constraints", []):
    cls = cross_rule.get("constraint_class")
    if cls == "Inequality":
        apply_inequality(cross_rule["low_column"], cross_rule["high_column"])
    elif cls == "FixedCombinations":
        apply_whitelist_filter(cross_rule["columns"], cross_rule["valid_combinations"])
    # ... etc
```

By standardizing generator architectures around this payload, you abstract clinical expertise cleanly away from the data engineering pipelines. Clinicians define the JSON rules, and the generator perfectly enforces them.
