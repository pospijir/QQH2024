from typing import Optional

import numpy as np
import pandas as pd


class IModel:
    def place_bets(self, summary: pd.DataFrame, inc: pd.DataFrame, opps: pd.DataFrame):
        raise NotImplementedError()


class Environment:

    result_cols = ["H", "A"]

    odds_cols = ["OddsH", "OddsA"]

    bet_cols = ["BetH", "BetA"]

    score_cols = ["HSC", "ASC"]

    # fmt: off
    feature_cols = [
        "HFGM", "AFGM", "HFGA", "AFGA", "HFG3M", "AFG3M", "HFG3A", "AFG3A", 
        "HFTM", "AFTM", "HFTA", "AFTA", "HORB", "AORB", "HDRB", "ADRB", "HRB", "ARB", "HAST",
        "AAST", "HSTL", "ASTL", "HBLK", "ABLK", "HTOV", "ATOV", "HPF", "APF",
    ]
    # fmt: on

    def __init__(
        self,
        df: pd.DataFrame,
        model: IModel,
        start_date: Optional[pd.Timestamp] = None,
        end_date: Optional[pd.Timestamp] = None,
        last_recorded_date: Optional[pd.Timestamp] = None,
        init_bankroll=1000.0,
        min_bet=0,
        max_bet=np.inf,
    ):

        self.df = df
        self.df[self.bet_cols] = 0.0

        self.start_date: pd.Timestamp = (
            start_date if start_date is not None else self.df["Open"].min()
        )
        self.end_date: pd.Timestamp = (
            end_date if end_date is not None else self.df["Date"].max()
        )
        self.last_recorded_date = last_recorded_date

        self.model = model

        self.bankroll = init_bankroll
        self.min_bet = min_bet
        self.max_bet = max_bet

        self.last_seen = pd.to_datetime("1900-01-01")

        self.history = {"Date": [], "Bankroll": [], "Cash_Invested": []}

    def run(self):
        for date in pd.date_range(self.start_date, self.end_date):

            # get game results from previous day(s) and evaluate bets
            inc = self._next_date(date)

            # get betting options for current day
            # today's games + next day(s) games -> self.odds_availability
            opps = self._get_options(date)
            if opps.empty:
                continue

            summary = self._generate_summary(date)

            bets = self.model.place_bets(opps, summary, inc)

            validated_bets = self._validate_bets(bets, opps)
            
            self._place_bets(date, validated_bets)

        # evaluate bets of last game day
        self._next_date(self.end_date + pd.to_timedelta(1, "days"))

        return self.df

    def get_history(self):
        history = pd.DataFrame(data=self.history)
        history = history.set_index("Date")
        return history

    def _next_date(self, date: pd.Timestamp):
        inc = self.df.loc[(self.df["Date"] > self.last_seen) & (self.df["Date"] < date)]
        self.last_seen = inc["Date"].max() if not inc.empty else self.last_seen

        if not inc.empty:
            # evaluate bets
            b = inc[self.bet_cols].values
            o = inc[self.odds_cols].values
            r = inc[self.result_cols].values
            winnings = (b * r * o).sum(axis=1).sum()

            # update bankroll with the winnings
            self.bankroll += winnings

            # save current bankroll
            self._save_state(date + pd.Timedelta(6, unit="h"), 0.0)

        return inc

    def _get_options(self, date: pd.Timestamp):
        opps = self.df.loc[(self.df["Open"] <= date) & (self.df["Date"] >= date)]
        opps = opps.loc[opps[self.odds_cols].sum(axis=1) > 0]
        return opps.drop(
            [
                *self.score_cols,
                *self.result_cols,
                *self.feature_cols,
                "Open",
            ],
            axis=1,
        )

    def _validate_bets(self, bets: pd.DataFrame, opps: pd.DataFrame):
        # print("Validating bets")
        rows = bets.index.intersection(opps.index)
        cols = bets.columns.intersection(self.bet_cols)

        # allow bets only on the send opportunities
        validated_bets = bets.loc[rows, cols]

        # reject bets lower than min_bet
        validated_bets[validated_bets < self.min_bet] = 0.0

        # reject bets higher than max_bet
        validated_bets[validated_bets > self.max_bet] = 0.0

        # reject bets if there are no sufficient funds left
        if validated_bets.sum().sum() > self.bankroll:
            validated_bets.loc[:, :] = 0.0

        return validated_bets

    def _place_bets(self, date: pd.Timestamp, bets: pd.DataFrame):
        self.df.loc[bets.index, self.bet_cols] = self.df.loc[
            bets.index, self.bet_cols
        ].add(bets, fill_value=0)

        # Decrease the bankroll with placed bets
        self.bankroll -= bets.values.sum()

        self._save_state(date + pd.Timedelta(23, unit="h"), bets.values.sum())

    def _generate_summary(self, date: pd.Timestamp):
        summary = {
            "Bankroll": self.bankroll,
            "Date": date,
            "Min_bet": self.min_bet,
            "Max_bet": self.max_bet,
        }
        return pd.Series(summary).to_frame().T

    def _save_state(self, date: pd.Timestamp, cash_invested: float):
        self.history["Date"].append(date)
        self.history["Bankroll"].append(self.bankroll)
        self.history["Cash_Invested"].append(cash_invested)
        print(f"{date.date()} bankroll: {self.bankroll:.2f}", end="\r")
