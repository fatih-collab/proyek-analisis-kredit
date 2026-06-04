# cek_artifact.py — jalankan terpisah
import mlflow
from mlflow import MlflowClient

mlflow.set_tracking_uri("http://127.0.0.1:5000")
client = MlflowClient()

exp = client.get_experiment_by_name("prosper-loan-borrower-apr")
runs = client.search_runs(
    experiment_ids=[exp.experiment_id],
    order_by=["attributes.start_time DESC"],
    max_results=10,
)

for r in runs:
    artifacts = client.list_artifacts(r.info.run_id)
    print(f"run: {r.info.run_id[:12]}  name: {r.data.tags.get('mlflow.runName','?'):<30}  artifacts: {[a.path for a in artifacts]}")