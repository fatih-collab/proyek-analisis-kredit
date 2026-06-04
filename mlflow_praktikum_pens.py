# =============================================================================
#  mlflow_praktikum_pens.py
#  MLflow Praktikum — Prosper Loan (BorrowerAPR Prediction)
#  Sesuai modul praktikum: Renovita Edelani, S.ST., M.Tr.Kom. — PENS
#
#  STRUKTUR:
#  ┌─────────────────────────────────────────────────────────────┐
#  │  PART 1 — Baseline Models (3 model, masing-masing 1 run)   │
#  │  PART 2 — Multiple Runs (Grid Search hyperparameter)        │
#  │  PART 3 — Hyperparameter Tuning dengan Optuna (nested run)  │
#  │  PART 4 — Model Registry (register, alias, load & predict)  │
#  └─────────────────────────────────────────────────────────────┘
#
#  FIX v4:
#  - Auto-restore experiment jika status "deleted" (tidak perlu buka UI)
#  - Part 4: loop 50 run, skip run kosong/nested/lama
#  - Part 1: artifact_path diseragamkan ke "model"
#
#  CARA PAKAI:
#  pip install mlflow xgboost lightgbm scikit-learn pandas optuna
#  mlflow ui --port 5000        ← terminal terpisah, biarkan jalan
#  python mlflow_praktikum_pens.py
#  buka: http://127.0.0.1:5000
# =============================================================================

import warnings
import itertools
import time
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")

# =============================================================================
#  KONFIGURASI
# =============================================================================
CSV_PATH        = "cleaning_prosperloandata.csv"
TARGET          = "BorrowerAPR"
IGNORE_COLS     = ["LoanStatus", "ListingCategory (numeric)"]
TEST_SIZE       = 0.2
RANDOM_STATE    = 42

MLFLOW_URI      = "http://127.0.0.1:5000"
EXPERIMENT_NAME = "prosper-loan-borrower-apr"
REGISTERED_NAME = "ProsperAPR_BestModel"

KNOWN_ARTIFACT_PATHS = ["xgb_optuna_best", "model"]
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — Setup Experiment (auto-restore jika deleted)
# ─────────────────────────────────────────────────────────────────────────────
def setup_experiment():
    """
    Set active experiment dengan aman.
    Jika experiment berstatus 'deleted', otomatis di-restore terlebih dahulu
    sehingga tidak perlu buka MLflow UI atau ubah nama experiment secara manual.
    """
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)

    if experiment is not None:
        # Experiment ada tapi statusnya deleted → restore dulu
        if experiment.lifecycle_stage == "deleted":
            print(f"  ⚠ Experiment '{EXPERIMENT_NAME}' berstatus deleted.")
            client.restore_experiment(experiment.experiment_id)
            print(f"  ✔ Experiment berhasil di-restore (id={experiment.experiment_id})")

    # Sekarang aman di-set (akan dibuat baru jika belum ada)
    mlflow.set_experiment(EXPERIMENT_NAME)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — Hitung Metrics Regresi
# ─────────────────────────────────────────────────────────────────────────────
def compute_metrics(y_true, y_pred) -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    return {
        "mae" : round(float(mae),  6),
        "rmse": round(float(rmse), 6),
        "r2"  : round(float(r2),   6),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — Cek artifact path valid dari sebuah run
#  Return (chosen_path, model_uri) atau (None, None) jika kosong
# ─────────────────────────────────────────────────────────────────────────────
def get_artifact_path(client: MlflowClient, run_id: str):
    try:
        artifacts      = client.list_artifacts(run_id)
        artifact_paths = [a.path for a in artifacts]
    except Exception:
        return None, None

    if not artifact_paths:
        return None, None

    for path in KNOWN_ARTIFACT_PATHS:
        if path in artifact_paths:
            return path, f"runs:/{run_id}/{path}"

    return artifact_paths[0], f"runs:/{run_id}/{artifact_paths[0]}"


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD & SPLIT DATA
# ─────────────────────────────────────────────────────────────────────────────
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    import re
    df = df.copy()
    df.columns = [re.sub(r'[^A-Za-z0-9_]', '_', col).strip('_') for col in df.columns]
    df.columns = [re.sub(r'_+', '_', col) for col in df.columns]
    return df


def load_and_split():
    print("\n" + "="*60)
    print("  LOAD DATA")
    print("="*60)

    df = pd.read_csv(CSV_PATH)
    drop_cols = [c for c in IGNORE_COLS if c in df.columns]
    df = df.drop(columns=drop_cols)
    df = df.dropna(subset=[TARGET])
    df = clean_column_names(df)

    X = df.drop(columns=[TARGET])
    y = df[TARGET]
    X = X.select_dtypes(include=[np.number])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    print(f"  ✔ File        : {CSV_PATH}")
    print(f"  ✔ Shape       : {df.shape[0]:,} baris x {df.shape[1]} kolom")
    print(f"  ✔ Fitur       : {X.shape[1]} kolom numerik")
    print(f"  ✔ Train       : {X_train.shape[0]:,} baris")
    print(f"  ✔ Test        : {X_test.shape[0]:,} baris")
    print(f"  ✔ Target mean : {y.mean():.4f}  std : {y.std():.4f}")
    print(f"  ✔ Nama kolom dibersihkan (karakter spesial -> underscore)")

    return X_train, X_test, y_train, y_test, X


# =============================================================================
#  PART 1 — BASELINE MODELS
# =============================================================================
def part1_baseline(X_train, X_test, y_train, y_test):
    print("\n" + "█"*60)
    print("  PART 1 — BASELINE MODELS")
    print("  (XGBoost | LightGBM | Random Forest)")
    print("█"*60)

    setup_experiment()   # ← ganti mlflow.set_tracking_uri + set_experiment

    baselines = {
        "XGBoost_Baseline": XGBRegressor(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            random_state=RANDOM_STATE, verbosity=0,
        ),
        "LightGBM_Baseline": LGBMRegressor(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            random_state=RANDOM_STATE, verbose=-1,
        ),
        "RandomForest_Baseline": RandomForestRegressor(
            n_estimators=100, max_depth=10, min_samples_split=4,
            random_state=RANDOM_STATE,
        ),
    }

    baseline_run_ids = {}

    for run_name, model in baselines.items():
        print(f"\n  Run: [{run_name}]")

        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_param("model", type(model).__name__)
            clean = {k: str(v)[:250] for k, v in model.get_params().items() if v is not None}
            mlflow.log_params(clean)

            model.fit(X_train, y_train)
            y_pred  = model.predict(X_test)
            metrics = compute_metrics(y_test, y_pred)

            mlflow.log_metric("mae",  metrics["mae"])
            mlflow.log_metric("rmse", metrics["rmse"])
            mlflow.log_metric("r2",   metrics["r2"])

            sample_in  = X_test.head(5)
            sample_out = pd.DataFrame({"BorrowerAPR_pred": y_pred[:5]})
            signature  = mlflow.models.infer_signature(sample_in, sample_out)

            mlflow.sklearn.log_model(
                sk_model=model, artifact_path="model",
                signature=signature, input_example=sample_in,
            )

            baseline_run_ids[run_name] = run.info.run_id
            print(f"     R2={metrics['r2']:.4f}  MAE={metrics['mae']:.6f}  RMSE={metrics['rmse']:.6f}")
            print(f"     run_id: {run.info.run_id[:12]}...")

    print("\n  ✅  Part 1 selesai")
    return baseline_run_ids


# =============================================================================
#  PART 2 — MULTIPLE RUNS (Grid Search)
# =============================================================================
def part2_multiple_runs(X_train, X_test, y_train, y_test):
    print("\n" + "█"*60)
    print("  PART 2 — MULTIPLE RUNS (Grid Search)")
    print("  XGBoost: n_estimators x max_depth x learning_rate")
    print("█"*60)

    setup_experiment()

    param_grid = {
        "n_estimators" : [50, 100, 200],
        "max_depth"    : [3, 6, 10],
        "learning_rate": [0.01, 0.1, 0.3],
    }

    keys   = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))
    print(f"\n  Total kombinasi: {len(combos)} run\n")

    grid_run_ids = {}

    for combo in combos:
        params   = dict(zip(keys, combo))
        n_est    = params["n_estimators"]
        max_d    = params["max_depth"]
        lr       = params["learning_rate"]
        run_name = f"XGB_n{n_est}_d{max_d}_lr{lr}"

        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_param("model",         "XGBRegressor")
            mlflow.log_param("n_estimators",  n_est)
            mlflow.log_param("max_depth",     max_d)
            mlflow.log_param("learning_rate", lr)

            model = XGBRegressor(
                n_estimators=n_est, max_depth=max_d, learning_rate=lr,
                random_state=RANDOM_STATE, verbosity=0,
            )
            model.fit(X_train, y_train)
            y_pred  = model.predict(X_test)
            metrics = compute_metrics(y_test, y_pred)

            mlflow.log_metric("mae",  metrics["mae"])
            mlflow.log_metric("rmse", metrics["rmse"])
            mlflow.log_metric("r2",   metrics["r2"])
            mlflow.sklearn.log_model(model, "model")

            grid_run_ids[run_name] = {"run_id": run.info.run_id, "r2": metrics["r2"]}

        print(f"  n_est={n_est:>3}  depth={max_d}  lr={lr:.2f}  "
              f"->  R2={metrics['r2']:.4f}  RMSE={metrics['rmse']:.6f}")

    best_grid = max(grid_run_ids.items(), key=lambda x: x[1]["r2"])
    print(f"\n  🏆 Best grid run : {best_grid[0]}  R2={best_grid[1]['r2']:.4f}")
    print("\n  ✅  Part 2 selesai")

    return grid_run_ids, best_grid


# =============================================================================
#  PART 3 — HYPERPARAMETER TUNING (Optuna + Nested Runs)
# =============================================================================
def part3_optuna_tuning(X_train, X_test, y_train, y_test):
    print("\n" + "█"*60)
    print("  PART 3 — HYPERPARAMETER TUNING (Optuna + Nested Runs)")
    print("█"*60)

    setup_experiment()

    def objective(trial):
        n_estimators  = trial.suggest_int("n_estimators",  50, 300)
        max_depth     = trial.suggest_int("max_depth",      3,  12)
        learning_rate = trial.suggest_float("learning_rate", 0.01, 0.3, log=True)
        subsample     = trial.suggest_float("subsample",    0.6, 1.0)
        colsample     = trial.suggest_float("colsample_bytree", 0.6, 1.0)

        model = XGBRegressor(
            n_estimators=n_estimators, max_depth=max_depth,
            learning_rate=learning_rate, subsample=subsample,
            colsample_bytree=colsample, random_state=RANDOM_STATE, verbosity=0,
        )
        model.fit(X_train, y_train)
        metrics = compute_metrics(y_test, model.predict(X_test))

        with mlflow.start_run(nested=True):
            mlflow.log_param("model",            "XGBRegressor")
            mlflow.log_param("n_estimators",     n_estimators)
            mlflow.log_param("max_depth",        max_depth)
            mlflow.log_param("learning_rate",    round(learning_rate, 5))
            mlflow.log_param("subsample",        round(subsample, 3))
            mlflow.log_param("colsample_bytree", round(colsample, 3))
            mlflow.log_metric("mae",  metrics["mae"])
            mlflow.log_metric("rmse", metrics["rmse"])
            mlflow.log_metric("r2",   metrics["r2"])

        return metrics["r2"]

    print(f"\n  Menjalankan Optuna (20 trials) ...")

    optuna_run_id  = None
    best_model_xgb = None

    with mlflow.start_run(run_name="Optuna_Optimization") as parent_run:
        optuna_run_id = parent_run.info.run_id

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=20, show_progress_bar=False)

        best_params = study.best_params
        best_r2     = study.best_value

        print(f"\n  Best Params : {best_params}")
        print(f"  Best R2     : {best_r2:.4f}")

        best_model_xgb = XGBRegressor(
            **best_params, random_state=RANDOM_STATE, verbosity=0,
        )
        best_model_xgb.fit(X_train, y_train)
        y_pred  = best_model_xgb.predict(X_test)
        metrics = compute_metrics(y_test, y_pred)

        mlflow.log_param("model",       "XGBRegressor")
        mlflow.log_param("search_type", "Optuna")
        mlflow.log_params({k: str(v)[:250] for k, v in best_params.items()})
        mlflow.log_metric("mae",  metrics["mae"])
        mlflow.log_metric("rmse", metrics["rmse"])
        mlflow.log_metric("r2",   metrics["r2"])

        sample_in  = X_test.head(5)
        sample_out = pd.DataFrame({"BorrowerAPR_pred": y_pred[:5]})
        signature  = mlflow.models.infer_signature(sample_in, sample_out)

        mlflow.sklearn.log_model(
            sk_model=best_model_xgb, artifact_path="xgb_optuna_best",
            signature=signature, input_example=sample_in,
        )

    print(f"\n  ✔ Parent run_id : {optuna_run_id[:12]}...")
    print(f"  ✔ Best R2       : {best_r2:.4f}")
    print("\n  ✅  Part 3 selesai")

    return optuna_run_id, best_model_xgb, best_r2


# =============================================================================
#  PART 4 — MODEL REGISTRY
# =============================================================================
def part4_model_registry(optuna_run_id: str, X_test: pd.DataFrame, y_test):
    print("\n" + "█"*60)
    print("  PART 4 — MODEL REGISTRY")
    print("  Register -> Alias @champion -> Load & Predict")
    print("█"*60)

    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()

    # ── 4a. Cari run terbaik yang PUNYA artifact (skip run lama/kosong) ───────
    print("\n  [4a] Mencari run terbaik yang memiliki artifact model ...")

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise ValueError(f"Experiment '{EXPERIMENT_NAME}' tidak ditemukan.")

    runs = client.search_runs(
        experiment_ids = [experiment.experiment_id],
        filter_string  = "",
        order_by       = ["metrics.r2 DESC"],
        max_results    = 50,
    )

    best_run    = None
    best_run_id = None
    model_uri   = None

    for run in runs:
        rid  = run.info.run_id
        tags = run.data.tags

        # Skip nested run (trial Optuna)
        if tags.get("mlflow.parentRunId"):
            continue

        chosen_path, uri = get_artifact_path(client, rid)

        if chosen_path is not None:
            best_run    = run
            best_run_id = rid
            model_uri   = uri
            print(f"  ✔ Run dipilih  : {rid[:12]}...  artifact: '{chosen_path}'")
            break
        else:
            print(f"  ⚠ Skip {rid[:12]}... — artifact kosong")

    if best_run is None:
        raise ValueError(
            "Tidak ada run dengan artifact model yang valid.\n"
            "Pastikan Part 1, 2, atau 3 sudah selesai dijalankan tanpa error."
        )

    best_r2 = best_run.data.metrics.get("r2", 0)
    print(f"  ✔ Best R2      : {best_r2:.4f}")
    print(f"  ✔ Run name     : {best_run.data.tags.get('mlflow.runName', '-')}")
    print(f"  ✔ Model URI    : {model_uri}")

    # ── 4b. Register model ────────────────────────────────────────────────────
    print(f"\n  [4b] Register model ke Registry ...")
    print(f"  Registry name : {REGISTERED_NAME}")

    registered = [m.name for m in client.search_registered_models()]
    if REGISTERED_NAME not in registered:
        client.create_registered_model(
            name        = REGISTERED_NAME,
            description = (
                "Model prediksi BorrowerAPR — Prosper Loan Dataset. "
                "Algoritma terbaik dari XGBoost, LightGBM, RandomForest "
                "dengan Optuna hyperparameter tuning. PENS MLOps Project."
            ),
        )
        print(f"  ✔ Registered model baru dibuat")

    result  = mlflow.register_model(model_uri=model_uri, name=REGISTERED_NAME)
    version = result.version
    print(f"  ✔ Model terdaftar -> Version {version}")

    print("  ⏳ Menunggu status READY ...")
    for _ in range(30):
        mv = client.get_model_version(REGISTERED_NAME, version)
        if mv.status == "READY":
            print(f"  ✔ Status : READY")
            break
        time.sleep(1)

    client.update_model_version(
        name        = REGISTERED_NAME,
        version     = version,
        description = f"Best model. R2={best_r2:.4f}. Run ID: {best_run_id[:8]}",
    )

    # ── 4c. Giving Alias ──────────────────────────────────────────────────────
    print(f"\n  [4c] Memberikan Alias ...")

    try:
        client.set_registered_model_alias(
            name=REGISTERED_NAME, alias="champion", version=version,
        )
        print(f"  ✔ Alias @champion -> Version {version}")

        if int(version) > 1:
            prev = str(int(version) - 1)
            client.set_registered_model_alias(
                name=REGISTERED_NAME, alias="candidate", version=prev,
            )
            print(f"  ✔ Alias @candidate -> Version {prev}")

    except Exception as e:
        print(f"  ⚠ Alias tidak tersedia: {e}")
        print(f"  Fallback: gunakan stage 'Production'")
        client.transition_model_version_stage(
            name=REGISTERED_NAME, version=version,
            stage="Production", archive_existing_versions=True,
        )
        print(f"  ✔ Version {version} -> Stage: Production")

    # ── 4d. Load & Predict ────────────────────────────────────────────────────
    print(f"\n  [4d] Load Model dari Registry -> Prediksi Data Baru ...")

    loaded_model  = None
    load_attempts = [
        (f"models:/{REGISTERED_NAME}@champion",   "via @champion alias"),
        (f"models:/{REGISTERED_NAME}/Production", "via /Production stage"),
        (f"models:/{REGISTERED_NAME}/{version}",  f"via /Version {version}"),
    ]

    for uri, label in load_attempts:
        try:
            loaded_model = mlflow.sklearn.load_model(uri)
            print(f"  ✔ Model loaded {label}")
            break
        except Exception:
            continue

    if loaded_model is None:
        raise RuntimeError("Gagal load model dari Registry.")

    sample      = X_test.head(10)
    y_true_samp = y_test.head(10).values
    y_pred_samp = loaded_model.predict(sample)

    print(f"\n  Contoh Prediksi BorrowerAPR (10 data):")
    print(f"  {'No':>4}  {'Actual':>12}  {'Predicted':>12}  {'Error':>12}")
    print(f"  {'-'*46}")
    for i, (act, pred) in enumerate(zip(y_true_samp, y_pred_samp)):
        print(f"  {i+1:>4}  {act:>12.6f}  {pred:>12.6f}  {abs(act-pred):>12.6f}")

    final_metrics = compute_metrics(y_true_samp, y_pred_samp)
    print(f"\n  Sample metrics -> R2={final_metrics['r2']:.4f}  "
          f"MAE={final_metrics['mae']:.6f}  RMSE={final_metrics['rmse']:.6f}")

    print("\n  ✅  Part 4 selesai")
    return version


# =============================================================================
#  MAIN
# =============================================================================
if __name__ == "__main__":

    print("\n" + "█"*60)
    print("  MLflow Praktikum — PENS Sains Data Terapan")
    print("  Prosper Loan — BorrowerAPR Prediction")
    print("█"*60)
    print(f"\n  MLflow UI : {MLFLOW_URI}")
    print(f"  Experiment: {EXPERIMENT_NAME}")
    print(f"  Registry  : {REGISTERED_NAME}\n")

    X_train, X_test, y_train, y_test, X_full = load_and_split()

    baseline_run_ids                   = part1_baseline(X_train, X_test, y_train, y_test)
    grid_run_ids, best_grid            = part2_multiple_runs(X_train, X_test, y_train, y_test)
    optuna_run_id, best_model, best_r2 = part3_optuna_tuning(X_train, X_test, y_train, y_test)
    version                            = part4_model_registry(optuna_run_id, X_test, y_test)

    print("\n" + "█"*60)
    print("  ✅  SEMUA PART SELESAI")
    print("█"*60)
    print(f"\n  Experiment  : {EXPERIMENT_NAME}")
    print(f"  Registry    : {REGISTERED_NAME}  (v{version})")
    print(f"  Best R2     : {best_r2:.4f}")
    print(f"  MLflow UI   : {MLFLOW_URI}")
    print()
    print("  ── Cara Load Model di Script Lain ──────────────────────")
    print(f'  import mlflow')
    print(f'  mlflow.set_tracking_uri("{MLFLOW_URI}")')
    print(f'  model = mlflow.sklearn.load_model(')
    print(f'      "models:/{REGISTERED_NAME}@champion"')
    print(f'  )')
    print(f'  preds = model.predict(X_baru)')
    print("  ────────────────────────────────────────────────────────")
    print()
    print("  ── Checklist Tugas (slide 36) ──────────────────────────")
    print("  ✔ 3 Baseline model (XGBoost, LightGBM, Random Forest)")
    print("  ✔ Multiple runs grid search (27 kombinasi hyperparameter)")
    print("  ✔ Hyperparameter tuning Optuna (20 trials, nested runs)")
    print("  ✔ Model Registry + Alias @champion")
    print("  ✔ Load model by alias & prediksi data baru")
    print("  ────────────────────────────────────────────────────────")
    print()
