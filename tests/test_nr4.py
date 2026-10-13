import pandas as pd
from nr4_scanner import NR4Scanner

def test_nr4_true_condition():
    # 25 days of data, last day has range of 5 (<= 10, 15, 20)
    data = []
    for i in range(25):
        rng = 5.0 if i == 24 else (10.0 + (i % 3) * 5.0)
        data.append({"high": 100.0 + rng, "low": 100.0, "close": 105.0})
    df = pd.DataFrame(data)
    res = NR4Scanner.evaluate_nr4(df)
    assert res["is_nr4"] is True
    assert res["daily_range"] == 5.0

def test_nr4_false_condition():
    data = []
    for i in range(25):
        rng = 30.0 if i == 24 else 10.0
        data.append({"high": 100.0 + rng, "low": 100.0, "close": 105.0})
    df = pd.DataFrame(data)
    res = NR4Scanner.evaluate_nr4(df)
    assert res["is_nr4"] is False

