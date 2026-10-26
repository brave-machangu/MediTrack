"""Checks the JSON schemas in api/openapi.yaml can't express on their own.

The response schemas don't say `additionalProperties: false`, so plain schema validation
accepts a response with an extra field. The contract is the interface for the frontend's
generated types, so an undocumented field is a contract break too (backend Excellence prompt).
"""

from __future__ import annotations

from typing import Any

import schemathesis

# Parsed YAML and JSON: their shape is what these functions inspect, so they stay untyped.
Node = Any


def resolve(contract: dict[str, Node], node: Node) -> Node:
    """Follows local `$ref`s ("#/components/...") until it reaches a real definition."""
    while isinstance(node, dict) and "$ref" in node:
        target: Node = contract
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def response_schema(
    contract: dict[str, Node], path: str, method: str, status: int, media_type: str
) -> Node | None:
    """The documented schema for this response, or None if the response has no body."""
    responses = contract["paths"][path][method.lower()]["responses"]
    documented = responses.get(str(status)) or responses.get(f"{str(status)[0]}XX")
    if documented is None:
        return None
    content = resolve(contract, documented).get("content", {})
    entry = content.get(media_type.split(";")[0].strip())
    return None if entry is None else entry.get("schema")


def undocumented_fields(
    contract: dict[str, Node], schema: Node, value: Node, at: str = "body"
) -> list[str]:
    """Paths of object keys in `value` that the schema doesn't list as properties."""
    schema = resolve(contract, schema)
    if isinstance(value, dict) and isinstance(schema, dict) and "properties" in schema:
        found = [f"{at}.{key}" for key in value if key not in schema["properties"]]
        for key, item in value.items():
            if key in schema["properties"]:
                found += undocumented_fields(
                    contract, schema["properties"][key], item, f"{at}.{key}"
                )
        return found
    if isinstance(value, list) and isinstance(schema, dict) and "items" in schema:
        return [
            field
            for index, item in enumerate(value)
            for field in undocumented_fields(contract, schema["items"], item, f"{at}[{index}]")
        ]
    return []


@schemathesis.check
def no_undocumented_fields(
    ctx: schemathesis.CheckContext, response: schemathesis.Response, case: schemathesis.Case
) -> bool | None:
    """Schemathesis check: fails when a response carries a field the contract doesn't name."""
    if not response.content:
        return None
    contract: dict[str, Node] = case.operation.schema.raw_schema
    schema = response_schema(
        contract,
        case.operation.path,
        case.operation.method,
        response.status_code,
        {name.lower(): values for name, values in response.headers.items()}.get(
            "content-type", ["application/json"]
        )[0],
    )
    if schema is None:
        return None
    extra = undocumented_fields(contract, schema, response.json())
    if extra:
        raise AssertionError(f"Undocumented fields in the response: {', '.join(extra)}")
    return None
