import pandas as pd
from pathlib import Path

df = pd.read_parquet(Path("data/calendly_marketing.parquet"))
print(df.dtypes)
