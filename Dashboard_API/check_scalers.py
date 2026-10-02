import joblib
import sys

scalers = joblib.load(r"F:\New folder (7)\project5\project\task2_dir\scalers.joblib")
print(list(scalers.keys()))
