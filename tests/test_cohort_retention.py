from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from cohort_retention import build_cohort, to_rates, weighted_retention


def make_df(rows):
    df = pd.DataFrame(rows, columns=["user_id", "behavior_type", "date"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_cohort_day_zero_is_always_100_percent():
    df = make_df(
        [
            [1, "buy", "2017-11-25"],
            [1, "pv", "2017-11-26"],
            [2, "buy", "2017-11-25"],
            [2, "buy", "2017-11-26"],
            [3, "buy", "2017-11-26"],
        ]
    )

    result = build_cohort(df, cohort_type="purchase", max_day=2)
    sizes = result["sizes"]
    activity = to_rates(result["activity_counts"], sizes, result["observable"])
    purchase = to_rates(result["purchase_counts"], sizes, result["observable"])

    first_day = pd.Timestamp("2017-11-25")
    second_day = pd.Timestamp("2017-11-26")

    assert sizes.to_dict() == {first_day: 2, second_day: 1}
    assert activity.loc[first_day, 0] == 1.0
    assert activity.loc[second_day, 0] == 1.0

    # 11-25 队列第 1 天：用户 1 浏览、用户 2 购买 => 2/2 活跃
    assert activity.loc[first_day, 1] == 1.0
    # 只有用户 2 再次购买 => 1/2 购买留存
    assert purchase.loc[first_day, 1] == 0.5


def test_unobservable_days_are_nan_not_zero():
    df = make_df(
        [
            [1, "buy", "2017-11-25"],
            [1, "buy", "2017-11-26"],
            [2, "buy", "2017-11-26"],
        ]
    )

    result = build_cohort(df, cohort_type="purchase", max_day=2)
    sizes = result["sizes"]
    activity = to_rates(result["activity_counts"], sizes, result["observable"])
    second_day = pd.Timestamp("2017-11-26")

    # 数据只到 11-26，11-26 队列的第 1 天不可观察，必须是 NaN 而不是 0
    assert pd.isna(activity.loc[second_day, 1])
    assert pd.isna(activity.loc[second_day, 2])

    summary = weighted_retention(result["activity_counts"], sizes, result["observable"])
    day1 = summary.loc[summary["day"] == 1].iloc[0]
    assert day1["cohorts"] == 1  # 只有 11-25 队列能观察到第 1 天
    assert day1["denominator"] == 1  # 11-25 队列只有用户 1
    assert day1["rate"] == 1.0
