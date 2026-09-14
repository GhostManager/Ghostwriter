"""
Validate every GraphQL document embedded in ``app.py`` against a live Hasura schema.

The middleware talks to Hasura through hardcoded query strings, so a change to the
Ghostwriter data model (or to ``hasura-docker/metadata``) can silently invalidate
them - nothing fails until a request 502s in production. The unit tests in
``test_app.py`` monkeypatch ``graphql_request`` and therefore never see the query
text, so this check exists to cover that gap.

Usage:

    pip install graphql-core requests
    python validate_graphql.py \
        --url http://localhost:8080/v1/graphql \
        --admin-secret "$HASURA_GRAPHQL_ADMIN_SECRET"

Exits non-zero and prints every offending document if any query fails to parse or
references fields, arguments or types the schema does not have.
"""
import argparse
import ast
import sys

import requests
from graphql import build_client_schema, get_introspection_query, parse, validate
from graphql.error import GraphQLError


# Anything that starts with one of these is treated as a GraphQL document. Plain
# strings that merely mention "query" are ignored.
GRAPHQL_PREFIXES = ("query ", "mutation ", "subscription ", "fragment ", "{")


def extract_documents(path):
    """Return (lineno, source) for every string literal in `path` that looks like GraphQL."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)

    documents = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        stripped = node.value.strip()
        if stripped.startswith(GRAPHQL_PREFIXES):
            documents.append((node.lineno, node.value))
    return documents


def fetch_schema(url, admin_secret, timeout):
    headers = {"Content-Type": "application/json"}
    if admin_secret:
        headers["x-hasura-admin-secret"] = admin_secret

    response = requests.post(
        url,
        json={"query": get_introspection_query()},
        headers=headers,
        timeout=timeout,
        verify=False,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise RuntimeError(f"introspection failed: {payload['errors']}")
    return build_client_schema(payload["data"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Hasura GraphQL endpoint")
    parser.add_argument("--admin-secret", default=None, help="x-hasura-admin-secret header")
    parser.add_argument("--app", default="app.py", help="middleware source file to scan")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    documents = extract_documents(args.app)
    if not documents:
        print(f"No GraphQL documents found in {args.app} - the extractor is probably broken.")
        return 1

    schema = fetch_schema(args.url, args.admin_secret, args.timeout)

    failures = 0
    for lineno, source in documents:
        location = f"{args.app}:{lineno}"
        try:
            document = parse(source)
        except GraphQLError as exc:
            failures += 1
            print(f"::error file={args.app},line={lineno}::syntax error: {exc.message}")
            continue

        errors = validate(schema, document)
        if errors:
            failures += 1
            for error in errors:
                print(f"::error file={args.app},line={lineno}::{error.message}")
        else:
            print(f"ok  {location}")

    print(f"\n{len(documents) - failures}/{len(documents)} GraphQL documents valid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
