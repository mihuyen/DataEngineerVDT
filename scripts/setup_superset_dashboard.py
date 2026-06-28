from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.setup_superset_day22 import SupersetClient, load_config


DASHBOARD_TITLE = "Stock Lakehouse Gold Overview"


def find_dataset_id(client: SupersetClient, database_id: int, schema: str, table_name: str) -> int:
    dataset_id = client.find_dataset_id(database_id, schema, table_name)
    if dataset_id is None:
        raise RuntimeError(f"Dataset {schema}.{table_name} not found; run setup_superset_day22.py first.")
    return dataset_id


def find_chart_id(client: SupersetClient, slice_name: str) -> int | None:
    response = client.session.get(
        f"{client.base_url}/api/v1/chart/",
        params={"q": json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": slice_name}]})},
        timeout=client.timeout,
    )
    response.raise_for_status()
    results = response.json().get("result", [])
    return int(results[0]["id"]) if results else None


def ensure_chart(
    client: SupersetClient,
    slice_name: str,
    dataset_id: int,
    viz_type: str,
    params: dict[str, Any],
    dashboard_id: int | None = None,
) -> int:
    existing_id = find_chart_id(client, slice_name)
    payload = {
        "slice_name": slice_name,
        "viz_type": viz_type,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps(params),
        **({"dashboards": [dashboard_id]} if dashboard_id is not None else {}),
    }
    if existing_id is not None:
        response = client.session.put(
            f"{client.base_url}/api/v1/chart/{existing_id}",
            json=payload,
            timeout=client.timeout,
        )
        response.raise_for_status()
        return existing_id

    response = client.session.post(
        f"{client.base_url}/api/v1/chart/",
        json=payload,
        timeout=client.timeout,
    )
    response.raise_for_status()
    return int(response.json()["id"])


def find_dashboard_id(client: SupersetClient, title: str) -> int | None:
    response = client.session.get(
        f"{client.base_url}/api/v1/dashboard/",
        params={"q": json.dumps({"filters": [{"col": "dashboard_title", "opr": "eq", "value": title}]})},
        timeout=client.timeout,
    )
    response.raise_for_status()
    results = response.json().get("result", [])
    return int(results[0]["id"]) if results else None


def ensure_dashboard_shell(client: SupersetClient, title: str) -> int:
    existing_id = find_dashboard_id(client, title)
    if existing_id is not None:
        return existing_id

    response = client.session.post(
        f"{client.base_url}/api/v1/dashboard/",
        json={"dashboard_title": title, "published": True},
        timeout=client.timeout,
    )
    response.raise_for_status()
    return int(response.json()["id"])


def set_dashboard_layout(client: SupersetClient, dashboard_id: int, chart_ids: list[int]) -> None:
    chart_width = max(1, 12 // len(chart_ids)) if chart_ids else 12
    row_id = "ROW-1"
    chart_node_ids = [f"CHART-{chart_id}" for chart_id in chart_ids]

    position_json: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [row_id],
            "parents": ["ROOT_ID"],
        },
        row_id: {
            "type": "ROW",
            "id": row_id,
            "children": chart_node_ids,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
        },
    }
    for chart_id, node_id in zip(chart_ids, chart_node_ids):
        position_json[node_id] = {
            "type": "CHART",
            "id": node_id,
            "children": [],
            "meta": {"chartId": chart_id, "width": chart_width, "height": 50},
            "parents": ["ROOT_ID", "GRID_ID", row_id],
        }

    response = client.session.put(
        f"{client.base_url}/api/v1/dashboard/{dashboard_id}",
        json={"position_json": json.dumps(position_json)},
        timeout=client.timeout,
    )
    response.raise_for_status()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create real Superset charts + dashboard on top of the Gold datasets.")
    parser.add_argument("--url", default=os.getenv("SUPERSET_URL", "http://localhost:8088"))
    parser.add_argument("--username", default=os.getenv("SUPERSET_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("SUPERSET_PASSWORD", "admin"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SUPERSET_TIMEOUT", "30")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()

    client = SupersetClient(base_url=args.url, username=args.username, password=args.password, timeout=args.timeout)
    client.login()
    database_id = client.ensure_database(config.database_name, config.sqlalchemy_uri)
    for dataset in config.datasets:
        client.ensure_dataset(database_id, config.schema, dataset)

    fact_market_index_id = find_dataset_id(client, database_id, config.schema, "fact_market_index")
    fact_daily_price_id = find_dataset_id(client, database_id, config.schema, "fact_daily_price")
    fact_news_sentiment_id = find_dataset_id(client, database_id, config.schema, "fact_news_sentiment_daily")

    dashboard_id = ensure_dashboard_shell(client, DASHBOARD_TITLE)

    chart_ids = []

    chart_ids.append(
        ensure_chart(
            client,
            "VN-Index theo ngay",
            fact_market_index_id,
            "echarts_timeseries_line",
            {
                "datasource": f"{fact_market_index_id}__table",
                "viz_type": "echarts_timeseries_line",
                "x_axis": "trading_date",
                "time_grain_sqla": "P1D",
                "metrics": [
                    {
                        "expressionType": "SIMPLE",
                        "column": {"column_name": "close_point"},
                        "aggregate": "AVG",
                        "label": "VN-Index",
                    }
                ],
                "adhoc_filters": [
                    {
                        "clause": "WHERE",
                        "subject": "index_id",
                        "operator": "==",
                        "comparator": "VNINDEX",
                        "expressionType": "SIMPLE",
                    }
                ],
                "row_limit": 200,
                "x_axis_sort_asc": True,
            },
            dashboard_id,
        )
    )

    chart_ids.append(
        ensure_chart(
            client,
            "Top 10 ma theo thanh khoan (gan nhat)",
            fact_daily_price_id,
            "table",
            {
                "datasource": f"{fact_daily_price_id}__table",
                "viz_type": "table",
                "query_mode": "aggregate",
                "groupby": ["ticker"],
                "metrics": [
                    {"expressionType": "SIMPLE", "column": {"column_name": "value"}, "aggregate": "MAX", "label": "GTGD"}
                ],
                "row_limit": 10,
                "order_by_cols": ['["MAX(value)", false]'],
            },
            dashboard_id,
        )
    )

    chart_ids.append(
        ensure_chart(
            client,
            "News sentiment trung binh theo ngay",
            fact_news_sentiment_id,
            "echarts_timeseries_line",
            {
                "datasource": f"{fact_news_sentiment_id}__table",
                "viz_type": "echarts_timeseries_line",
                "x_axis": "news_date",
                "time_grain_sqla": "P1D",
                "metrics": [
                    {
                        "expressionType": "SIMPLE",
                        "column": {"column_name": "avg_sentiment_score"},
                        "aggregate": "AVG",
                        "label": "Avg Sentiment",
                    }
                ],
                "row_limit": 200,
                "x_axis_sort_asc": True,
            },
            dashboard_id,
        )
    )

    print(f"- charts created/updated: {chart_ids}")

    set_dashboard_layout(client, dashboard_id, chart_ids)
    print(f"- dashboard_id: {dashboard_id}")
    print(f"- dashboard_url: {args.url}/superset/dashboard/{dashboard_id}/")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            detail = exc.response.text  # type: ignore[union-attr]
        print(f"Superset API request failed: {exc}\n{detail}", file=sys.stderr)
        raise SystemExit(1) from exc
