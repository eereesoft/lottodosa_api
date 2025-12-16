import pandas as pd

def clean_value(value):
    if pd.isna(value): # pandas DataFrame의 NaN, NaT, None 값을 Python의 None으로 변환
        return None
    return value

def to_str(value):
    if pd.isna(value): # pandas DataFrame의 NaN, NaT, None 값을 Python의 None으로 변환
        return None
    return str(value)

def to_int(value):
    if pd.isna(value): # pandas DataFrame의 NaN, NaT, None 값을 Python의 None으로 변환
        return None
    return int(value)

def to_float(value):
    if pd.isna(value): # pandas DataFrame의 NaN, NaT, None 값을 Python의 None으로 변환
        return None
    return float(value)
