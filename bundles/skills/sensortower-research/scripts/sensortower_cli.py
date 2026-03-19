#!/usr/bin/env python3
"""Sensor Tower research helper CLI.

The script wraps a verified subset of Sensor Tower endpoints and keeps a raw
escape hatch for anything not covered by a first-class subcommand.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib import error, parse, request


BASE_URL = "https://api.sensortower.com"
MIN_REQUEST_INTERVAL_SECONDS = 0.18

REVIEW_THEME_PATTERNS = {
    "crash_stability": [
        r"\bcrash(?:es|ed|ing)?\b",
        r"\bfreeze(?:s|d|ing)?\b",
        r"\bstuck\b",
        r"\bbug(?:s)?\b",
        r"\berror(?:s)?\b",
        r"\bglitch(?:es)?\b",
        r"\bblack screen\b",
        r"\bwhite screen\b",
        r"\b闪退\b",
        r"\b卡死\b",
        r"\b崩溃\b",
        r"\b报错\b",
        r"\b白屏\b",
        r"\b黑屏\b",
    ],
    "performance_speed": [
        r"\bslow\b",
        r"\blag(?:gy|ging)?\b",
        r"\bloading\b",
        r"\bdelay(?:ed)?\b",
        r"\bperformance\b",
        r"\bresponsive\b",
        r"\b卡\b",
        r"\b很慢\b",
        r"\b加载\b",
        r"\b延迟\b",
    ],
    "ads_monetization": [
        r"\bads?\b",
        r"\badvert(?:isement|ising|s)?\b",
        r"\btoo many ads\b",
        r"\bforced ads?\b",
        r"\b广告\b",
        r"\b弹窗\b",
    ],
    "pricing_subscription": [
        r"\bsubscription\b",
        r"\bsubscribe\b",
        r"\bprice(?:s|d)?\b",
        r"\bpaywall\b",
        r"\bexpensive\b",
        r"\brefund\b",
        r"\bbilling\b",
        r"\bcharged\b",
        r"\btrial\b",
        r"\b付费\b",
        r"\b订阅\b",
        r"\b价格\b",
        r"\b退款\b",
        r"\b收费\b",
    ],
    "login_account": [
        r"\blog(?:in|ged)?\b",
        r"\bsign[ -]?in\b",
        r"\baccount\b",
        r"\bpassword\b",
        r"\bverify\b",
        r"\bverification\b",
        r"\bfacebook login\b",
        r"\bgoogle login\b",
        r"\b登录\b",
        r"\b账号\b",
        r"\b密码\b",
        r"\b验证码\b",
    ],
    "updates_regressions": [
        r"\bupdate(?:d|s)?\b",
        r"\bnew version\b",
        r"\blatest version\b",
        r"\bafter the update\b",
        r"\b更新\b",
        r"\b新版\b",
        r"\b版本\b",
    ],
    "ux_navigation": [
        r"\bui\b",
        r"\bux\b",
        r"\bdesign\b",
        r"\binterface\b",
        r"\bnavigation\b",
        r"\bconfusing\b",
        r"\bhard to use\b",
        r"\b体验\b",
        r"\b界面\b",
        r"\b设计\b",
        r"\b难用\b",
    ],
    "notifications": [
        r"\bnotification(?:s)?\b",
        r"\breminder(?:s)?\b",
        r"\bpush\b",
        r"\b通知\b",
        r"\b提醒\b",
    ],
    "privacy_security": [
        r"\bprivacy\b",
        r"\bdata\b",
        r"\btracking\b",
        r"\bpermission(?:s)?\b",
        r"\bsecurity\b",
        r"\b隐私\b",
        r"\b权限\b",
        r"\b安全\b",
        r"\b追踪\b",
    ],
    "support_service": [
        r"\bsupport\b",
        r"\bcustomer service\b",
        r"\bhelp\b",
        r"\bresponse\b",
        r"\bcontact\b",
        r"\b客服\b",
        r"\b支持\b",
        r"\b联系\b",
        r"\b回复\b",
    ],
    "feature_request": [
        r"\bplease add\b",
        r"\bwould love\b",
        r"\bneed\b",
        r"\bwish\b",
        r"\bfeature\b",
        r"\b希望\b",
        r"\b建议\b",
        r"\b增加\b",
        r"\b新增\b",
        r"\b功能\b",
    ],
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "for",
    "from",
    "game",
    "get",
    "good",
    "great",
    "had",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "just",
    "like",
    "me",
    "my",
    "not",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "their",
    "this",
    "to",
    "too",
    "very",
    "was",
    "with",
    "you",
    "your",
}


def positive_theme_names() -> set[str]:
    return {"ux_navigation", "feature_request"}


class SensorTowerError(RuntimeError):
    """API or CLI usage error."""


@dataclass
class ResponseMeta:
    url: str
    status: int
    auth_mode: str
    token_index: int
    headers: dict[str, str]


class RateLimiter:
    def __init__(self, min_interval: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        self.min_interval = min_interval
        self._last_request_at = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_at = time.monotonic()


class SensorTowerClient:
    def __init__(
        self,
        token: str | None = None,
        backup_token: str | None = None,
        auth_mode: str = "auto",
        base_url: str = BASE_URL,
        timeout: float = 45.0,
    ) -> None:
        primary = token or os.getenv("SENSORTOWER_AUTH_TOKEN") or os.getenv("SENSOR_TOWER_API_TOKEN")
        if not primary:
            primary = os.getenv("SENSORTOWER_API_TOKEN")
        secondary = (
            backup_token
            or os.getenv("SENSORTOWER_AUTH_TOKEN_BACKUP")
            or os.getenv("SENSOR_TOWER_API_TOKEN_BACKUP")
        )
        if not secondary:
            secondary = os.getenv("SENSORTOWER_API_TOKEN_BACKUP")
        self.tokens = [value for value in [primary, secondary] if value]
        self.auth_mode = auth_mode
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limiter = RateLimiter()
        self.current_token_index = 0

    def has_token(self) -> bool:
        return bool(self.tokens)

    def require_token(self) -> None:
        if not self.tokens:
            raise SensorTowerError(
                "Missing Sensor Tower token. Set SENSORTOWER_AUTH_TOKEN or SENSOR_TOWER_API_TOKEN."
            )

    def _auth_modes(self) -> list[str]:
        if self.auth_mode == "auto":
            return ["query", "bearer"]
        return [self.auth_mode]

    def _quota_like(self, status: int, payload: Any) -> bool:
        if status == 429:
            return True
        if status != 403:
            return False
        body = json.dumps(payload, ensure_ascii=False).lower() if payload else ""
        return any(word in body for word in ("quota", "limit", "exceeded", "rate"))

    def _build_url(self, endpoint: str, params: list[tuple[str, str]]) -> str:
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        query = parse.urlencode(params, doseq=True)
        return f"{self.base_url}{path}?{query}" if query else f"{self.base_url}{path}"

    def _decode_json(self, raw_body: bytes) -> Any:
        if not raw_body:
            return None
        text = raw_body.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}

    def _attempt_request(
        self,
        endpoint: str,
        params: list[tuple[str, str]],
        token: str,
        auth_mode: str,
    ) -> tuple[Any, ResponseMeta]:
        request_params = list(params)
        headers = {
            "Accept": "application/json",
            "User-Agent": "codex-sensortower-skill/1.0",
        }
        if auth_mode == "query":
            request_params.append(("auth_token", token))
        elif auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {token}"
        else:
            raise SensorTowerError(f"Unsupported auth mode: {auth_mode}")

        url = self._build_url(endpoint, request_params)
        req = request.Request(url, headers=headers, method="GET")
        self.rate_limiter.wait()
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                payload = self._decode_json(body)
                meta = ResponseMeta(
                    url=url,
                    status=resp.getcode(),
                    auth_mode=auth_mode,
                    token_index=self.current_token_index,
                    headers=dict(resp.headers.items()),
                )
                return payload, meta
        except error.HTTPError as exc:
            payload = self._decode_json(exc.read())
            meta = ResponseMeta(
                url=url,
                status=exc.code,
                auth_mode=auth_mode,
                token_index=self.current_token_index,
                headers=dict(exc.headers.items()),
            )
            raise SensorTowerError(
                json.dumps(
                    {
                        "status": exc.code,
                        "url": url,
                        "auth_mode": auth_mode,
                        "body": payload,
                    },
                    ensure_ascii=False,
                )
            ) from exc
        except error.URLError as exc:
            raise SensorTowerError(f"Network error for {url}: {exc}") from exc

    def get(self, endpoint: str, params: list[tuple[str, str]]) -> tuple[Any, ResponseMeta]:
        self.require_token()
        last_error: str | None = None
        starting_index = self.current_token_index

        for token_index in range(starting_index, len(self.tokens)):
            self.current_token_index = token_index
            token = self.tokens[token_index]
            for auth_mode in self._auth_modes():
                try:
                    return self._attempt_request(endpoint, params, token, auth_mode)
                except SensorTowerError as exc:
                    last_error = str(exc)
                    try:
                        decoded = json.loads(last_error)
                    except json.JSONDecodeError:
                        continue
                    status = int(decoded.get("status", 0))
                    payload = decoded.get("body")
                    if status in (401, 403) and auth_mode != self._auth_modes()[-1]:
                        continue
                    if self._quota_like(status, payload) and token_index < len(self.tokens) - 1:
                        break
            else:
                continue
        raise SensorTowerError(last_error or "Sensor Tower request failed.")


def non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def csv_or_repeat(values: list[str] | None, key: str) -> list[tuple[str, str]]:
    if not values:
        return []
    cleaned = [value for value in (non_empty(item) for item in values) if value]
    if not cleaned:
        return []
    return [(key, ",".join(cleaned))]


def maybe_pair(key: str, value: str | int | bool | None) -> list[tuple[str, str]]:
    if value is None:
        return []
    if isinstance(value, bool):
        return [(key, "true" if value else "false")]
    return [(key, str(value))]


def flatten_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def flatten_record(record: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    for key, value in record.items():
        joined_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_record(value, joined_key))
        else:
            flattened[joined_key] = flatten_value(value)
    return flattened


def extract_records(payload: Any, preferred_keys: Iterable[str] | None = None) -> list[dict[str, Any]] | None:
    keys = list(preferred_keys or [])
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, list) and all(isinstance(item, dict) for item in candidate):
                return candidate
        for value in payload.values():
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
    return None


def emit_result(
    payload: Any,
    args: argparse.Namespace,
    meta: ResponseMeta | None = None,
    preferred_keys: Iterable[str] | None = None,
) -> None:
    if args.format == "csv":
        records = extract_records(payload, preferred_keys)
        if records is None:
            raise SensorTowerError("CSV output requires a list of object records.")
        write_csv(records, args.output)
        if not args.output:
            return
        print(str(Path(args.output).resolve()))
        return

    result: Any = payload
    if args.records_only:
        records = extract_records(payload, preferred_keys)
        if records is None:
            raise SensorTowerError("Could not extract records from payload. Remove --records-only.")
        result = records
    if args.include_meta and meta is not None:
        result = {
            "meta": {
                "url": meta.url,
                "status": meta.status,
                "auth_mode": meta.auth_mode,
                "token_index": meta.token_index,
                "x_api_usage_limit": meta.headers.get("x-api-usage-limit"),
                "x_api_usage_count": meta.headers.get("x-api-usage-count"),
            },
            "data": result,
        }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(text + "\n", encoding="utf-8")
        print(str(Path(args.output).expanduser().resolve()))
    else:
        print(text)


def write_csv(records: list[dict[str, Any]], output_path: str | None) -> None:
    flattened = [flatten_record(record) for record in records]
    fieldnames = sorted({key for row in flattened for key in row.keys()})
    if output_path:
        target = Path(output_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened)
        return

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(flattened)


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def get_first(record: dict[str, Any], candidates: Iterable[str]) -> Any:
    for key in candidates:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def review_text(record: dict[str, Any]) -> str:
    value = get_first(record, ("review", "review_text", "content", "body", "text"))
    return str(value or "").strip()


def review_rating(record: dict[str, Any]) -> int | None:
    value = get_first(record, ("rating", "score", "stars", "star_rating"))
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def review_sentiment(record: dict[str, Any]) -> str | None:
    value = get_first(record, ("sentiment", "review_sentiment"))
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def review_polarity(record: dict[str, Any]) -> str:
    sentiment = review_sentiment(record)
    if sentiment in {"happy", "positive", "satisfied"}:
        return "positive"
    if sentiment in {"unhappy", "negative", "dissatisfied"}:
        return "negative"
    if sentiment in {"mixed", "neutral"}:
        return "neutral"

    rating = review_rating(record)
    if rating is None:
        return "neutral"
    if rating >= 4:
        return "positive"
    if rating <= 2:
        return "negative"
    return "neutral"


def analyze_review_themes(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        text = review_text(record).lower()
        if not text:
            continue
        for theme, patterns in REVIEW_THEME_PATTERNS.items():
            if any(re.search(pattern, text) for pattern in patterns):
                grouped[theme].append(record)
    return grouped


def extract_top_terms(records: list[dict[str, Any]], max_terms: int = 20) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for record in records:
        text = review_text(record).lower()
        tokens = re.findall(r"[a-z][a-z0-9_'-]{2,}", text)
        for token in tokens:
            if token in STOPWORDS:
                continue
            counter[token] += 1
    return [{"term": term, "count": count} for term, count in counter.most_common(max_terms)]


def compact_review_sample(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": normalize_date(get_first(record, ("date", "review_date", "created_at"))),
        "rating": review_rating(record),
        "version": get_first(record, ("version", "app_version", "appVersion")),
        "title": get_first(record, ("title", "review_title")),
        "user": get_first(record, ("username", "user_name", "author_name")),
        "text": review_text(record)[:280],
    }


def build_review_insights(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "summary": {
                "total_reviews": 0,
                "message": "No reviews found for the supplied filters.",
            }
        }

    ratings = [rating for rating in (review_rating(record) for record in records) if rating is not None]
    dates = [normalize_date(get_first(record, ("date", "review_date", "created_at"))) for record in records]
    versions = [str(value) for value in (get_first(record, ("version", "app_version", "appVersion")) for record in records) if value]

    positive = [record for record in records if review_polarity(record) == "positive"]
    negative = [record for record in records if review_polarity(record) == "negative"]
    neutral = [record for record in records if review_polarity(record) == "neutral"]

    theme_groups = analyze_review_themes(records)
    negative_themes = []
    positive_themes = []
    for theme, theme_records in sorted(theme_groups.items(), key=lambda item: len(item[1]), reverse=True):
        entry = {
            "theme": theme,
            "count": len(theme_records),
            "sample_reviews": [compact_review_sample(record) for record in theme_records[:3]],
        }
        if theme in positive_theme_names():
            positive_themes.append(entry)
        else:
            negative_themes.append(entry)

    negative_versions = Counter(
        str(get_first(record, ("version", "app_version", "appVersion")))
        for record in negative
        if get_first(record, ("version", "app_version", "appVersion"))
    )

    return {
        "summary": {
            "total_reviews": len(records),
            "ratings_with_values": len(ratings),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "positive_reviews": len(positive),
            "negative_reviews": len(negative),
            "neutral_reviews": len(neutral),
            "first_review_date": min(value for value in dates if value) if any(dates) else None,
            "last_review_date": max(value for value in dates if value) if any(dates) else None,
        },
        "rating_distribution": {str(key): value for key, value in sorted(Counter(ratings).items())},
        "top_versions": [{"version": version, "count": count} for version, count in Counter(versions).most_common(10)],
        "negative_version_hotspots": [
            {"version": version, "negative_review_count": count}
            for version, count in negative_versions.most_common(10)
        ],
        "negative_themes": negative_themes[:10],
        "positive_themes": positive_themes[:10],
        "top_terms_negative": extract_top_terms(negative),
        "top_terms_positive": extract_top_terms(positive),
        "review_samples": {
            "negative": [compact_review_sample(record) for record in negative[:5]],
            "positive": [compact_review_sample(record) for record in positive[:5]],
        },
    }


def render_review_insights_markdown(insights: dict[str, Any]) -> str:
    summary = insights.get("summary", {})
    lines = [
        "# Review Insights",
        "",
        f"- Total reviews: {summary.get('total_reviews')}",
        f"- Average rating: {summary.get('average_rating')}",
        f"- Positive reviews: {summary.get('positive_reviews')}",
        f"- Negative reviews: {summary.get('negative_reviews')}",
        f"- Neutral reviews: {summary.get('neutral_reviews')}",
        f"- Date range: {summary.get('first_review_date')} -> {summary.get('last_review_date')}",
        "",
        "## Negative Themes",
    ]
    for item in insights.get("negative_themes", [])[:8]:
        lines.append(f"- {item['theme']}: {item['count']}")
    lines.extend(["", "## Positive Themes"])
    for item in insights.get("positive_themes", [])[:8]:
        lines.append(f"- {item['theme']}: {item['count']}")
    lines.extend(["", "## Top Negative Terms"])
    for item in insights.get("top_terms_negative", [])[:15]:
        lines.append(f"- {item['term']}: {item['count']}")
    lines.extend(["", "## Top Positive Terms"])
    for item in insights.get("top_terms_positive", [])[:15]:
        lines.append(f"- {item['term']}: {item['count']}")
    return "\n".join(lines) + "\n"


def load_input_records(path: str) -> list[dict[str, Any]]:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise SensorTowerError(f"Input file not found: {source}")
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    payload = json.loads(source.read_text(encoding="utf-8"))
    records = extract_records(payload, ("reviews", "data", "results", "records"))
    if records is None:
        raise SensorTowerError("Could not extract review records from JSON input.")
    return records


def parse_key_value_pairs(items: list[str] | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in items or []:
        if "=" not in item:
            raise SensorTowerError(f"Expected key=value, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise SensorTowerError(f"Empty key in parameter: {item}")
        pairs.append((key, value))
    return pairs


def fetch_reviews(
    client: SensorTowerClient,
    os_name: str,
    app_id: str,
    country: str,
    start_date: str | None,
    end_date: str | None,
    rating_filter: str | None,
    search_term: str | None,
    username: str | None,
    limit: int,
    page: int,
    all_pages: bool,
    max_pages: int,
) -> tuple[Any, ResponseMeta]:
    endpoint = f"/v1/{os_name}/review/get_reviews"
    base_params = [
        ("app_id", app_id),
        ("country", country),
        ("limit", str(limit)),
        ("page", str(page)),
    ]
    base_params += maybe_pair("start_date", start_date)
    base_params += maybe_pair("end_date", end_date)
    base_params += maybe_pair("rating_filter", rating_filter)
    base_params += maybe_pair("search_term", search_term)
    base_params += maybe_pair("username", username)

    payload, meta = client.get(endpoint, base_params)
    if not all_pages:
        return payload, meta

    records = extract_records(payload, ("reviews", "data", "results")) or []
    fetched_pages = 1
    current_page = page
    while records and fetched_pages < max_pages:
        current_page += 1
        next_params = [(key, value) for key, value in base_params if key != "page"] + [("page", str(current_page))]
        next_payload, meta = client.get(endpoint, next_params)
        next_records = extract_records(next_payload, ("reviews", "data", "results")) or []
        if not next_records:
            break
        records.extend(next_records)
        fetched_pages += 1
    return {
        "records": records,
        "pages_fetched": fetched_pages,
        "page_start": page,
        "limit": limit,
    }, meta


def fetch_paginated_records(
    client: SensorTowerClient,
    endpoint: str,
    params: list[tuple[str, str]],
    preferred_keys: tuple[str, ...],
    page: int,
    max_pages: int,
) -> tuple[Any, ResponseMeta]:
    payload, meta = client.get(endpoint, params + [("page", str(page))])
    records = extract_records(payload, preferred_keys) or []
    fetched_pages = 1
    current_page = page
    while records and fetched_pages < max_pages:
        current_page += 1
        next_payload, meta = client.get(endpoint, params + [("page", str(current_page))])
        next_records = extract_records(next_payload, preferred_keys) or []
        if not next_records:
            break
        records.extend(next_records)
        fetched_pages += 1
    return {"records": records, "pages_fetched": fetched_pages, "page_start": page}, meta


def add_common_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--output")
    parser.add_argument("--records-only", action="store_true")
    parser.add_argument("--include-meta", action="store_true")


def add_client_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--token")
    parser.add_argument("--backup-token")
    parser.add_argument("--auth-mode", choices=("auto", "query", "bearer"), default="auto")


def build_client(args: argparse.Namespace) -> SensorTowerClient:
    return SensorTowerClient(
        token=args.token,
        backup_token=args.backup_token,
        auth_mode=args.auth_mode,
    )


def handle_search(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [
        ("entity_type", args.entity_type),
        ("term", args.term),
        ("limit", str(args.limit)),
    ]
    payload, meta = client.get(f"/v1/{args.store}/search_entities", params)
    emit_result(payload, args, meta, preferred_keys=("data",))


def handle_metadata(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = csv_or_repeat(args.app_id, "app_ids")
    params += maybe_pair("country", args.country)
    params += maybe_pair("include_sdk_data", args.include_sdk_data)
    payload, meta = client.get(f"/v1/{args.os}/apps", params)
    emit_result(payload, args, meta, preferred_keys=("apps",))


def handle_sales(args: argparse.Namespace) -> None:
    client = build_client(args)
    if not args.app_id and not args.publisher_id:
        raise SensorTowerError("sales requires at least one --app-id or --publisher-id.")
    params = csv_or_repeat(args.app_id, "app_ids")
    params += csv_or_repeat(args.publisher_id, "publisher_ids")
    params += csv_or_repeat(args.country, "countries")
    params += [
        ("date_granularity", args.date_granularity),
        ("start_date", args.start_date),
        ("end_date", args.end_date),
    ]
    params += maybe_pair("data_model", args.data_model)
    payload, meta = client.get(f"/v1/{args.os}/sales_report_estimates", params)
    emit_result(payload, args, meta)


def handle_rankings(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [
        ("category", args.category),
        ("chart_type", args.chart_type),
        ("country", args.country),
        ("date", args.date),
    ]
    payload, meta = client.get(f"/v1/{args.os}/ranking", params)
    emit_result(payload, args, meta)


def handle_top_apps(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [
        ("comparison_attribute", args.comparison_attribute),
        ("time_range", args.time_range),
        ("measure", args.measure),
        ("category", args.category),
        ("date", args.date),
    ]
    params += csv_or_repeat(args.region, "regions")
    params += maybe_pair("end_date", args.end_date)
    params += maybe_pair("limit", args.limit)
    params += maybe_pair("offset", args.offset)
    params += maybe_pair("device_type", args.device_type)
    params += maybe_pair("custom_fields_filter_id", args.custom_fields_filter_id)
    params += maybe_pair("custom_tags_mode", args.custom_tags_mode)
    params += maybe_pair("data_model", args.data_model)
    payload, meta = client.get(f"/v1/{args.os}/sales_report_estimates_comparison_attributes", params)
    emit_result(payload, args, meta)


def handle_keywords(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [
        ("app_id", args.app_id),
        ("country", args.country),
    ]
    payload, meta = client.get(f"/v1/{args.os}/keywords/get_current_keywords", params)
    emit_result(payload, args, meta)


def handle_keyword_research(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [
        ("term", args.term),
        ("country", args.country),
    ]
    params += maybe_pair("app_id", args.app_id)
    params += maybe_pair("page", args.page)
    payload, meta = client.get(f"/v1/{args.os}/keywords/research_keyword", params)
    emit_result(payload, args, meta)


def handle_reviews(args: argparse.Namespace) -> None:
    client = build_client(args)
    payload, meta = fetch_reviews(
        client=client,
        os_name=args.os,
        app_id=args.app_id,
        country=args.country,
        start_date=args.start_date,
        end_date=args.end_date,
        rating_filter=args.rating_filter,
        search_term=args.search_term,
        username=args.username,
        limit=args.limit,
        page=args.page,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
    )
    emit_result(payload, args, meta, preferred_keys=("records", "reviews", "data", "results"))


def handle_review_summary(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [
        ("app_id", args.app_id),
    ]
    params += maybe_pair("country", args.country)
    params += maybe_pair("start_date", args.start_date)
    params += maybe_pair("end_date", args.end_date)
    params += maybe_pair("rating_filter", args.rating_filter)
    payload, meta = client.get(f"/v1/{args.os}/review/app_history_summary", params)
    emit_result(payload, args, meta)


def handle_ratings(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = [("app_id", args.app_id)]
    params += maybe_pair("country", args.country)
    params += maybe_pair("start_date", args.start_date)
    params += maybe_pair("end_date", args.end_date)
    payload, meta = client.get(f"/v1/{args.os}/review/get_ratings", params)
    emit_result(payload, args, meta)


def handle_creatives(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = csv_or_repeat(args.app_id, "app_ids")
    params += [
        ("start_date", args.start_date),
    ]
    params += maybe_pair("end_date", args.end_date)
    params += csv_or_repeat(args.country, "countries")
    params += csv_or_repeat(args.network, "networks")
    params += csv_or_repeat(args.ad_type, "ad_types")
    params += maybe_pair("limit", args.limit)
    params += maybe_pair("display_breakdown", args.display_breakdown)
    params += csv_or_repeat(args.placement, "placements")
    endpoint = f"/v1/{args.os}/ad_intel/creatives"
    if args.all_pages:
        payload, meta = fetch_paginated_records(
            client,
            endpoint,
            params,
            preferred_keys=("ad_units", "creatives", "records", "data"),
            page=args.page,
            max_pages=args.max_pages,
        )
    else:
        payload, meta = client.get(endpoint, params + maybe_pair("page", args.page))
    emit_result(payload, args, meta, preferred_keys=("records", "ad_units", "creatives", "data"))


def handle_review_insights(args: argparse.Namespace) -> None:
    if args.input:
        records = load_input_records(args.input)
    else:
        client = build_client(args)
        payload, _ = fetch_reviews(
            client=client,
            os_name=args.os,
            app_id=args.app_id,
            country=args.country,
            start_date=args.start_date,
            end_date=args.end_date,
            rating_filter=args.rating_filter,
            search_term=args.search_term,
            username=args.username,
            limit=args.limit,
            page=args.page,
            all_pages=True,
            max_pages=args.max_pages,
        )
        records = extract_records(payload, ("records", "reviews", "data", "results")) or []
    insights = build_review_insights(records)
    if args.report:
        target = Path(args.report).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".md":
            target.write_text(render_review_insights_markdown(insights), encoding="utf-8")
        else:
            target.write_text(json.dumps(insights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(target))
        return
    print(json.dumps(insights, ensure_ascii=False, indent=2))


def handle_raw(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = parse_key_value_pairs(args.param)
    payload, meta = client.get(args.endpoint, params)
    emit_result(payload, args, meta)


def handle_docs(args: argparse.Namespace) -> None:
    client = build_client(args)
    urls = [
        ("docs_page", "https://app.sensortower.com/api/docs"),
        ("swagger_json", "https://api.sensortower.com/swagger.json"),
        ("openapi_json", "https://api.sensortower.com/openapi.json"),
        ("api_docs", "https://api.sensortower.com/api-docs"),
    ]
    token = client.tokens[0] if client.tokens else None
    results = []
    for name, url in urls:
        final_url = url
        if token and "api.sensortower.com" in url:
            separator = "&" if "?" in url else "?"
            final_url = f"{url}{separator}auth_token={parse.quote(token)}"
        req = request.Request(
            final_url,
            headers={"User-Agent": "codex-sensortower-skill/1.0", "Accept": "application/json,text/html"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                snippet = body.decode("utf-8", errors="replace")[:200]
                results.append(
                    {
                        "name": name,
                        "url": final_url,
                        "status": resp.getcode(),
                        "content_type": resp.headers.get("content-type"),
                        "snippet": snippet,
                    }
                )
                if args.save_dir:
                    target = Path(args.save_dir).expanduser().resolve()
                    target.mkdir(parents=True, exist_ok=True)
                    suffix = ".json" if "json" in (resp.headers.get("content-type") or "") else ".html"
                    (target / f"{name}{suffix}").write_bytes(body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            results.append(
                {
                    "name": name,
                    "url": final_url,
                    "status": exc.code,
                    "content_type": exc.headers.get("content-type"),
                    "snippet": body,
                }
            )
    print(json.dumps(results, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sensor Tower research helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search apps or publishers")
    add_client_args(search)
    add_common_output_args(search)
    search.add_argument("--store", choices=("unified", "ios", "android"), default="unified")
    search.add_argument("--entity-type", choices=("app", "publisher"), default="app")
    search.add_argument("--term", required=True)
    search.add_argument("--limit", type=int, default=20)
    search.set_defaults(func=handle_search)

    metadata = subparsers.add_parser("metadata", help="Fetch app metadata")
    add_client_args(metadata)
    add_common_output_args(metadata)
    metadata.add_argument("--os", choices=("ios", "android"), required=True)
    metadata.add_argument("--app-id", action="append", required=True, help="Repeat for multiple app IDs")
    metadata.add_argument("--country", default="US")
    metadata.add_argument("--include-sdk-data", action="store_true")
    metadata.set_defaults(func=handle_metadata)

    sales = subparsers.add_parser("sales", help="Fetch downloads and revenue estimates")
    add_client_args(sales)
    add_common_output_args(sales)
    sales.add_argument("--os", choices=("ios", "android", "unified"), required=True)
    sales.add_argument("--app-id", action="append")
    sales.add_argument("--publisher-id", action="append")
    sales.add_argument("--country", action="append", required=True, help="Repeat for multiple countries; use WW for worldwide")
    sales.add_argument("--date-granularity", choices=("daily", "weekly", "monthly", "quarterly"), default="daily")
    sales.add_argument("--start-date", required=True)
    sales.add_argument("--end-date", required=True)
    sales.add_argument("--data-model", choices=("DM_2025_Q1", "DM_2025_Q2"))
    sales.set_defaults(func=handle_sales)

    rankings = subparsers.add_parser("rankings", help="Fetch category rankings")
    add_client_args(rankings)
    add_common_output_args(rankings)
    rankings.add_argument("--os", choices=("ios", "android"), required=True)
    rankings.add_argument("--category", required=True)
    rankings.add_argument("--chart-type", required=True)
    rankings.add_argument("--country", default="US")
    rankings.add_argument("--date", required=True)
    rankings.set_defaults(func=handle_rankings)

    top_apps = subparsers.add_parser("top-apps", help="Fetch top apps by downloads or revenue")
    add_client_args(top_apps)
    add_common_output_args(top_apps)
    top_apps.add_argument("--os", choices=("ios", "android", "unified"), required=True)
    top_apps.add_argument("--comparison-attribute", choices=("absolute", "delta", "transformed_delta"), default="absolute")
    top_apps.add_argument("--time-range", choices=("day", "week", "month", "quarter", "year"), default="week")
    top_apps.add_argument("--measure", choices=("units", "revenue"), default="units")
    top_apps.add_argument("--device-type", choices=("iphone", "ipad", "total"))
    top_apps.add_argument("--category", required=True)
    top_apps.add_argument("--date", required=True)
    top_apps.add_argument("--end-date")
    top_apps.add_argument("--region", action="append", required=True)
    top_apps.add_argument("--limit", type=int)
    top_apps.add_argument("--offset", type=int)
    top_apps.add_argument("--custom-fields-filter-id")
    top_apps.add_argument("--custom-tags-mode", choices=("include_unified_apps", "exclude_unified_apps"))
    top_apps.add_argument("--data-model", choices=("DM_2025_Q1", "DM_2025_Q2"))
    top_apps.set_defaults(func=handle_top_apps)

    keywords = subparsers.add_parser("keywords", help="Fetch keyword list for an app")
    add_client_args(keywords)
    add_common_output_args(keywords)
    keywords.add_argument("--os", choices=("ios", "android"), required=True)
    keywords.add_argument("--app-id", required=True)
    keywords.add_argument("--country", default="US")
    keywords.set_defaults(func=handle_keywords)

    keyword_research = subparsers.add_parser("keyword-research", help="Research a keyword")
    add_client_args(keyword_research)
    add_common_output_args(keyword_research)
    keyword_research.add_argument("--os", choices=("ios", "android"), required=True)
    keyword_research.add_argument("--term", required=True)
    keyword_research.add_argument("--country", default="US")
    keyword_research.add_argument("--app-id")
    keyword_research.add_argument("--page", type=int)
    keyword_research.set_defaults(func=handle_keyword_research)

    reviews = subparsers.add_parser("reviews", help="Fetch user reviews")
    add_client_args(reviews)
    add_common_output_args(reviews)
    reviews.add_argument("--os", choices=("ios", "android"), required=True)
    reviews.add_argument("--app-id", required=True)
    reviews.add_argument("--country", default="US")
    reviews.add_argument("--start-date")
    reviews.add_argument("--end-date")
    reviews.add_argument("--rating-filter")
    reviews.add_argument("--search-term")
    reviews.add_argument("--username")
    reviews.add_argument("--limit", type=int, default=200)
    reviews.add_argument("--page", type=int, default=1)
    reviews.add_argument("--all-pages", action="store_true")
    reviews.add_argument("--max-pages", type=int, default=20)
    reviews.set_defaults(func=handle_reviews)

    review_summary = subparsers.add_parser("review-summary", help="Fetch review history summary")
    add_client_args(review_summary)
    add_common_output_args(review_summary)
    review_summary.add_argument("--os", choices=("ios", "android"), required=True)
    review_summary.add_argument("--app-id", required=True)
    review_summary.add_argument("--country")
    review_summary.add_argument("--start-date")
    review_summary.add_argument("--end-date")
    review_summary.add_argument("--rating-filter")
    review_summary.set_defaults(func=handle_review_summary)

    ratings = subparsers.add_parser("ratings", help="Fetch rating history")
    add_client_args(ratings)
    add_common_output_args(ratings)
    ratings.add_argument("--os", choices=("ios", "android"), required=True)
    ratings.add_argument("--app-id", required=True)
    ratings.add_argument("--country")
    ratings.add_argument("--start-date")
    ratings.add_argument("--end-date")
    ratings.set_defaults(func=handle_ratings)

    creatives = subparsers.add_parser("creatives", help="Fetch advertising creatives")
    add_client_args(creatives)
    add_common_output_args(creatives)
    creatives.add_argument("--os", choices=("ios", "android", "unified"), required=True)
    creatives.add_argument("--app-id", action="append", required=True)
    creatives.add_argument("--start-date", required=True)
    creatives.add_argument("--end-date")
    creatives.add_argument("--country", action="append", required=True)
    creatives.add_argument("--network", action="append", required=True)
    creatives.add_argument("--ad-type", action="append", required=True)
    creatives.add_argument("--placement", action="append")
    creatives.add_argument("--limit", type=int, default=50)
    creatives.add_argument("--page", type=int, default=1)
    creatives.add_argument("--max-pages", type=int, default=10)
    creatives.add_argument("--all-pages", action="store_true")
    creatives.add_argument("--display-breakdown", action=argparse.BooleanOptionalAction, default=True)
    creatives.set_defaults(func=handle_creatives)

    review_insights = subparsers.add_parser("review-insights", help="Fetch reviews and build heuristic insights")
    add_client_args(review_insights)
    review_insights.add_argument("--input", help="Existing JSON or CSV review export")
    review_insights.add_argument("--os", choices=("ios", "android"))
    review_insights.add_argument("--app-id")
    review_insights.add_argument("--country", default="US")
    review_insights.add_argument("--start-date")
    review_insights.add_argument("--end-date")
    review_insights.add_argument("--rating-filter")
    review_insights.add_argument("--search-term")
    review_insights.add_argument("--username")
    review_insights.add_argument("--limit", type=int, default=200)
    review_insights.add_argument("--page", type=int, default=1)
    review_insights.add_argument("--max-pages", type=int, default=20)
    review_insights.add_argument("--report", help="Write .json or .md report")
    review_insights.set_defaults(func=handle_review_insights)

    raw = subparsers.add_parser("raw", help="Call any endpoint with explicit params")
    add_client_args(raw)
    add_common_output_args(raw)
    raw.add_argument("--endpoint", required=True, help="Example: /v1/unified/ad_intel/top_apps")
    raw.add_argument("--param", action="append", help="Repeat key=value pairs")
    raw.set_defaults(func=handle_raw)

    docs = subparsers.add_parser("docs", help="Check or save gated documentation endpoints")
    add_client_args(docs)
    docs.add_argument("--save-dir")
    docs.set_defaults(func=handle_docs)

    return parser


def validate_review_insights_args(args: argparse.Namespace) -> None:
    if args.command != "review-insights":
        return
    if args.input:
        return
    if not args.os or not args.app_id:
        raise SensorTowerError("review-insights requires --input or both --os and --app-id.")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_review_insights_args(args)
        args.func(args)
        return 0
    except SensorTowerError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
