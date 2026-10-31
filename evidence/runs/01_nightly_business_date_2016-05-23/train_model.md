# Task `train_model` — SUCCESS

*Run 1120998187240366 · started 2026-10-30 23:57:40 UTC · 43s*

# ML 1/2 · Train the 3-day stockout-risk model

**Question the model answers:** *for a store-item that is on the shelf tonight, what is the probability it will
be out of stock on at least one of the next 3 days?* (label `label_oos_next3`; stockouts inferred from real
M5 sales).

* Data: `gold_stockout_features` (Lakeflow pipeline output), active store-items in stock at end of day.
* Time-based split (no leakage across time): train → validation → **test = 2016-05-01 … 2016-05-19**.
* Model: LightGBM, wrapped as an MLflow `pyfunc` that returns the probability **and its top-3 drivers**
  (LightGBM native SHAP contributions) so the app and the agents can explain every alert.
* Baseline: the replenishment team's current rule — *alert when days of cover < 3 or a PO is overdue*.
* Business metrics: precision of the daily top-K alert list and share of next-3-day lost revenue it covers.
* Registered in Unity Catalog as `osa_stockout_risk` with alias `@champion`.

```python
%pip install -q lightgbm==4.6.0 "mlflow>=3.1"
%restart_python
```

**Output:**

```text
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("force_retrain", "false")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
S = f"{catalog}.{schema}"
MODEL_NAME = f"{S}.osa_stockout_risk"

import mlflow
from mlflow import MlflowClient
mlflow.set_registry_uri("databricks-uc")
client = MlflowClient()
try:
    champ = client.get_model_version_by_alias(MODEL_NAME, "champion")
except Exception:
    champ = None
if champ is not None and dbutils.widgets.get("force_retrain").lower() != "true":
    print(f"champion already registered: {MODEL_NAME} v{champ.version} (run {champ.run_id}); skipping retrain")
    dbutils.notebook.exit(f"skipped: champion v{champ.version}")
print("training a new model version")
```

**Output:**

```text
skipped: champion v2
```

```python
import numpy as np, pandas as pd
from pyspark.sql import functions as F

FEATURES_NUM = ["lambda_90d", "avg_units_7d", "avg_units_28d", "cv_units_28d", "trend_7_28", "days_since_last_sale",
                "sell_price", "price_change_7d", "on_hand_units", "on_order_units", "days_of_cover",
                "position_cover_days", "open_po_count", "open_po_qty", "overdue_po_count", "max_days_overdue",
                "days_to_next_receipt", "sup_on_time_56d", "contract_lead_time_days", "dow", "event_next3", "snap_next3"]
FEATURES_CAT = ["store_id", "dept_id", "cat_id", "reliability_tier"]
FEATURES = FEATURES_NUM + FEATURES_CAT
TEST_START, VALID_START = "2016-05-01", "2016-04-10"

base = (spark.table(f"{S}.gold_stockout_features")
        .where("label_oos_next3 IS NOT NULL AND NOT is_oos_today AND lambda_90d >= 0.3 AND days_since_last_sale <= 28"))
print("labeled rows by split:")
display(base.withColumn("split", F.when(F.col("date") >= TEST_START, "test")
                        .when(F.col("date") >= VALID_START, "valid").otherwise("train"))
        .groupBy("split").agg(F.count("*").alias("rows"), F.round(100 * F.avg("label_oos_next3"), 3).alias("positive_pct"),
                              F.min("date").alias("from"), F.max("date").alias("to")).orderBy("from"))
```

```python
# Negative down-sampling for the training split only (weights restore the prior); valid/test stay untouched.
NEG_RATE = 0.25
train_sdf = base.where(f"date < '{VALID_START}'").where(f"label_oos_next3 = 1 OR rand(7) < {NEG_RATE}")
cols = ["date", "item_id", "label_oos_next3", "lost_revenue_next3"] + FEATURES
train = train_sdf.select(cols).toPandas()
valid = base.where(f"date >= '{VALID_START}' AND date < '{TEST_START}'").select(cols).toPandas()
test = base.where(f"date >= '{TEST_START}'").select(cols).toPandas()
CATS = {c: sorted(pd.concat([train[c], valid[c], test[c]]).dropna().unique().tolist()) for c in FEATURES_CAT}

def prep(df):
    X = df[FEATURES].copy()
    for c in FEATURES_NUM:
        X[c] = pd.to_numeric(X[c], errors="coerce").astype("float64")
    for c in FEATURES_CAT:
        X[c] = pd.Categorical(X[c], categories=CATS[c])
    return X

w_train = np.where(train.label_oos_next3 == 1, 1.0, 1.0 / NEG_RATE)
print(f"train={len(train):,} (pos {train.label_oos_next3.sum():,})  valid={len(valid):,}  test={len(test):,}")
```

```python
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score

params = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_data_in_leaf=200, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=42)
mlflow.set_experiment(f"/Users/{spark.sql('select current_user()').first()[0]}/osa_stockout_risk")
run = mlflow.start_run(run_name="lgbm_oos_next3")
mlflow.log_params({**params, "neg_sampling_rate": NEG_RATE, "test_start": TEST_START, "valid_start": VALID_START,
                   "n_features": len(FEATURES)})
dtrain = lgb.Dataset(prep(train), train.label_oos_next3, weight=w_train, categorical_feature=FEATURES_CAT)
dvalid = lgb.Dataset(prep(valid), valid.label_oos_next3, categorical_feature=FEATURES_CAT, reference=dtrain)
booster = lgb.train(params, dtrain, num_boost_round=2000, valid_sets=[dvalid], valid_names=["valid"],
                    callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)])
mlflow.log_param("best_iteration", booster.best_iteration)
```

## Test-period evaluation vs. the current business rule

```python
test["score"] = booster.predict(prep(test), num_iteration=booster.best_iteration)
test["rule"] = ((test.days_of_cover < 3) | (test.overdue_po_count > 0)).astype(int)
# tie-break the rule's binary flag by cover so it can also produce a ranked top-K list
test["rule_rank_score"] = test.rule + 1.0 / (1.0 + test.days_of_cover.clip(lower=0))

def topk(df, col, k):
    g = df.sort_values(col, ascending=False).groupby("date").head(k)
    lost_total = df.groupby("date").lost_revenue_next3.sum().sum()
    return dict(precision=g.label_oos_next3.mean(), recall=g.label_oos_next3.sum() / df.label_oos_next3.sum(),
                lost_rev_captured=g.lost_revenue_next3.sum() / lost_total)

auc = roc_auc_score(test.label_oos_next3, test.score)
ap = average_precision_score(test.label_oos_next3, test.score)
rule_auc = roc_auc_score(test.label_oos_next3, test.rule_rank_score)
rule_ap = average_precision_score(test.label_oos_next3, test.rule_rank_score)
rows = [("ROC AUC", auc, rule_auc), ("PR AUC (avg precision)", ap, rule_ap),
        ("base rate (random alerts)", test.label_oos_next3.mean(), test.label_oos_next3.mean())]
for k in [100, 250, 500]:
    m, r = topk(test, "score", k), topk(test, "rule_rank_score", k)
    rows += [(f"precision@{k}/day", m["precision"], r["precision"]),
             (f"recall@{k}/day", m["recall"], r["recall"]),
             (f"lost revenue captured@{k}/day", m["lost_rev_captured"], r["lost_rev_captured"])]
rule_flag_precision = test.loc[test.rule == 1, "label_oos_next3"].mean()
rows.append(("rule: alerts per day (all flagged)", test.groupby("date").rule.sum().mean(), test.groupby("date").rule.sum().mean()))
rows.append(("rule: precision of all flagged", np.nan, rule_flag_precision))
metrics_df = pd.DataFrame(rows, columns=["metric", "model", "baseline_rule"])
metrics_df["lift_vs_rule"] = metrics_df.model / metrics_df.baseline_rule
print(metrics_df.round(4).to_string(index=False))
for m, v, b in rows:
    key = m.replace(" ", "_").replace("@", "_at_").replace("/", "_per_").replace("(", "").replace(")", "").replace(":", "")
    if not np.isnan(v):
        mlflow.log_metric(f"test_{key}", float(v))
    mlflow.log_metric(f"baseline_{key}", float(b))
mlflow.log_table(metrics_df, "test_metrics_vs_baseline.json")
```

```python
imp = (pd.DataFrame({"feature": booster.feature_name(), "gain": booster.feature_importance("gain")})
       .sort_values("gain", ascending=False))
imp["gain_share_pct"] = (100 * imp.gain / imp.gain.sum()).round(2)
print(imp[["feature", "gain_share_pct"]].head(15).to_string(index=False))
mlflow.log_table(imp, "feature_importance.json")
```

## Package as an explainable pyfunc and register in Unity Catalog

```python
import json, os, tempfile

class StockoutRiskModel(mlflow.pyfunc.PythonModel):
    """Returns risk score + top-3 drivers (LightGBM SHAP contributions) for each row."""

    def load_context(self, context):
        import lightgbm as lgb
        self.booster = lgb.Booster(model_file=context.artifacts["booster"])
        meta = json.load(open(context.artifacts["meta"]))
        self.num, self.cat, self.cats = meta["num"], meta["cat"], meta["cats"]

    def _prep(self, df):
        import pandas as pd
        X = df[self.num + self.cat].copy()
        for c in self.num:
            X[c] = pd.to_numeric(X[c], errors="coerce").astype("float64")
        for c in self.cat:
            X[c] = pd.Categorical(X[c], categories=self.cats[c])
        return X

    def predict(self, context, model_input, params=None):
        import numpy as np, pandas as pd
        X = self._prep(model_input)
        score = self.booster.predict(X)
        contrib = self.booster.predict(X, pred_contrib=True)[:, :-1]
        names = np.array(self.num + self.cat)
        top = np.argsort(-contrib, axis=1)[:, :3]
        out = pd.DataFrame({"risk_score": score})
        for i in range(3):
            out[f"driver_{i+1}"] = names[top[:, i]]
            out[f"driver_{i+1}_impact"] = contrib[np.arange(len(X)), top[:, i]].round(4)
        return out

tmp = tempfile.mkdtemp()
booster.save_model(f"{tmp}/booster.txt", num_iteration=booster.best_iteration)
json.dump({"num": FEATURES_NUM, "cat": FEATURES_CAT, "cats": CATS}, open(f"{tmp}/meta.json", "w"))
example = test[FEATURES].head(5)
pyfunc_model = StockoutRiskModel()
from mlflow.models import infer_signature
ctx = type("C", (), {"artifacts": {"booster": f"{tmp}/booster.txt", "meta": f"{tmp}/meta.json"}})()
pyfunc_model.load_context(ctx)
sig = infer_signature(example, pyfunc_model.predict(ctx, example))
info = mlflow.pyfunc.log_model(
    name="model", python_model=pyfunc_model,
    artifacts={"booster": f"{tmp}/booster.txt", "meta": f"{tmp}/meta.json"},
    signature=sig, input_example=example, pip_requirements=["lightgbm==4.6.0", "pandas", "numpy"],
    registered_model_name=MODEL_NAME)
mlflow.end_run()
mv = info.registered_model_version
client.set_registered_model_alias(MODEL_NAME, "champion", mv)
client.update_registered_model(MODEL_NAME, description=(
    "3-day stockout-risk classifier for store-items (M5 Walmart demand + synthetic ERP). "
    f"Test ROC AUC {auc:.3f}, PR AUC {ap:.3f} (baseline rule PR AUC {rule_ap:.3f})."))
print(f"registered {MODEL_NAME} v{mv} -> @champion  (run_id={run.info.run_id})")
print(pyfunc_model.predict(ctx, example).to_string())
```
