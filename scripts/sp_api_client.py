#!/usr/bin/env python3
"""Minimal LWA-only Amazon SP-API helper using the Python standard library.

This helper intentionally does not implement legacy AWS SigV4 signing. It exchanges
LWA tokens, calls regional SP-API JSON endpoints, and creates narrowly scoped RDTs.
It never accepts a full request URL, preventing accidental token forwarding to an
untrusted host.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
PRODUCTION_ENDPOINTS = {
    "NA": "https://sellingpartnerapi-na.amazon.com",
    "EU": "https://sellingpartnerapi-eu.amazon.com",
    "FE": "https://sellingpartnerapi-fe.amazon.com",
}
SANDBOX_ENDPOINTS = {
    "NA": "https://sandbox.sellingpartnerapi-na.amazon.com",
    "EU": "https://sandbox.sellingpartnerapi-eu.amazon.com",
    "FE": "https://sandbox.sellingpartnerapi-fe.amazon.com",
}
RETRYABLE_STATUSES = {429, 500, 503}
DEFAULT_TIMEOUT = 30.0


@dataclass
class SpApiHttpError(RuntimeError):
    status: int
    message: str
    request_id: str | None = None
    retry_after: float | None = None

    def __str__(self) -> str:
        request_id = f" request_id={self.request_id}" if self.request_id else ""
        return f"SP-API HTTP {self.status}:{request_id} {self.message}"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def redact(text: str) -> str:
    for name in (
        "SP_API_LWA_CLIENT_SECRET",
        "SP_API_REFRESH_TOKEN",
        "SP_API_ACCESS_TOKEN",
    ):
        value = os.getenv(name)
        if value:
            text = text.replace(value, "<redacted>")
    return text


def decode_json(raw: bytes, context: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{context} returned a non-JSON response") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} returned JSON that is not an object")
    return value


def http_error(error: HTTPError) -> SpApiHttpError:
    raw = error.read(8192)
    message = raw.decode("utf-8", errors="replace").strip() or error.reason
    request_id = error.headers.get("x-amzn-RequestId")
    return SpApiHttpError(
        status=error.code,
        message=redact(message),
        request_id=request_id,
        retry_after=parse_retry_after(error.headers.get("Retry-After")),
    )


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def token_request(form: dict[str, str], timeout: float) -> dict[str, Any]:
    request = Request(
        LWA_TOKEN_URL,
        data=urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = decode_json(response.read(), "LWA token endpoint")
    except HTTPError as error:
        raise http_error(error) from error
    except URLError as error:
        raise RuntimeError(f"LWA token request failed: {redact(str(error.reason))}") from error

    if not result.get("access_token"):
        raise RuntimeError("LWA response did not contain access_token")
    return result


def seller_access_token(timeout: float) -> dict[str, Any]:
    return token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": required_env("SP_API_REFRESH_TOKEN"),
            "client_id": required_env("SP_API_LWA_CLIENT_ID"),
            "client_secret": required_env("SP_API_LWA_CLIENT_SECRET"),
        },
        timeout,
    )


def grantless_access_token(scope: str, timeout: float) -> dict[str, Any]:
    return token_request(
        {
            "grant_type": "client_credentials",
            "scope": scope,
            "client_id": required_env("SP_API_LWA_CLIENT_ID"),
            "client_secret": required_env("SP_API_LWA_CLIENT_SECRET"),
        },
        timeout,
    )


def authorization_code_token(code: str, redirect_uri: str, timeout: float) -> dict[str, Any]:
    return token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": required_env("SP_API_LWA_CLIENT_ID"),
            "client_secret": required_env("SP_API_LWA_CLIENT_SECRET"),
        },
        timeout,
    )


def endpoint(region: str, sandbox: bool) -> str:
    endpoints = SANDBOX_ENDPOINTS if sandbox else PRODUCTION_ENDPOINTS
    return endpoints[region]


def validate_path(path: str) -> str:
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("--path must be an absolute SP-API path beginning with one slash")
    if "://" in path or "\r" in path or "\n" in path:
        raise ValueError("--path must not contain a URL, CR, or LF")
    return path


def parse_query(values: Iterable[str]) -> list[tuple[str, str]]:
    query: list[tuple[str, str]] = []
    for value in values:
        key, separator, item = value.partition("=")
        if not separator or not key:
            raise ValueError(f"Invalid --query value {value!r}; expected KEY=VALUE")
        query.append((key, item))
    return query


def parse_aware_datetime(value: str, option: str) -> datetime:
    """Parse an ISO 8601 instant without silently assuming a local time zone."""
    candidate = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError(f"{option} must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{option} must include Z or an explicit UTC offset")
    return parsed


def finances_query(args: argparse.Namespace) -> list[tuple[str, str]]:
    if bool(args.related_identifier_name) != bool(args.related_identifier_value):
        raise ValueError(
            "--related-identifier-name and --related-identifier-value must be supplied together"
        )
    if not args.posted_after and not args.related_identifier_name:
        raise ValueError(
            "--posted-after is required unless a related identifier pair is supplied"
        )

    query: list[tuple[str, str]] = []
    after = None
    before = None
    if args.posted_after:
        after = parse_aware_datetime(args.posted_after, "--posted-after")
        query.append(("postedAfter", args.posted_after))
    if args.posted_before:
        before = parse_aware_datetime(args.posted_before, "--posted-before")
        query.append(("postedBefore", args.posted_before))
    if after and before:
        if before <= after:
            raise ValueError("--posted-before must be later than --posted-after")
        if before - after > timedelta(days=180):
            raise ValueError("the posted time window must not exceed 180 days")

    for key, value in (
        ("marketplaceId", args.marketplace_id),
        ("transactionStatus", args.transaction_status),
        ("relatedIdentifierName", args.related_identifier_name),
        ("relatedIdentifierValue", args.related_identifier_value),
        ("nextToken", args.next_token),
    ):
        if value:
            query.append((key, value))
    return query


def request_json(
    *,
    method: str,
    region: str,
    path: str,
    access_token: str,
    query: list[tuple[str, str]] | None = None,
    body: dict[str, Any] | None = None,
    sandbox: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    max_attempts: int = 4,
) -> tuple[dict[str, Any], dict[str, str | None]]:
    path = validate_path(path)
    query_string = urlencode(query or [], doseq=True)
    url = endpoint(region, sandbox) + path
    if query_string:
        url += "?" + query_string

    payload = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
    user_agent = os.getenv(
        "SP_API_USER_AGENT",
        f"AmazonSPAPISkill/1.0 (Language=Python/{sys.version_info.major}.{sys.version_info.minor})",
    )

    for attempt in range(max_attempts):
        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
            "x-amz-access-token": access_token,
            "x-amz-date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
                result = {} if not raw else decode_json(raw, "SP-API")
                metadata = {
                    "request_id": response.headers.get("x-amzn-RequestId"),
                    "rate_limit": response.headers.get("x-amzn-RateLimit-Limit"),
                }
                return result, metadata
        except HTTPError as original:
            error = http_error(original)
            if error.status not in RETRYABLE_STATUSES or attempt + 1 >= max_attempts:
                raise error from original
            base = error.retry_after
            if base is None:
                base = min(30.0, 0.5 * (2**attempt))
            time.sleep(base + random.uniform(0.0, max(0.1, base * 0.2)))
        except URLError as error:
            if attempt + 1 >= max_attempts:
                raise RuntimeError(f"SP-API request failed: {redact(str(error.reason))}") from error
            base = min(30.0, 0.5 * (2**attempt))
            time.sleep(base + random.uniform(0.0, max(0.1, base * 0.2)))

    raise RuntimeError("SP-API request failed without a terminal result")


def print_token_result(result: dict[str, Any], show_token: bool) -> None:
    output = {
        "access_token": result["access_token"] if show_token else "<redacted>",
        "token_type": result.get("token_type"),
        "expires_in": result.get("expires_in"),
    }
    if "refresh_token" in result:
        output["refresh_token"] = result["refresh_token"] if show_token else "<redacted>"
    print(json.dumps(output, ensure_ascii=False, indent=2))


def command_token(args: argparse.Namespace) -> None:
    print_token_result(seller_access_token(args.timeout), args.show_token)


def command_grantless_token(args: argparse.Namespace) -> None:
    print_token_result(grantless_access_token(args.scope, args.timeout), args.show_token)


def command_authorization_code(args: argparse.Namespace) -> None:
    result = authorization_code_token(
        required_env(args.code_env),
        args.redirect_uri,
        args.timeout,
    )
    print_token_result(result, args.show_token)


def resolve_access_token(args: argparse.Namespace) -> str:
    if args.access_token_env:
        return required_env(args.access_token_env)
    return str(seller_access_token(args.timeout)["access_token"])


def command_get(args: argparse.Namespace) -> None:
    result, metadata = request_json(
        method="GET",
        region=args.region,
        path=args.path,
        query=parse_query(args.query),
        access_token=resolve_access_token(args),
        sandbox=args.sandbox,
        timeout=args.timeout,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.show_metadata:
        print(json.dumps(metadata, ensure_ascii=False), file=sys.stderr)


def command_finances(args: argparse.Namespace) -> None:
    result, metadata = request_json(
        method="GET",
        region=args.region,
        path="/finances/2024-06-19/transactions",
        query=finances_query(args),
        access_token=resolve_access_token(args),
        sandbox=args.sandbox,
        timeout=args.timeout,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.show_metadata:
        print(json.dumps(metadata, ensure_ascii=False), file=sys.stderr)


def command_rdt(args: argparse.Namespace) -> None:
    restricted_resource: dict[str, Any] = {
        "method": args.resource_method,
        "path": validate_path(args.resource_path),
    }
    if args.data_element:
        restricted_resource["dataElements"] = args.data_element

    result, metadata = request_json(
        method="POST",
        region=args.region,
        path="/tokens/2021-03-01/restrictedDataToken",
        access_token=str(seller_access_token(args.timeout)["access_token"]),
        body={"restrictedResources": [restricted_resource]},
        sandbox=args.sandbox,
        timeout=args.timeout,
        max_attempts=args.max_attempts,
    )
    token = result.get("restrictedDataToken")
    if not token:
        raise RuntimeError("Tokens API response did not contain restrictedDataToken")
    output = {
        "restrictedDataToken": token if args.show_token else "<redacted>",
        "expiresIn": result.get("expiresIn"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if args.show_metadata:
        print(json.dumps(metadata, ensure_ascii=False), file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exchange Amazon LWA tokens and call current SP-API JSON endpoints."
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    token = subparsers.add_parser("token", help="Exchange a seller refresh token for an LWA access token")
    token.add_argument("--show-token", action="store_true", help="Print the secret token; avoid in logs")
    token.set_defaults(handler=command_token)

    authorization_code = subparsers.add_parser(
        "authorization-code",
        help="Exchange a public-app OAuth authorization code for LWA tokens",
    )
    authorization_code.add_argument(
        "--code-env",
        default="SP_API_AUTHORIZATION_CODE",
        help="Environment variable containing the short-lived authorization code",
    )
    authorization_code.add_argument("--redirect-uri", required=True)
    authorization_code.add_argument(
        "--show-token",
        action="store_true",
        help="Print access and refresh tokens; capture securely and avoid logs",
    )
    authorization_code.set_defaults(handler=command_authorization_code)

    grantless = subparsers.add_parser("grantless-token", help="Get a scoped grantless LWA token")
    grantless.add_argument(
        "--scope",
        required=True,
        choices=(
            "sellingpartnerapi::notifications",
            "sellingpartnerapi::client_credential:rotation",
        ),
    )
    grantless.add_argument("--show-token", action="store_true", help="Print the secret token; avoid in logs")
    grantless.set_defaults(handler=command_grantless_token)

    get = subparsers.add_parser("get", help="Call a direct SP-API GET operation and print JSON")
    get.add_argument("--region", required=True, choices=tuple(PRODUCTION_ENDPOINTS))
    get.add_argument("--path", required=True, help="SP-API path only, never a full URL")
    get.add_argument("--query", action="append", default=[], metavar="KEY=VALUE")
    get.add_argument("--sandbox", action="store_true")
    get.add_argument(
        "--access-token-env",
        help="Read an existing LWA access token or RDT from this environment variable",
    )
    get.add_argument("--max-attempts", type=int, default=4)
    get.add_argument("--show-metadata", action="store_true")
    get.set_defaults(handler=command_get)

    finances = subparsers.add_parser(
        "finances",
        help="Call Finances v2024-06-19 listTransactions and print one response page",
    )
    finances.add_argument("--region", required=True, choices=tuple(PRODUCTION_ENDPOINTS))
    finances.add_argument(
        "--posted-after",
        help="Inclusive ISO 8601 lower bound with Z or an explicit UTC offset",
    )
    finances.add_argument(
        "--posted-before",
        help="Exclusive ISO 8601 upper bound with Z or an explicit UTC offset",
    )
    finances.add_argument("--marketplace-id")
    finances.add_argument(
        "--transaction-status",
        choices=("DEFERRED", "RELEASED", "DEFERRED_RELEASED"),
    )
    finances.add_argument(
        "--related-identifier-name",
        choices=("FINANCIAL_EVENT_GROUP_ID", "ORDER_ID"),
    )
    finances.add_argument("--related-identifier-value")
    finances.add_argument(
        "--next-token",
        help="Opaque token from the preceding page; keep all other filters unchanged",
    )
    finances.add_argument("--sandbox", action="store_true")
    finances.add_argument(
        "--access-token-env",
        help="Read an existing LWA access token from this environment variable",
    )
    finances.add_argument("--max-attempts", type=int, default=4)
    finances.add_argument("--show-metadata", action="store_true")
    finances.set_defaults(handler=command_finances)

    rdt = subparsers.add_parser("rdt", help="Create a narrowly scoped Restricted Data Token")
    rdt.add_argument("--region", required=True, choices=tuple(PRODUCTION_ENDPOINTS))
    rdt.add_argument("--resource-method", required=True, choices=("GET", "POST", "PUT", "PATCH", "DELETE"))
    rdt.add_argument("--resource-path", required=True)
    rdt.add_argument("--data-element", action="append", default=[])
    rdt.add_argument("--sandbox", action="store_true")
    rdt.add_argument("--max-attempts", type=int, default=4)
    rdt.add_argument("--show-token", action="store_true", help="Print the RDT; avoid in logs")
    rdt.add_argument("--show-metadata", action="store_true")
    rdt.set_defaults(handler=command_rdt)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "max_attempts", 1) < 1:
        parser.error("--max-attempts must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        args.handler(args)
    except (ValueError, RuntimeError, SpApiHttpError) as error:
        print(f"error: {redact(str(error))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
