# Simple example to train and save model based on db/access_logs.json
import os, json, pickle
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
BASE = os.path.join(os.path.dirname(__file__), "..")
LOG_PATH = os.path.join(BASE, "db", "access_logs.json")
MODEL_OUT = os.path.join(BASE, "ai_model.pkl")

def load_logs():
    if not os.path.exists(LOG_PATH): return []
    with open(LOG_PATH,"r") as f:
        return json.load(f)

def featurize(logs):
    rows=[]
    for e in logs:
        ts = e.get("ts","")
        hour = int(ts[11:13]) if len(ts)>=13 else 0
        action = 0 if e.get("action")=="upload" else 1
        rows.append({"hour":hour,"action":action})
    return pd.DataFrame(rows)

logs = load_logs()
df = featurize(logs)
if len(df)<5:
    print("Not enough logs to train. Add more access entries by uploading/downloading files.")
else:
    X = df[["hour","action"]]
    y = [1 if r["hour"]<6 else 0 for idx,r in df.iterrows()]
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X,y)
    with open(MODEL_OUT,"wb") as f:
        pickle.dump(clf,f)
    print("Model trained and saved to", MODEL_OUT)