import pandas as pd

import sys

sys.path.append(".")

from model import Model
from environment import Environment

df = pd.read_csv("./data/training_data.csv", index_col=0)
df["Date"] = pd.to_datetime(df["Date"])
df["Open"] = pd.to_datetime(df["Open"])

env = Environment(df, Model(), 42, init_bankroll=1000, min_bet=1, max_bet=100)

evaluation = env.run()

print()
print(f'Final bankroll: {env.bankroll:.2f}')

history = env.get_history()