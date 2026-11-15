"""Cohort retention analysis for Taobao user behavior data.

What is a cohort?
    Users grouped by the date they first did something. By default we group by
    the date of a user's first purchase ("首购队列").

What is retention?
    On day N after the cohort date, how many users in that cohort were still
    active (any behavior) or still buying (behavior_type == "buy").

Important detail:
    A cohort created on 2017-12-03 can only be observed on day 0, because the
    dataset ends that day. Those unobservable cells are written as "—" instead
    of 0, otherwise the matrix would look like a collapse that never happened.

Usage:
    python src/cohort_retention.py
    python src/cohort_retention.py --input data/cleaned_user_behavior.csv
    python src/cohort_retention.py --cohort-type active
    python src/cohort_retention.py --compare-input data/cleaned_user_behavior_random_sample.csv --compare-label "随机按行抽样"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 不弹窗，直接存图

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "cleaned_user_behavior.csv"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "cohort_retention.md"
DEFAULT_FIG_DIR = PROJECT_ROOT / "reports" / "figures"
DEFAULT_MATRIX_DIR = PROJECT_ROOT / "reports"
FONT_CANDIDATES = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]


# ---------------------------------------------------------------------------
# 1. 读数据
# ---------------------------------------------------------------------------
def load_behavior(path: Path) -> pd.DataFrame:
    """Read a cleaned behavior CSV and normalize the two columns we rely on."""
    df = pd.read_csv(path)
    required = {"user_id", "behavior_type", "date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} 缺少必要字段: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["behavior_type"] = df["behavior_type"].astype(str).str.lower().str.strip()
    df = df[df["behavior_type"].isin(["pv", "fav", "cart", "buy"])]
    if df.empty:
        raise ValueError(f"{path} 中没有有效行为记录")
    return df


# ---------------------------------------------------------------------------
# 2. 建队列 + 算留存
# ---------------------------------------------------------------------------
def build_cohort(df: pd.DataFrame, cohort_type: str = "purchase", max_day: int = 8) -> dict:
    """Group users into cohorts and count retained users per day.

    Returned counts are *users*, not behavior rows: a user who views 10 items on
    day 3 still counts once.
    """
    if cohort_type == "purchase":
        base = df[df["behavior_type"] == "buy"]
        if base.empty:
            raise ValueError("数据中没有购买记录，无法按首购日期建队列")
    elif cohort_type == "active":
        base = df
    else:
        raise ValueError("cohort_type 只能是 'purchase' 或 'active'")

    # 每个用户第一次发生 base 行为的日期 = 队列标签
    first = base.groupby("user_id")["date"].min().rename("cohort")
    merged = df.merge(first, left_on="user_id", right_index=True)

    # 行为日期 - 队列日期 = 第几天；只保留 0..max_day
    merged["day"] = (merged["date"] - merged["cohort"]).dt.days
    merged = merged[(merged["day"] >= 0) & (merged["day"] <= max_day)]

    sizes = first.value_counts().sort_index().rename("users")
    cohort_dates = sizes.index
    days = list(range(max_day + 1))

    def count_unique(frame: pd.DataFrame) -> pd.DataFrame:
        matrix = (
            frame.groupby(["cohort", "day"])["user_id"]
            .nunique()
            .unstack(fill_value=0)
        )
        return matrix.reindex(index=cohort_dates, columns=days, fill_value=0)

    activity_counts = count_unique(merged)
    purchase_counts = count_unique(merged[merged["behavior_type"] == "buy"])

    # 可观察掩码：队列日期 + N 天 是否仍在数据窗口内
    end_date = df["date"].max()
    observable = pd.DataFrame(
        [
            [(cohort + pd.Timedelta(days=day)) <= end_date for day in days]
            for cohort in cohort_dates
        ],
        index=cohort_dates,
        columns=days,
    )

    return {
        "cohort_type": cohort_type,
        "sizes": sizes,
        "activity_counts": activity_counts,
        "purchase_counts": purchase_counts,
        "observable": observable,
        "end_date": end_date,
        "start_date": df["date"].min(),
        "users": int(df["user_id"].nunique()),
        "cohort_users": int(len(first)),
        "avg_behaviors": len(df) / df["user_id"].nunique(),
        "dau": df.groupby("date")["user_id"].nunique(),
    }


def to_rates(counts: pd.DataFrame, sizes: pd.Series, observable: pd.DataFrame) -> pd.DataFrame:
    """Counts -> retention rates; unobservable cells become NaN (shown as —)."""
    return counts.div(sizes, axis=0).where(observable)


def weighted_retention(
    counts: pd.DataFrame, sizes: pd.Series, observable: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate retention per day, weighting each cohort by its size.

    Only cohorts that can actually observe that day enter the denominator.
    """
    rows = []
    for day in counts.columns:
        mask = observable[day]
        denominator = int(sizes[mask].sum())
        retained = int(counts.loc[mask, day].sum())
        rows.append(
            {
                "day": day,
                "cohorts": int(mask.sum()),
                "denominator": denominator,
                "retained": retained,
                "rate": retained / denominator if denominator else None,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. 画图
# ---------------------------------------------------------------------------
def save_heatmap(rates: pd.DataFrame, title: str, output_path: Path) -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.sans-serif"] = FONT_CANDIDATES
    plt.rcParams["axes.unicode_minus"] = False

    data = rates * 100
    fig, ax = plt.subplots(figsize=(10, 4.8))
    sns.heatmap(
        data,
        annot=True,
        fmt=".0f",
        cmap="YlGnBu",
        mask=data.isna(),
        linewidths=0.5,
        cbar_kws={"label": "留存率 (%)"},
        ax=ax,
    )
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("队列首日后的第几天")
    ax.set_ylabel("队列（首次购买日期）")
    ax.set_xticklabels([f"D{int(day)}" for day in rates.columns], rotation=0)
    ax.set_yticklabels([str(index.date()) for index in rates.index], rotation=0)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. 写 Markdown
# ---------------------------------------------------------------------------
def pct(value: float | None) -> str:
    return "—" if value is None or pd.isna(value) else f"{value * 100:.1f}%"


def display_path(path: Path) -> str:
    """Prefer a project-relative path in the report; fall back to absolute."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def save_matrix(df: pd.DataFrame, path: Path) -> Path:
    """Write a matrix CSV, tolerating the file being open in Excel/WPS.

    If the file is locked but its content already matches, keep it. If it is
    locked and stale, write a `_new.csv` next to it and warn the user.
    """
    try:
        df.to_csv(path, encoding="utf-8-sig")
        return path
    except PermissionError:
        try:
            existing = pd.read_csv(path, index_col=0)
            existing.index = pd.to_datetime(existing.index)
            existing.columns = [int(column) for column in existing.columns]
            existing = existing.reindex(index=df.index, columns=df.columns)
            diff = (existing.round(4).fillna(-1) - df.round(4).fillna(-1)).abs().max().max()
            if pd.notna(diff) and diff < 1e-4:
                print(f"WARNING: {path.name} 正在被占用，但内容与本次结果一致，保留原文件。")
                return path
        except Exception:
            pass
        fallback = path.with_name(f"{path.stem}_new{path.suffix}")
        df.to_csv(fallback, encoding="utf-8-sig")
        print(f"WARNING: {path.name} 正在被占用，本次结果已写入 {fallback.name}。")
        return fallback


def rate_table(rates: pd.DataFrame, sizes: pd.Series) -> str:
    headers = ["队列", "人数"] + [f"D{int(day)}" for day in rates.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for cohort, row in rates.iterrows():
        cells = [str(cohort.date()), str(int(sizes[cohort]))]
        cells += [pct(value) for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def summary_table(activity: pd.DataFrame, purchase: pd.DataFrame) -> str:
    merged = activity.merge(
        purchase,
        on="day",
        suffixes=("_active", "_purchase"),
        how="outer",
    )
    lines = [
        "| 第几天 | 可观察队列数 | 活跃留存 | 购买留存 |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in merged.iterrows():
        lines.append(
            f"| D{int(row['day'])} | {int(row['cohorts_active'])} | "
            f"{pct(row['rate_active'])} | {pct(row['rate_purchase'])} |"
        )
    return "\n".join(lines)


def comparison_table(
    primary_activity: pd.DataFrame,
    primary_purchase: pd.DataFrame,
    compare_activity: pd.DataFrame,
    compare_purchase: pd.DataFrame,
    primary_label: str,
    compare_label: str,
) -> str:
    lines = [
        f"| 指标 | {primary_label} | {compare_label} |",
        "| --- | --- | --- |",
    ]
    for day in [1, 3, 7]:
        act_a = primary_activity.loc[primary_activity["day"] == day, "rate"]
        act_b = compare_activity.loc[compare_activity["day"] == day, "rate"]
        buy_a = primary_purchase.loc[primary_purchase["day"] == day, "rate"]
        buy_b = compare_purchase.loc[compare_purchase["day"] == day, "rate"]
        lines.append(
            f"| D{day} 活跃留存 | {pct(act_a.iloc[0]) if len(act_a) else '—'} | "
            f"{pct(act_b.iloc[0]) if len(act_b) else '—'} |"
        )
        lines.append(
            f"| D{day} 购买留存 | {pct(buy_a.iloc[0]) if len(buy_a) else '—'} | "
            f"{pct(buy_b.iloc[0]) if len(buy_b) else '—'} |"
        )
    return "\n".join(lines)


def write_report(
    result: dict,
    output_path: Path,
    figure_dir: Path,
    matrix_dir: Path,
    figure_prefix: str,
    compare: dict | None = None,
    compare_label: str = "对照样本",
    primary_label: str = "首购样本",
) -> None:
    sizes = result["sizes"]
    activity = to_rates(result["activity_counts"], sizes, result["observable"])
    purchase = to_rates(result["purchase_counts"], sizes, result["observable"])
    activity_summary = weighted_retention(result["activity_counts"], sizes, result["observable"])
    purchase_summary = weighted_retention(result["purchase_counts"], sizes, result["observable"])

    figure_dir.mkdir(parents=True, exist_ok=True)
    activity_png = figure_dir / f"{figure_prefix}_activity.png"
    purchase_png = figure_dir / f"{figure_prefix}_purchase.png"
    cohort_label = "首购" if result["cohort_type"] == "purchase" else "首次活跃"
    save_heatmap(activity, f"{cohort_label} Cohort 活跃留存率", activity_png)
    save_heatmap(purchase, f"{cohort_label} Cohort 购买留存率", purchase_png)

    matrix_dir.mkdir(parents=True, exist_ok=True)
    activity_matrix_path = save_matrix(
        activity.round(4), matrix_dir / f"{figure_prefix}_activity_matrix.csv"
    )
    purchase_matrix_path = save_matrix(
        purchase.round(4), matrix_dir / f"{figure_prefix}_purchase_matrix.csv"
    )

    def retention_bullet(day: int, label: str, frame: pd.DataFrame) -> str:
        hit = frame.loc[frame["day"] == day]
        if hit.empty or pd.isna(hit["rate"].iloc[0]):
            return f"- **D{day} {label}：无法观察**（没有队列能覆盖到第 {day} 天）。"
        rate = float(hit["rate"].iloc[0])
        cohorts = int(hit["cohorts"].iloc[0])
        if label == "活跃留存" and rate > 0.9:
            return (
                f"- **D{day} 活跃留存 {pct(rate)}**：仅 {cohorts} 个队列可观察，"
                "且落在全站活跃高峰日，**不建议当作留存结论**。"
            )
        return f"- **D{day} {label} {pct(rate)}**：{cohorts} 个队列可观察。"

    min_cohort = int(sizes.min())
    max_cohort = int(sizes.max())
    compare_avg_behaviors = compare["avg_behaviors"] if compare is not None else 0.0
    day1_rows = activity_summary.loc[activity_summary["day"] == 1, "rate"]
    day1_activity_text = pct(day1_rows.iloc[0]) if len(day1_rows) else "—"
    if result["cohort_type"] == "purchase":
        d0_note = "- **D0 一定是 100%**：队列按首次购买定义，D0 的活跃和购买留存都应为 100%；不是就说明代码或数据有问题。"
        coverage_note = "- 首购队列只覆盖买过的人，不能代表全部新用户。"
    else:
        d0_note = "- **D0 活跃留存一定是 100%**：队列按首次活跃定义；D0 购买留存不一定，因为首次活跃当天未必购买。"
        coverage_note = "- 首次活跃队列覆盖所有产生过行为的用户，但仍不含只曝光未点击的人。"
    dau = result["dau"]
    peak_dates = dau.nlargest(2).index
    peak_text = "、".join(str(d.date()) for d in peak_dates)
    peak_values = "、".join(f"{int(dau[d]):,}" for d in peak_dates)

    cohort_type_text = "首次购买日期" if result["cohort_type"] == "purchase" else "首次活跃日期"
    cohort_intro = (
        "把用户按“第一次购买”的日期分成若干队列，观察他们在之后第 1、2……8 天是否还回来。"
        if result["cohort_type"] == "purchase"
        else "把用户按“第一次活跃”的日期分成若干队列，观察他们在之后第 1、2……8 天是否还回来。"
    )
    cohort_question = (
        "它回答的是：**新客买完一次之后，还会不会继续活跃 / 继续买？**"
        if result["cohort_type"] == "purchase"
        else "它回答的是：**新客第一次来之后，还会不会继续活跃 / 最终购买？**"
    )
    sample_note = (
        "> 入队用户数小于总用户数，是因为没有购买行为的用户不属于“首购队列”。"
        if result["cohort_type"] == "purchase"
        else "> 入队用户数等于总用户数，因为每个产生过行为的用户都有“首次活跃日期”。"
    )
    lines = [
        f"# {cohort_label} Cohort 留存分析",
        "",
        "## 1. 这份报告回答什么",
        "",
        cohort_intro,
        cohort_question,
        "",
        f"> **样本说明**：本报告使用 `{display_path(Path(result['input_path']))}`"
        f"（{result['users']:,} 个用户、人均 {result['avg_behaviors']:.2f} 条行为）。"
        "Cohort 需要同一个用户的多条行为，而对照样本是随机按行抽样"
        f"（人均 {compare_avg_behaviors:.2f} 条），无法做留存。两者的差异见第 10 节。"
        if compare is not None
        else "",
        "",
        "## 2. 口径",
        "",
        f"- 队列：按用户{cohort_type_text}分组。",
        "- 活跃留存：第 N 天有任意行为（浏览、收藏、加购、购买都算）。",
        "- 购买留存：第 N 天再次发生购买。",
        "- 第 N 天 = 行为日期 − 队列日期，D0 即队列当天。",
        f"- 观察窗口：{result['start_date'].date()} 至 {result['end_date'].date()}。",
        "- 尚未到观察期的格子记为“—”，**不能当成 0**；否则尾部会被误读成流失。",
        "",
        "## 3. 样本概览",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 用户数 | {result['users']:,} |",
        f"| 入队用户数 | {result['cohort_users']:,} |",
        f"| 队列数 | {len(sizes)} |",
        f"| 人均行为数 | {result['avg_behaviors']:.2f} 条 |",
        "",
        sample_note,
        "",
        "## 4. 队列规模",
        "",
        "| 队列 | 人数 | 可观察天数 |",
        "| --- | --- | --- |",
    ]
    for cohort, size in sizes.items():
        observable_days = int(result["observable"].loc[cohort].sum())
        lines.append(f"| {cohort.date()} | {int(size)} | {observable_days} |")

    lines += [
        "",
        "## 5. 活跃留存矩阵",
        "",
        "每一行是一个队列，每一列是队列首日后的第几天，格子里的数字是留存率。",
        "",
        rate_table(activity, sizes),
        "",
        f"![活跃留存热力图](figures/{activity_png.name})",
        "",
        "## 6. 购买留存矩阵",
        "",
        "只统计“又买了一次”的人，比活跃留存严格。",
        "",
        rate_table(purchase, sizes),
        "",
        f"![购买留存热力图](figures/{purchase_png.name})",
        "",
        "## 7. 加权留存汇总",
        "",
        "把每个队列按人数加权，并只统计“当天确实可观察”的队列。",
        "",
        summary_table(activity_summary, purchase_summary),
        "",
        "### 7.1 每日活跃用户（用来解释尾部反弹）",
        "",
        "| 日期 | DAU |",
        "| --- | --- |",
    ]
    lines += [f"| {date.date()} | {int(value):,} |" for date, value in dau.items()]
    lines += [
        "",
        f"> 本样本 DAU 最高的两天是 {peak_text}（{peak_values}），明显高于前后几天。"
        "所以任何队列在这两天都会显得“留存高”，这是大盘效应，不是用户变忠诚。",
        "",
        "## 8. 怎么读这张表",
        "",
        d0_note,
        retention_bullet(1, "活跃留存", activity_summary),
        retention_bullet(1, "购买留存", purchase_summary),
        retention_bullet(7, "活跃留存", activity_summary),
        retention_bullet(7, "购买留存", purchase_summary),
        "- 矩阵是**三角形**：越晚的队列能观察的天数越少，右边的“—”不是流失。",
        "- 购买留存比活跃留存更接近“真实复购意愿”，做留存运营时优先看它。",
        "",
        "## 9. 局限（必须写进报告）",
        "",
        "- 数据窗口只有 9 天，只能看短期回访，**不能外推月留存 / 长期留存**。",
        f"- 队列人数在 {min_cohort}~{max_cohort} 人之间，单格波动大；人数少于 30 的队列不应单独下结论。",
        "- 样本是“已经产生行为的用户”，不含曝光人群和新访客，留存率会偏高。",
        f"- 本样本人均 {result['avg_behaviors']:.2f} 条行为，用户几乎每天在线，活跃留存（如 D1 {day1_activity_text}）不能当作真实产品留存率。",
        coverage_note,
        "- 活跃留存受全站日活波动影响，购买留存更接近用户真实复购意愿。",
    ]

    if compare is not None:
        compare_sizes = compare["sizes"]
        compare_activity = weighted_retention(
            compare["activity_counts"], compare_sizes, compare["observable"]
        )
        compare_purchase = weighted_retention(
            compare["purchase_counts"], compare_sizes, compare["observable"]
        )
        lines += [
            "",
            "## 10. 对照：换一种抽样方式会怎样",
            "",
            f"用同一个脚本跑「{compare_label}」样本，结果如下：",
            "",
            comparison_table(
                activity_summary,
                purchase_summary,
                compare_activity,
                compare_purchase,
                primary_label,
                compare_label,
            ),
            "",
            f"- 对照样本人均行为数：{compare['avg_behaviors']:.2f} 条（{primary_label} {result['avg_behaviors']:.2f} 条）。",
            "- 对照样本按行随机抽样，同一个用户的行为被拆散，D1 之后几乎凑不出“再次活跃”。",
            "- 这说明 **Cohort 分析必须使用“用户完整”的样本**；否则留存率会接近 0，不是业务结论而是抽样假象。",
            "- 详细对比见 `reports/sampling_comparison.md`。",
        ]

    command_args = [
        f"  --input {display_path(Path(result['input_path']))}",
        f"  --cohort-type {result['cohort_type']}",
        "  --max-day 8",
    ]
    if compare is not None and compare.get("input_path"):
        command_args.append(
            f"  --compare-input {display_path(Path(compare['input_path']))}"
        )
        command_args.append(f'  --compare-label "{compare_label}"')
    command_block = "\n".join(
        ["python src/cohort_retention.py `"]
        + [line + " `" for line in command_args[:-1]]
        + [command_args[-1]]
    )

    lines += [
        "",
        "## 11. 复现",
        "",
        "```powershell",
        command_block,
        "```",
        "",
        "产物：",
        "",
        f"- `{display_path(output_path)}`（本报告）",
        f"- `{display_path(activity_png)}` / `{display_path(purchase_png)}`（两张热力图）",
        f"- `{display_path(activity_matrix_path)}` / "
        f"`{display_path(purchase_matrix_path)}`（矩阵 CSV，可直接丢进 Excel）",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 5. 命令行入口
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="按首购日期做 Cohort 留存分析。")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="清洗后的行为 CSV。")
    parser.add_argument(
        "--cohort-type",
        choices=["purchase", "active"],
        default="purchase",
        help="purchase=按首次购买建队列；active=按首次活跃建队列。",
    )
    parser.add_argument("--max-day", type=int, default=8, help="最多观察到第几天。")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_REPORT, help="Markdown 报告路径。")
    parser.add_argument("--figure-dir", type=Path, default=DEFAULT_FIG_DIR, help="图片输出目录。")
    parser.add_argument("--matrix-dir", type=Path, default=DEFAULT_MATRIX_DIR, help="矩阵 CSV 输出目录。")
    parser.add_argument("--prefix", default="cohort", help="图片和矩阵文件名前缀。")
    parser.add_argument(
        "--primary-label",
        default="首购样本（用户完整）",
        help="报告和对照表里主样本的名字。",
    )
    parser.add_argument("--compare-input", type=Path, default=None, help="可选：对照样本 CSV。")
    parser.add_argument("--compare-label", default="对照样本", help="对照样本在报告里的名字。")
    args = parser.parse_args()

    df = load_behavior(args.input)
    result = build_cohort(df, cohort_type=args.cohort_type, max_day=args.max_day)
    result["input_path"] = str(args.input)

    compare = None
    if args.compare_input is not None:
        compare_df = load_behavior(args.compare_input)
        compare = build_cohort(compare_df, cohort_type=args.cohort_type, max_day=args.max_day)
        compare["input_path"] = str(args.compare_input)

    write_report(
        result,
        output_path=args.output_md,
        figure_dir=args.figure_dir,
        matrix_dir=args.matrix_dir,
        figure_prefix=args.prefix,
        compare=compare,
        compare_label=args.compare_label,
        primary_label=args.primary_label,
    )

    print("Cohort summary")
    print(f"- Input: {args.input}")
    print(f"- Cohort type: {args.cohort_type}")
    print(f"- Users: {result['users']:,}")
    print(f"- Cohort users: {result['cohort_users']:,}")
    print(f"- Cohorts: {len(result['sizes'])}")
    print(f"- Report: {args.output_md}")
    print(f"- Figures: {args.figure_dir / (args.prefix + '_activity.png')}")
    if compare is not None:
        print(f"- Compare input: {args.compare_input}")


if __name__ == "__main__":
    main()
