# 数据说明

本项目提交的 CSV 文件来自公开淘宝 UserBehavior 数据集，样本规模控制在适合 GitHub 展示和本地复现的范围内。

## 当前文件

- `raw_user_behavior_sample.csv`：主分析样本，从下载后的 `archive.zip` / `UserBehavior.csv` 中按“顺序抽样”抽取的 100,000 行真实行为记录。
- `cleaned_user_behavior.csv`：主分析清洗后保留的 99,956 行 / 983 用户。清洗过程包括重复值、缺失值、行为类型、时间戳和分析窗口过滤；Unix 时间戳会先转换为 `Asia/Shanghai` 业务时间，再生成日期和小时字段。
- `raw_user_behavior_random_sample.csv`：对照样本，按行随机抽取的 100,000 行（固定种子 42）。
- `cleaned_user_behavior_random_sample.csv`：对照样本清洗后的 99,939 行 / 91,923 用户。

> 主分析（README、`analysis_summary.md`、`cohort_retention.md`）统一使用顺序抽样样本；随机样本只用于 `reports/sampling_comparison.md` 和 Cohort 报告第 10 节的偏差对照。

## 重新构建真实样本

方式 A：从阿里天池下载 `UserBehavior.csv`：
   <https://tianchi.aliyun.com/dataset/649?lang=en-us>

方式 B：从 Kaggle 镜像下载：
   <https://www.kaggle.com/datasets/marwa80/userbehavior/data>

将下载后的文件放在：

```text
data/UserBehavior.csv
```

如果保留压缩文件，则放在：

```text
data/UserBehavior.csv.zip
```

抽取适合 GitHub 展示的主分析样本（顺序抽样，保留同一用户的完整行为路径）：

```bash
python src/prepare_real_data_sample.py --input data/UserBehavior.csv --output data/raw_user_behavior_sample.csv --rows 100000
```

如果希望额外生成一份固定随机种子的对照样本，**写到单独文件，避免覆盖主样本**：

```bash
python src/prepare_real_data_sample.py --input data/UserBehavior.csv --output data/raw_user_behavior_random_sample.csv --rows 100000 --sample-mode random --random-state 42
python src/data_cleaning.py --input data/raw_user_behavior_random_sample.csv --output data/cleaned_user_behavior_random_sample.csv
```

如果下载的是 zip 文件：

```bash
python src/prepare_real_data_sample.py --input data/UserBehavior.csv.zip --output data/raw_user_behavior_sample.csv --rows 100000
```

重新生成清洗后数据：

```bash
python src/data_cleaning.py --input data/raw_user_behavior_sample.csv --output data/cleaned_user_behavior.csv
```

运行分析：

```bash
python src/analysis.py --input data/cleaned_user_behavior.csv
python src/cohort_retention.py
```

完整 `UserBehavior.csv` 文件体积较大，已通过 `.gitignore` 排除，不建议提交到 GitHub。
