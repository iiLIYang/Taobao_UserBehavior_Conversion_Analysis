from pathlib import Path
import json

import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT / "reports" / "dashboard_data.json"
DEFAULT_OUTPUT_PATH = ROOT / "dashboard" / "auto_dashboard.xlsx"


def export_dashboard(data_path=DEFAULT_DATA_PATH, output_path=DEFAULT_OUTPUT_PATH):
    data_path = Path(data_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    DATA = json.loads(data_path.read_text(encoding="utf-8"))
    wb = xlsxwriter.Workbook(output_path)

    had_error = False
    try:
        FONT = "Microsoft YaHei"
        fmt_title = wb.add_format({
            "bold": True, "font_size": 18, "font_name": FONT, "font_color": "#1F2937"
        })
        fmt_subtitle = wb.add_format({
            "font_size": 10, "font_name": FONT, "font_color": "#6B7280"
        })
        fmt_header = wb.add_format({
            "bold": True, "font_name": FONT, "font_color": "#FFFFFF",
            "bg_color": "#2F80ED", "border": 1,
            "align": "center", "valign": "vcenter",
        })
        fmt_text = wb.add_format({
            "font_name": FONT, "border": 1, "valign": "vcenter"
        })
        fmt_number = wb.add_format({
            "font_name": FONT, "border": 1, "num_format": "#,##0", "align": "right"
        })
        fmt_percent = wb.add_format({
            "font_name": FONT, "border": 1, "num_format": "0.0%", "align": "right"
        })
        fmt_decimal = wb.add_format({
            "font_name": FONT, "border": 1, "num_format": "0.00", "align": "right"
        })
        fmt_section = wb.add_format({
            "bold": True, "font_name": FONT, "font_size": 12, "font_color": "#2F80ED"
        })
        fmt_info = wb.add_format({
            "font_name": FONT, "font_size": 10, "font_color": "#374151", "valign": "top"
        })
        fmt_kpi_label = wb.add_format({
            "font_name": FONT, "font_size": 10, "font_color": "#6B7280",
            "bg_color": "#F3F4F6", "border": 1,
            "align": "center", "valign": "vcenter",
        })
        fmt_kpi_number = wb.add_format({
            "font_name": FONT, "font_size": 16, "bold": True, "font_color": "#111827",
            "bg_color": "#FFFFFF", "border": 1,
            "align": "center", "valign": "vcenter", "num_format": "#,##0",
        })
        fmt_kpi_percent = wb.add_format({
            "font_name": FONT, "font_size": 16, "bold": True, "font_color": "#111827",
            "bg_color": "#FFFFFF", "border": 1,
            "align": "center", "valign": "vcenter", "num_format": "0.00%",
        })



        # 00_看板

        ws_dashboard = wb.add_worksheet("00_看板")
        ws_dashboard.activate()
        ws_dashboard.hide_gridlines(2)
        ws_dashboard.set_column("A:J", 14)
        ws_dashboard.set_zoom(80)
        ws_dashboard.write("A1", "淘宝用户行为分析 · 经营总览", fmt_title)
        ws_dashboard.write("A2", f"样本：{DATA['meta']['clean_rows']:,} 条行为 / Asia/Shanghai", fmt_subtitle)
        kpi_percent_indexes = {3,4,5,6}

        for i, item in enumerate(DATA["kpis"]):
            row = 4 + (i//4) * 3
            col = (i%4) * 2
            ws_dashboard.merge_range(row, col, row, col + 1, item["metric"], fmt_kpi_label)
            value_fmt = fmt_kpi_percent if i in kpi_percent_indexes else fmt_kpi_number
            ws_dashboard.merge_range(row + 1, col, row + 1, col + 1, item["value"], value_fmt)
        ws_dashboard.merge_range("A12:H12",
            "口径提示：用户级转化率不等于平台真实访客转化率；顺序转化为用户-商品级严格口径。",
            fmt_subtitle)

        # 01_说明

        ws_info = wb.add_worksheet("01_说明")
        ws_info.hide_gridlines(2)
        ws_info.set_column("A:A", 16)
        ws_info.set_column("B:B", 100)
        ws_info.write("A1", "淘宝用户行为分析 · 数据说明", fmt_title)

        info_rows = [
            ("数据来源", "阿里天池 Taobao UserBehavior 公开数据集（UserBehavior.csv）"),
            ("样本规模", f"顺序抽样 {DATA['meta']['raw_rows']:,} 行；清洗后 {DATA['meta']['clean_rows']:,} 行 / {DATA['kpis'][1]['value']:,} 用户"),
            ("时间窗口", f"{DATA['meta']['date_min'][:10]} 至 {DATA['meta']['date_max'][:10]}（Asia/Shanghai）"),
            ("核心口径", "用户级转化 vs 用户-商品级顺序转化；Cohort 区分活跃留存与购买留存"),
            ("已知局限", "样本仅覆盖重度用户，不含曝光人群；无金额字段；9 天窗口，不能外推长期留存"),
            ("生成方式", "python src/generate_reports.py → python src/export_dashboard.py"),
            ("相关报告", "reports/analysis_summary.md、sampling_comparison.md、cohort_retention.md"),
        ]
        for row, (label, value) in enumerate(info_rows, start=3):
            ws_info.write(row - 1, 0, label, fmt_section)
            ws_info.write(row - 1, 1, value, fmt_info)

        # 通用表格函数

        def write_table(ws, headers, rows, percent_cols=(), decimal_cols=(), start_row=0):
            for c, header in enumerate(headers):
                ws.write_string(start_row, c, header, fmt_header)

            for r, row in enumerate(rows, start=start_row + 1):
                for c, value in enumerate(row):
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        if c in percent_cols:
                            fmt = fmt_percent
                        elif c in decimal_cols:
                            fmt = fmt_decimal
                        else:
                            fmt = fmt_number
                        ws.write_number(r, c, value, fmt)
                    else:
                        ws.write_string(r, c, str(value), fmt_text)

            ws.freeze_panes(start_row + 1, 0)

        # 02_行为分布

        ws_behavior = wb.add_worksheet("02_行为分布")
        ws_behavior.hide_gridlines(2)
        rows = [
            [item["behavior_type"], item["behavior_count"], item["behavior_share"]]
            for item in DATA["behavior_distribution"]
        ]
        write_table(
            ws_behavior,
            headers=["行为类型", "行为次数", "行为占比"],
            rows=rows,
            percent_cols=(2,),
        )
        ws_behavior.set_column("A:A", 14)
        ws_behavior.set_column("B:C", 16)

        # 03_每日趋势

        ws_trend = wb.add_worksheet("03_每日趋势")
        ws_trend.hide_gridlines(2)
        rows_trend= [
            [item["date"], item["dau"], item["purchase_count"], item["purchase_users"]]
            for item in DATA["daily_trends"]
        ]
        write_table(
            ws_trend,
            headers=["日期", "日活跃用户数(DAU)", "购买次数", "购买用户数"],
            rows=rows_trend,
        )
        ws_trend.set_column("A:A", 14)
        ws_trend.set_column("B:D", 16)

        # 04_品类Top10

        ws_top10 = wb.add_worksheet("04_品类Top10")
        ws_top10.hide_gridlines(2)
        rows_top10= [
            [int(item["category_id"]), item["purchase_count"], item["buyer_count"]]
            for item in DATA["top_categories"]
        ]
        write_table(
            ws_top10,
            headers=["品类ID", "购买次数", "购买用户数"],
            rows=rows_top10,
        )
        ws_top10.set_column("A:A", 14)
        ws_top10.set_column("B:C", 16)

        # 05_用户分层

        ws_seg = wb.add_worksheet("05_用户分层")
        ws_seg.hide_gridlines(2)
        rows_seg= [
            [
                item["behavior_depth"],
                item["purchase_segment"],
                item["users"],
                item["avg_active_days"],
                item["total_purchases"],
                item["avg_purchase_count"],
                item["avg_cart_count"]
            ]
            for item in DATA["user_segmentation"]
        ]
        write_table(
            ws_seg,
            headers=["行为深度", "购买分层", "用户数", "平均活跃天数", "总购买次数", "平均购买次数", "平均加购次数"],
            rows=rows_seg,
            decimal_cols=(3, 5, 6),
        )
        ws_seg.write_string(0, 7, "分层标签", fmt_header)
        for r, item in enumerate(DATA["user_segmentation"], start=1):
            ws_seg.write_string(
                r, 7, # 7 代表第 7 列（索引从0开始，0是A，7就是H）
                f"{item['behavior_depth']} / {item['purchase_segment']}",
                fmt_text
            )
        ws_seg.set_column("A:B", 14)
        ws_seg.set_column("C:G", 16)
        ws_seg.set_column("H:H", 30)

        #  06_小时行为

        ws_hour = wb.add_worksheet("06_小时行为")
        ws_hour.hide_gridlines(2)
        rows_hour = [
            [int(item["hour"]), int(item["pv"]), int(item["fav"]), int(item["cart"]), int(item["buy"])]
            for item in DATA["hourly_activity"]
        ]
        write_table(
            ws_hour,
            headers=["小时", "浏览量(pv)", "收藏量(fav)", "加购量(cart)", "购买量(buy)"],
            rows=rows_hour
        )
        ws_hour.conditional_format(
            1, 1, 24, 4,
            {
                "type": "3_color_scale",
                "min_color": "#FFFFFF",
                "mid_color": "#9BE9A8",
                "max_color": "#2166AC",
            },
        )
        ws_hour.set_column("A:A", 10)
        ws_hour.set_column("B:E", 14)

        # 图表统一插到 00_看板，数据留在各自的数据表

        chart_behavior = wb.add_chart({"type": "column"})
        chart_behavior.add_series({
            "name": "行为次数",
            "categories": ["02_行为分布", 1, 0, 4, 0],
            "values":     ["02_行为分布", 1, 1, 4, 1],
            "data_labels": {"value": True},
        })
        chart_behavior.set_title({"name": "行为类型分布"})
        chart_behavior.set_x_axis({"name": "行为类型"})
        chart_behavior.set_y_axis({"name": "行为次数"})
        chart_behavior.set_legend({"none": True})
        chart_behavior.set_size({"width": 480, "height": 300})
        chart_behavior.set_style(10)
        ws_dashboard.insert_chart("A14", chart_behavior, {"x_offset": 10, "y_offset": 10})

        chart_trend = wb.add_chart({"type": "line"})
        chart_trend.add_series({
            "name": "DAU",
            "categories": ["03_每日趋势", 1, 0, 9, 0],
            "values":     ["03_每日趋势", 1, 1, 9, 1],
            "marker": {"type": "circle", "size": 5},
        })
        chart_trend.add_series({
            "name": "购买次数",
            "categories": ["03_每日趋势", 1, 0, 9, 0],
            "values":     ["03_每日趋势", 1, 2, 9, 2],
            "y2_axis": True,
            "marker": {"type": "square", "size": 5},
        })
        chart_trend.set_title({"name": "每日活跃用户与购买趋势"})
        chart_trend.set_x_axis({"name": "日期"})
        chart_trend.set_y_axis({"name": "DAU"})
        chart_trend.set_y2_axis({"name": "购买次数"})
        chart_trend.set_size({"width": 560, "height": 300})
        chart_trend.set_style(10)
        ws_dashboard.insert_chart("F14", chart_trend, {"x_offset": 10, "y_offset": 10})

        chart_top10 = wb.add_chart({"type": "bar"})
        chart_top10.add_series({
            "name": "购买次数",
            "categories": ["04_品类Top10", 1, 0, 10, 0],
            "values":     ["04_品类Top10", 1, 1, 10, 1],
            "data_labels": {"value": True},
        })
        chart_top10.set_title({"name": "购买次数 Top 10 品类"})
        chart_top10.set_x_axis({"name": "购买次数"})
        chart_top10.set_y_axis({"name": "品类 ID", "reverse": True})
        chart_top10.set_legend({"none": True})
        chart_top10.set_size({"width": 480, "height": 400})
        chart_top10.set_style(10)
        ws_dashboard.insert_chart("A32", chart_top10, {"x_offset": 10, "y_offset": 10})

        chart_seg = wb.add_chart({"type": "column"})
        chart_seg.add_series({
            "name": "用户数",
            "categories": ["05_用户分层", 1, 7, 6, 7],
            "values":     ["05_用户分层", 1, 2, 6, 2],
            "data_labels": {"value": True},
        })
        chart_seg.set_title({"name": "用户分层人数"})
        chart_seg.set_x_axis({"name": "分层", "label_rotation": -30})
        chart_seg.set_y_axis({"name": "用户数"})
        chart_seg.set_legend({"none": True})
        chart_seg.set_size({"width": 560, "height": 320})
        chart_seg.set_style(10)
        ws_dashboard.insert_chart("F32", chart_seg, {"x_offset": 10, "y_offset": 10})

        # 数据表保留但隐藏；右键标签 → Unhide 可查看
        for ws in [ws_behavior, ws_trend, ws_top10, ws_seg, ws_hour]:
            ws.set_tab_color("#9CA3AF")
            ws.hide()

        ws_info.set_zoom(90)
        ws_info.freeze_panes(1, 0)
        ws_info.set_tab_color("#6B7280")
        ws_dashboard.set_tab_color("#2F80ED")
    except Exception:
        had_error = True
        raise
    finally:
        try:
            wb.close()
        except xlsxwriter.exceptions.FileCreateError as exc:
            if not had_error:
                raise RuntimeError(
                    f"无法写入 {output_path}：请先关闭 Excel/WPS 中打开的同名文件，再重新运行。"
                ) from exc
    print(f"written: {output_path}")
    return output_path

if __name__ == "__main__":
    export_dashboard()