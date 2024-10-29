import numpy as np
import pandas as pd

class Model:

    def place_bets(self, summary: pd.DataFrame, opps: pd.DataFrame, inc: pd.DataFrame):
        date = summary.iloc[0]["Date"]
        bankroll = summary.iloc[0]["Bankroll"]
        print(f"{date} Bankroll: {bankroll:.2f}   ", end="\r")
        min_bet = summary.iloc[0]["Min_bet"]
        N = len(opps)
        bets = np.zeros((N, 2))
        bets[np.arange(N), np.random.choice([0, 1])] = min_bet
        bets = pd.DataFrame(data=bets, columns=["BetH", "BetA"], index=opps.index)
        return bets
    