"""Validate the custom mod's configuration contract.

The mod is code-second by design: before any Java exists, its data contract is
written down as JSON Schemas (``mod/schema/``) plus the files that instantiate
them, the shipped datapack (``mod/datapack/``), the default server config
(``mod/config/``) and a fixture set (``mod/examples/``) that exercises every
schema branch.

This module validates all of it with no network access and no third-party
dependencies:

- a small JSON Schema subset that fails loudly on unknown keywords, so a typo
  in a schema cannot silently weaken it;
- the semantic rules the schemas cannot express: derived ids, familiar
  lifecycle, duplicate policy per kind, ``attach_modifier`` references, gamble
  table coverage, power-score arithmetic and loot-modifier bounds;
- ``chaoslab datapack --selftest``, which proves the validator rejects bad
  input instead of assuming it does.

``chaoslab verify`` writes ``reports/datapack_report.md`` from this module and
validates the same files as inputs, so the contract cannot drift from the
committed report.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .util import ensure_dir

SCHEMA_DIR = Path("mod") / "schema"
DATAPACK_DIR = Path("mod") / "datapack"
EXAMPLES_DIR = Path("mod") / "examples"
CONFIG_DIR = Path("mod") / "config"
REPORT_NAME = Path("reports") / "datapack_report.md"

# Registry directory (under ``data/<namespace>/``) -> schema file.
REGISTRY_SCHEMAS = {
    "entry": "entry.schema.json",
    "feat": "feat.schema.json",
    "curse": "curse.schema.json",
    "module": "module.schema.json",
    "advancement": "advancement.schema.json",
}
GLM_REGISTRY = "loot_modifiers"
GLM_SCHEMA = "loot_modifier.schema.json"
TAGS_REGISTRY = "tags"
CONFIG_SCHEMAS = {"power_score.json": "power_score.schema.json"}

# Registries whose key namespace is `gacha`; NeoForge stores them under
# data/<pack_ns>/gacha/<registry>/ rather than data/<pack_ns>/<registry>/.
PREFIXED_REGISTRIES = frozenset({"entry", "feat", "curse", "module"})

MAX_ERRORS_PER_FILE = 20

# The duplicate policy of PROJECT_PLAN.md section 6.6, per entry kind. An entry
# may omit ``duplicate`` and let the engine derive it; when present it must be
# one of these.
DUPLICATE_POLICY = {
    "item": frozenset({"stack", "residue"}),
    "ability": frozenset({"insight", "residue"}),
    "trait": frozenset({"insight", "residue"}),
    "skill": frozenset({"insight", "residue"}),
    "familiar": frozenset({"insight", "count", "lost", "cooldown"}),
    "vehicle": frozenset({"residue"}),
    "location": frozenset({"residue"}),
    "modifier": frozenset(),
    "system": frozenset(),
}
ADAPTERLESS_KINDS = frozenset({"modifier", "system"})

TICKET_BANDS = (
    "Trash",
    "Bronze",
    "Silver",
    "Gold",
    "Aluminium",
    "Platinum",
    "Diamond",
    "Legendary",
    "Mythical",
    "Wild",
    "Divine",
    "Transcendent",
)

_NAMESPACE_RE = re.compile(r"^[a-z0-9_.-]+$")
_NAME_RE = re.compile(r"^[a-z0-9_][a-z0-9_./-]*$")
_DATA_PATH = re.compile(r"^data/(?P<ns>[a-z0-9_.-]+)/(?P<rest>.+)$")

# Draft 2020-12 subset. ``check_schema`` rejects anything else, so a misspelled
# keyword is an error rather than a silently ignored assertion.
_ASSERTIONS = frozenset(
    {
        "type",
        "enum",
        "const",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "minLength",
        "maxLength",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "oneOf",
        "anyOf",
        "$ref",
    }
)
_ANNOTATIONS = frozenset(
    {
        "$schema",
        "$id",
        "title",
        "description",
        "$comment",
        "default",
        "examples",
        "deprecated",
        "readOnly",
        "writeOnly",
        "$defs",
    }
)
_TYPES = ("null", "boolean", "object", "array", "number", "integer", "string")

_TAG_SCHEMA = {
    "type": "object",
    "additionalProperties": {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "uniqueItems": True,
    },
}


def _resolve(root: Path, path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _canonical(value) -> str:
    """A hashable, bool/int-distinguishing rendering of a JSON value."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _type_ok(type_name: str, value) -> bool:
    if type_name == "null":
        return value is None
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "object":
        return isinstance(value, dict)
    return False


def check_schema(node, where: str, errors: list[str]) -> None:
    """Structurally validate a schema node against the supported subset."""
    if isinstance(node, bool):
        return
    if not isinstance(node, dict):
        errors.append(f"{where}: schema must be an object or boolean")
        return
    for key in sorted(node):
        if key not in _ASSERTIONS and key not in _ANNOTATIONS:
            errors.append(f"{where}: unsupported schema keyword {key!r}")
    if "type" in node:
        types = node["type"]
        if isinstance(types, str):
            types = [types]
        if (
            not isinstance(types, list)
            or not types
            or any(not isinstance(item, str) or item not in _TYPES for item in types)
        ):
            errors.append(f"{where}.type: must be a type name or an array of type names")
    if "required" in node:
        required = node["required"]
        if (
            not isinstance(required, list)
            or any(not isinstance(item, str) or not item for item in required)
            or len(set(required)) != len(required)
        ):
            errors.append(f"{where}.required: must be an array of unique non-empty strings")
    if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"]):
        errors.append(f"{where}.enum: must be a non-empty array")
    if "properties" in node:
        properties = node["properties"]
        if not isinstance(properties, dict):
            errors.append(f"{where}.properties: must be an object")
        else:
            for name in sorted(properties):
                check_schema(properties[name], f"{where}.properties.{name}", errors)
    if "additionalProperties" in node:
        extra = node["additionalProperties"]
        if not isinstance(extra, bool):
            check_schema(extra, f"{where}.additionalProperties", errors)
    if "items" in node:
        check_schema(node["items"], f"{where}.items", errors)
    for key in ("oneOf", "anyOf"):
        if key in node:
            branches = node[key]
            if not isinstance(branches, list) or not branches:
                errors.append(f"{where}.{key}: must be a non-empty array of schemas")
            else:
                for index, branch in enumerate(branches):
                    check_schema(branch, f"{where}.{key}[{index}]", errors)
    if "$defs" in node:
        defs = node["$defs"]
        if not isinstance(defs, dict):
            errors.append(f"{where}.$defs: must be an object")
        else:
            for name in sorted(defs):
                check_schema(defs[name], f"{where}.$defs.{name}", errors)
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            errors.append(f"{where}.$ref: only '#/$defs/<name>' references are supported")
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        if key in node and not _type_ok("number", node[key]):
            errors.append(f"{where}.{key}: must be a number")
    for key in ("minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"):
        if key in node and not (_type_ok("integer", node[key]) and node[key] >= 0):
            errors.append(f"{where}.{key}: must be a non-negative integer")
    if "pattern" in node:
        pattern = node["pattern"]
        if not isinstance(pattern, str):
            errors.append(f"{where}.pattern: must be a string")
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{where}.pattern: {exc}")
    if "minItems" in node and "maxItems" in node and node["minItems"] > node["maxItems"]:
        errors.append(f"{where}: minItems exceeds maxItems")
    if "minProperties" in node and "maxProperties" in node and node["minProperties"] > node["maxProperties"]:
        errors.append(f"{where}: minProperties exceeds maxProperties")


class _Checker:
    """Validate one data value against one schema tree."""

    def __init__(self, root):
        self.root = root
        self.errors: list[str] = []
        self.truncated = False

    def _add(self, message: str) -> None:
        if len(self.errors) >= MAX_ERRORS_PER_FILE:
            self.truncated = True
            return
        self.errors.append(message)

    def _resolve(self, ref: str):
        name = ref[len("#/$defs/") :]
        defs = self.root.get("$defs") if isinstance(self.root, dict) else None
        if not isinstance(defs, dict):
            return None
        return defs.get(name)

    def validate(self, schema, data, path: str) -> None:
        if self.truncated:
            return
        if schema is True:
            return
        if schema is False:
            self._add(f"{path}: no value is allowed here")
            return
        if not isinstance(schema, dict):
            self._add(f"{path}: invalid schema node")
            return
        if "$ref" in schema:
            target = self._resolve(schema["$ref"])
            if target is None:
                self._add(f"{path}: unresolved schema reference {schema['$ref']!r}")
                return
            self.validate(target, data, path)
            rest = {key: value for key, value in schema.items() if key != "$ref"}
            if rest:
                self.validate(rest, data, path)
            return
        if "type" in schema:
            types = schema["type"]
            if isinstance(types, str):
                types = [types]
            if not any(_type_ok(name, data) for name in types):
                expected = " or ".join(types)
                self._add(f"{path}: expected {expected}, got {_kind(data)}")
                return
        if "const" in schema and _canonical(data) != _canonical(schema["const"]):
            self._add(f"{path}: expected {schema['const']!r}")
            return
        if "enum" in schema and _canonical(data) not in {
            _canonical(item) for item in schema["enum"]
        }:
            self._add(f"{path}: {data!r} is not one of {schema['enum']}")
            return
        if "oneOf" in schema:
            matches = 0
            for branch in schema["oneOf"]:
                probe = _Checker(self.root)
                probe.validate(branch, data, path)
                if not probe.errors:
                    matches += 1
            if matches != 1:
                hint = ""
                if isinstance(data, dict):
                    for key in ("type", "verb", "kind", "class"):
                        if key in data:
                            hint = f" ({key} = {data[key]!r})"
                            break
                self._add(f"{path}: matches {matches} oneOf variant(s), need exactly 1{hint}")
            return
        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                probe = _Checker(self.root)
                probe.validate(branch, data, path)
                if not probe.errors:
                    break
            else:
                self._add(f"{path}: matches no anyOf variant")
            return
        if isinstance(data, dict):
            self._object(schema, data, path)
        elif isinstance(data, list):
            self._array(schema, data, path)
        elif isinstance(data, str):
            self._string(schema, data, path)
        elif _type_ok("number", data):
            self._number(schema, data, path)

    def _object(self, schema: dict, data: dict, path: str) -> None:
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        for name in required:
            if name not in data:
                self._add(f"{path}: missing required property {name!r}")
        extra = schema.get("additionalProperties", True)
        for name in sorted(data):
            child = f"{path}.{name}"
            if name in properties:
                self.validate(properties[name], data[name], child)
            elif extra is False:
                self._add(f"{path}: unexpected property {name!r}")
            else:
                self.validate(extra, data[name], child)
        if "minProperties" in schema and len(data) < schema["minProperties"]:
            self._add(f"{path}: needs at least {schema['minProperties']} propert(ies)")
        if "maxProperties" in schema and len(data) > schema["maxProperties"]:
            self._add(f"{path}: allows at most {schema['maxProperties']} propert(ies)")

    def _array(self, schema: dict, data: list, path: str) -> None:
        if "minItems" in schema and len(data) < schema["minItems"]:
            self._add(f"{path}: needs at least {schema['minItems']} item(s)")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            self._add(f"{path}: allows at most {schema['maxItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(data):
                self.validate(schema["items"], item, f"{path}[{index}]")
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for index, item in enumerate(data):
                key = _canonical(item)
                if key in seen:
                    self._add(f"{path}[{index}]: duplicate item")
                seen.add(key)

    def _string(self, schema: dict, data: str, path: str) -> None:
        if "minLength" in schema and len(data) < schema["minLength"]:
            self._add(f"{path}: shorter than {schema['minLength']} character(s)")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            self._add(f"{path}: longer than {schema['maxLength']} character(s)")
        if "pattern" in schema and re.fullmatch(schema["pattern"], data) is None:
            self._add(f"{path}: {data!r} does not match {schema['pattern']!r}")

    def _number(self, schema: dict, data, path: str) -> None:
        if "minimum" in schema and data < schema["minimum"]:
            self._add(f"{path}: {data} is below the minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            self._add(f"{path}: {data} is above the maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            self._add(f"{path}: {data} must be above {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
            self._add(f"{path}: {data} must be below {schema['exclusiveMaximum']}")


def _valid_namespace(value: str) -> bool:
    return _NAMESPACE_RE.fullmatch(value) is not None


def _valid_name(value: str) -> bool:
    if not _NAME_RE.fullmatch(value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _discover(root: Path, area: Path, label: str) -> list[dict]:
    """Return one record per JSON file under ``area/data/``."""
    records: list[dict] = []
    data_root = area / "data"
    if not data_root.is_dir():
        records.append(
            {
                "rel": _rel(root, area),
                "area": label,
                "error": "no data/ directory",
            }
        )
        return records
    for path in sorted(data_root.rglob("*.json")):
        rel = _rel(root, path)
        relative = path.relative_to(data_root)
        parts = relative.parts
        record = {"rel": rel, "area": label, "payload": None, "error": None, "invalid": False}
        # NeoForge datapack registries live under
        # data/<pack_ns>/<registry_ns>/<registry_path>/ (Registries.elementsDirPath
        # prefixes non-minecraft namespaces), so `gacha:entry` is
        # data/*/gacha/entry/. Vanilla registries (advancement, tags) and
        # NeoForge's loot_modifiers stay at data/<pack_ns>/<registry>/.
        if len(parts) >= 4 and parts[1] == "gacha" and parts[2] in PREFIXED_REGISTRIES:
            namespace = "gacha"
            registry = parts[2]
            name = Path(*parts[3:]).with_suffix("").as_posix()
        elif len(parts) >= 3:
            namespace, registry = parts[0], parts[1]
            name = Path(*parts[2:]).with_suffix("").as_posix()
        else:
            record["error"] = "expected data/<namespace>/<registry>/<name>.json"
            records.append(record)
            continue
        record.update({"namespace": namespace, "registry": registry, "name": name})
        if not _valid_namespace(namespace):
            record["error"] = f"invalid namespace {namespace!r}"
            records.append(record)
            continue
        if not _valid_name(name):
            record["error"] = f"invalid registry name {name!r}"
            records.append(record)
            continue
        try:
            record["payload"] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            record["error"] = str(exc)
            records.append(record)
            continue
        record["id"] = f"{namespace}:{name}"
        records.append(record)
    return records


def _schema_for(registry: str, schemas: dict) -> tuple[dict | None, str | None]:
    if registry in REGISTRY_SCHEMAS:
        name = REGISTRY_SCHEMAS[registry]
    elif registry == GLM_REGISTRY:
        name = GLM_SCHEMA
    elif registry == TAGS_REGISTRY:
        return _TAG_SCHEMA, "tags"
    else:
        return None, None
    return schemas.get(name), name


def _modifier_refs(payload: dict) -> list[str]:
    hooks = payload.get("hooks") or {}
    refs: list[str] = []
    for slot in sorted(hooks):
        for hook in hooks[slot] or []:
            if isinstance(hook, dict) and hook.get("verb") == "attach_modifier":
                modifier = hook.get("modifier")
                if isinstance(modifier, str):
                    refs.append(modifier)
    return refs


def _roll_ordering(errors: list[str], roll, where: str) -> None:
    if not isinstance(roll, dict):
        return
    minimum, average, maximum = roll.get("min"), roll.get("avg"), roll.get("max")
    if None not in (minimum, average, maximum) and not (minimum <= average <= maximum):
        errors.append(f"{where}: must satisfy min <= avg <= max")


def _entry_semantics(payload: dict, record: dict) -> list[str]:
    errors: list[str] = []
    kind = payload.get("kind")
    adapter = payload.get("adapter")
    if kind not in ADAPTERLESS_KINDS and adapter is None:
        errors.append(f"$.adapter: kind {kind!r} requires an adapter")
    familiar = payload.get("familiar")
    if kind == "familiar":
        if not isinstance(familiar, dict):
            errors.append("$.familiar: familiar entries require a familiar object")
        else:
            life = familiar.get("class")
            if life == "group":
                if "count" not in familiar:
                    errors.append("$.familiar.count: group familiars require a count")
            elif "count" in familiar:
                errors.append(f"$.familiar.count: only group familiars carry a count (class {life!r})")
    elif familiar is not None:
        errors.append("$.familiar: only familiar entries may carry a familiar object")
    duplicate = payload.get("duplicate")
    if duplicate is not None:
        allowed = DUPLICATE_POLICY.get(kind, frozenset())
        if duplicate not in allowed:
            errors.append(
                f"$.duplicate: {duplicate!r} is not allowed for kind {kind!r}"
                + (f" (allowed: {', '.join(sorted(allowed))})" if allowed else " (no duplicate rule)")
            )
    hooks = payload.get("hooks") or {}
    for slot in sorted(hooks):
        for index, hook in enumerate(hooks[slot] or []):
            if isinstance(hook, dict) and hook.get("verb") == "grant_ticket":
                _roll_ordering(errors, hook.get("roll"), f"$.hooks.{slot}[{index}].roll")
    return errors


def _glm_semantics(payload: dict) -> list[str]:
    errors: list[str] = []
    kind = payload.get("type")
    if kind == "gacha:add_ticket":
        _roll_ordering(errors, (payload.get("ticket") or {}).get("roll"), "$.ticket.roll")
        count = payload.get("count")
        if isinstance(count, dict):
            minimum, maximum = count.get("min"), count.get("max")
            if minimum is not None and maximum is not None and minimum > maximum:
                errors.append("$.count: min exceeds max")
    elif kind == "gacha:remove_items":
        items = payload.get("items") or []
        tags = payload.get("tags") or []
        if not items and not tags:
            errors.append("$.items/$.tags: removal needs at least one item or tag to strip")
    return errors


def _module_semantics(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("kind") != "gamble":
        return errors
    seen: dict[int, str] = {}
    for index, row in enumerate(payload.get("table") or []):
        roll = row.get("roll") if isinstance(row, dict) else None
        outcome = row.get("outcome") if isinstance(row, dict) else None
        if isinstance(roll, int):
            values = [roll]
        elif isinstance(roll, list) and len(roll) == 2:
            if roll[0] > roll[1]:
                errors.append(f"$.table[{index}].roll: range runs backwards")
                continue
            values = list(range(roll[0], roll[1] + 1))
        else:
            continue
        for value in values:
            if value in seen:
                errors.append(
                    f"$.table[{index}]: roll {value} is already covered by {seen[value]!r}"
                )
            else:
                seen[value] = str(outcome)
    missing = [value for value in range(1, 21) if value not in seen]
    if missing:
        errors.append(f"$.table: rolls {missing} are not covered")
    return errors


def _power_score_semantics(payload: dict) -> list[str]:
    errors: list[str] = []
    weights = payload.get("weights")
    if not isinstance(weights, dict):
        return errors
    total = sum(value for value in weights.values() if isinstance(value, (int, float)))
    if abs(total - 1.0) > 0.001:
        errors.append(f"$.weights: sum to {total:.3f}, expected 1.000")
    bounds = payload.get("weight_bounds")
    if isinstance(bounds, list) and len(bounds) == 2:
        low, high = bounds
        if not (0.0 <= low < high <= 1.0):
            errors.append("$.weight_bounds: expected 0 <= min < max <= 1")
        else:
            for name in sorted(weights):
                value = weights[name]
                if isinstance(value, (int, float)) and not (low - 0.001 <= value <= high + 0.001):
                    errors.append(
                        f"$.weights.{name}: {value} is outside the declared bounds {bounds}"
                    )
    clamp = payload.get("score_clamp")
    if isinstance(clamp, list) and len(clamp) == 2:
        low, high = clamp
        if not (0.0 <= low < high <= 1.0):
            errors.append("$.score_clamp: expected 0 <= min < max <= 1")
    reference = payload.get("reference")
    if isinstance(reference, dict):
        for name in sorted(reference):
            value = reference[name]
            if isinstance(value, (int, float)) and value <= 0:
                errors.append(f"$.reference.{name}: must be positive")
    return errors


def validate(
    root,
    *,
    schema=SCHEMA_DIR,
    datapack=DATAPACK_DIR,
    examples=EXAMPLES_DIR,
    config=CONFIG_DIR,
) -> dict:
    """Validate every schema, datapack, fixture and config file under ``root``."""
    root = Path(root)
    errors: list[str] = []
    schemas: dict[str, dict] = {}
    schema_titles: dict[str, str] = {}

    schema_dir = _resolve(root, schema)
    schema_files = 0
    if not schema_dir.is_dir():
        errors.append(f"{_rel(root, schema_dir)}: directory missing")
    else:
        for path in sorted(schema_dir.glob("*.schema.json")):
            schema_files += 1
            rel = _rel(root, path)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{rel}: {exc}")
                continue
            schema_errors: list[str] = []
            check_schema(payload, "$", schema_errors)
            errors.extend(f"{rel}: {message}" for message in schema_errors)
            if isinstance(payload, dict) and not schema_errors:
                schemas[path.name] = payload
                schema_titles[path.name] = str(payload.get("title") or path.stem)

    records: list[dict] = []
    for label, directory in (("datapack", datapack), ("examples", examples)):
        area = _resolve(root, directory)
        if area.is_dir():
            records.extend(_discover(root, area, label))
        else:
            records.append({"rel": _rel(root, area), "area": label, "error": "directory missing"})

    by_id: dict[str, dict] = {}
    modifier_refs: list[tuple[dict, str]] = []
    glm_manifest: dict | None = None
    for record in records:
        rel = record["rel"]
        if record.get("error"):
            errors.append(f"{rel}: {record['error']}")
            record["invalid"] = True
            continue
        registry = record["registry"]
        if (
            registry == GLM_REGISTRY
            and record["name"] == "global_loot_modifiers"
            and record["area"] == "datapack"
        ):
            # NeoForge only loads the modifiers listed in this manifest; a file
            # on disk that is not listed is silently inert. Validate the
            # manifest itself and cross-check it after the loop.
            payload = record["payload"]
            if not isinstance(payload, dict):
                errors.append(f"{rel}: expected a JSON object")
                record["invalid"] = True
            else:
                entries = payload.get("entries")
                if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
                    errors.append(f"{rel}: 'entries' must be a list of modifier ids")
                    record["invalid"] = True
                elif payload.get("replace") not in (None, True, False):
                    errors.append(f"{rel}: 'replace' must be a boolean")
                    record["invalid"] = True
                else:
                    glm_manifest = {item: record for item in entries}
            continue
        schema_payload, schema_name = _schema_for(registry, schemas)
        if schema_payload is None:
            if schema_name is None:
                errors.append(f"{rel}: no schema is mapped for registry {registry!r}")
            else:
                errors.append(f"{rel}: schema {schema_name!r} is missing or invalid")
            record["invalid"] = True
            continue
        checker = _Checker(schema_payload)
        checker.validate(schema_payload, record["payload"], "$")
        if checker.errors:
            errors.extend(f"{rel}: {message}" for message in checker.errors)
            if checker.truncated:
                errors.append(f"{rel}: more than {MAX_ERRORS_PER_FILE} errors; output truncated")
            record["invalid"] = True
            continue
        payload = record["payload"]
        if registry in REGISTRY_SCHEMAS:
            if record["id"] in by_id:
                errors.append(f"{rel}: duplicate id {record['id']!r}")
                record["invalid"] = True
            else:
                by_id[record["id"]] = record
        if registry == "entry":
            semantic = _entry_semantics(payload, record)
            errors.extend(f"{rel}: {message}" for message in semantic)
            if semantic:
                record["invalid"] = True
            for ref in _modifier_refs(payload):
                modifier_refs.append((record, ref))
        elif registry == GLM_REGISTRY:
            semantic = _glm_semantics(payload)
            errors.extend(f"{rel}: {message}" for message in semantic)
            if semantic:
                record["invalid"] = True
        elif registry == "module":
            semantic = _module_semantics(payload)
            errors.extend(f"{rel}: {message}" for message in semantic)
            if semantic:
                record["invalid"] = True

    for record, ref in modifier_refs:
        target = by_id.get(ref)
        if target is None:
            errors.append(f"{record['rel']}: attach_modifier {ref!r} names no entry")
            record["invalid"] = True
        elif target["payload"].get("kind") != "modifier":
            errors.append(
                f"{record['rel']}: attach_modifier {ref!r} is not a modifier "
                f"(kind {target['payload'].get('kind')!r})"
            )
            record["invalid"] = True

    # Advancement tabs are data, and two mistakes are invisible until the client
    # draws them: a root with no background shows the missing-texture grid, and
    # a parent that does not resolve silently starts a new tab. The quest layer
    # keys off these ids, so treat both as errors.
    advancements = {
        record["id"]: record
        for record in records
        if record["area"] == "datapack"
        and record["registry"] == "advancement"
        and not record.get("invalid")
    }
    for advancement_id, record in sorted(advancements.items()):
        payload = record["payload"]
        display = payload.get("display")
        parent = payload.get("parent")
        if isinstance(display, dict):
            for key in ("icon", "title", "description"):
                if key not in display:
                    errors.append(f"{record['rel']}: display is missing {key!r}")
                    record["invalid"] = True
            if not parent and not display.get("background"):
                errors.append(
                    f"{record['rel']}: a root advancement needs display.background "
                    "or the client renders a missing texture"
                )
                record["invalid"] = True
        if parent and parent not in advancements:
            errors.append(f"{record['rel']}: parent {parent!r} names no advancement")
            record["invalid"] = True

    # One table must feed one band: a table listed in two injection files would
    # receive two tickets from the same chest. This is cheap to check and easy
    # to reintroduce with a bulk allowlist edit.
    injected: dict[str, dict] = {}
    for record in records:
        if record.get("invalid") or record["registry"] != GLM_REGISTRY:
            continue
        if record["area"] != "datapack":
            continue
        payload = record["payload"]
        if payload.get("type") != "gacha:add_ticket":
            continue
        for table in payload.get("tables") or []:
            if table in injected:
                errors.append(
                    f"{record['rel']}: loot table {table!r} is also injected by "
                    f"{injected[table]['rel']}"
                )
                record["invalid"] = True
            else:
                injected[table] = record

    # NeoForge's LootModifierManager only applies modifiers named in
    # data/<ns>/loot_modifiers/global_loot_modifiers.json. A modifier file that
    # is not listed (or a listed id with no file) is inert, so it is an error,
    # not a warning: the shipped GLMs must actually load.
    modifiers = {
        record["id"]: record
        for record in records
        if record["registry"] == GLM_REGISTRY
        and record["area"] == "datapack"
        and record["name"] != "global_loot_modifiers"
        and not record.get("invalid")
    }
    if glm_manifest is None:
        if modifiers:
            errors.append(
                "data/neoforge/loot_modifiers/global_loot_modifiers.json is missing; "
                "NeoForge will not load any listed modifier"
            )
    else:
        for modifier_id in sorted(modifiers):
            if modifier_id not in glm_manifest:
                errors.append(
                    f"{modifiers[modifier_id]['rel']}: not listed in "
                    "global_loot_modifiers.json"
                )
                modifiers[modifier_id]["invalid"] = True
        for modifier_id, record in sorted(glm_manifest.items()):
            if modifier_id not in modifiers:
                errors.append(
                    f"{record['rel']}: entry {modifier_id!r} names no modifier file"
                )
                record["invalid"] = True

    configs: list[dict] = []
    config_dir = _resolve(root, config)
    config_files = 0
    if not config_dir.is_dir():
        errors.append(f"{_rel(root, config_dir)}: directory missing")
    else:
        for path in sorted(config_dir.glob("*.json")):
            config_files += 1
            rel = _rel(root, path)
            schema_name = CONFIG_SCHEMAS.get(path.name)
            if schema_name is None:
                errors.append(f"{rel}: no schema is mapped for this config file")
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{rel}: {exc}")
                continue
            schema_payload = schemas.get(schema_name)
            if schema_payload is None:
                errors.append(f"{rel}: schema {schema_name!r} is missing or invalid")
                continue
            checker = _Checker(schema_payload)
            checker.validate(schema_payload, payload, "$")
            if checker.errors:
                errors.extend(f"{rel}: {message}" for message in checker.errors)
                continue
            if path.name == "power_score.json":
                errors.extend(f"{rel}: {message}" for message in _power_score_semantics(payload))
            configs.append({"rel": rel, "name": path.name, "payload": payload})

    files = len(records) + len(configs)
    return {
        "ok": not errors,
        "files": files,
        "schemas": schemas,
        "schema_titles": schema_titles,
        "schema_files": schema_files,
        "records": records,
        "configs": configs,
        "config_files": config_files,
        "errors": errors,
    }


# --------------------------------------------------------------------------- report
def _cell(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _counts(values) -> list[tuple[str, int]]:
    counter = Counter(str(value) for value in values)
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def _render(result: dict) -> str:
    schemas = result["schemas"]
    records = result["records"]
    configs = result["configs"]
    errors = result["errors"]
    valid = [
        record
        for record in records
        if not record.get("error") and not record.get("invalid")
    ]
    shipped = [record for record in valid if record["area"] == "datapack"]
    fixtures = [record for record in valid if record["area"] == "examples"]
    state = "PASS" if result["ok"] else "FAIL"

    lines = [
        "# Datapack validation",
        "",
        "Generated by `chaoslab datapack` with no network access. This checks the",
        "custom mod's configuration contract before any Java exists: every JSON file",
        "under `mod/datapack/`, `mod/examples/` and `mod/config/` is validated against",
        "the JSON Schemas in `mod/schema/`, plus the cross-file rules a schema cannot",
        "express. `mod/datapack/` is what the mod ships; `mod/examples/` is the",
        "validation fixture set and is not shipped.",
        "",
        f"Result: {state} — {result['files']} file(s) validated against "
        f"{len(schemas)} schema(s); {len(errors)} error(s).",
        "",
        "## Schemas",
        "",
        "| schema | title | registry |",
        "| --- | --- | --- |",
    ]
    for name in sorted(schemas):
        applies = [
            registry
            for registry, schema_name in REGISTRY_SCHEMAS.items()
            if schema_name == name
        ]
        if name == GLM_SCHEMA:
            applies = [GLM_REGISTRY]
        if name in CONFIG_SCHEMAS.values():
            applies = ["config"]
        lines.append(
            f"| `{name}` | {_cell(result['schema_titles'].get(name))} | "
            f"{_cell(', '.join(sorted(applies)))} |"
        )

    lines += ["", "## Shipped datapack", ""]
    if shipped:
        lines += [
            "| file | id | kind | detail |",
            "| --- | --- | --- | --- |",
        ]
        for record in sorted(shipped, key=lambda item: item.get("id") or item["rel"]):
            payload = record["payload"]
            kind = payload.get("kind") or payload.get("type")
            lines.append(
                "| `{}` | `{}` | {} | {} |".format(
                    _cell(record["rel"]),
                    _cell(record.get("id")),
                    _cell(kind),
                    _cell(_record_detail(record)),
                )
            )
    else:
        lines.append("No content files ship yet; the seed modules and config are below.")

    modules = [record for record in shipped if record["registry"] == "module"]
    if modules:
        lines += ["", "### Module definitions", ""]
        for record in sorted(modules, key=lambda item: item["id"]):
            payload = record["payload"]
            if payload.get("kind") == "gamble":
                lines.append(
                    f"- `{record['id']}`: gamble, stakes "
                    f"{', '.join(str(value) for value in payload.get('stake') or [])}; "
                    "outcome table below."
                )
                lines += ["", "| roll | outcome |", "| --- | --- |"]
                for row in payload.get("table") or []:
                    roll = row.get("roll")
                    label = f"{roll[0]}–{roll[1]}" if isinstance(roll, list) else str(roll)
                    lines.append(f"| {label} | {_cell(row.get('outcome'))} |")
            else:
                lines.append(f"- `{record['id']}`: {payload.get('kind')}, bands {payload.get('bands')}")

    for entry in configs:
        if entry["name"] != "power_score.json":
            continue
        payload = entry["payload"]
        lines += [
            "",
            "### Power score default",
            "",
            f"`{entry['rel']}` (the answered D3 default; the decision sheet is the",
            "source of record).",
            "",
            "| input | weight |",
            "| --- | --- |",
        ]
        for name in sorted(payload.get("weights") or {}):
            lines.append(f"| {name} | {payload['weights'][name]:.2f} |")
        lines += [
            "",
            f"- Range: ±{payload.get('weight_range', 0.0):.2f}",
            f"- Weight bounds: {payload.get('weight_bounds', [])[0]:.2f} .. "
            f"{payload.get('weight_bounds', [0.0, 0.0])[-1]:.2f}",
            f"- Score clamp: {payload.get('score_clamp', [])[0]:.1f} .. "
            f"{payload.get('score_clamp', [0.0, 0.0])[-1]:.1f}",
            f"- Reference: gear {payload.get('reference', {}).get('gear')}, "
            f"entries {payload.get('reference', {}).get('entries')}",
        ]

    lines += ["", "## Fixtures (mod/examples, not shipped)", ""]
    if fixtures:
        lines.append(f"Files: {len(fixtures)}.")
        registry_counts = _counts(record["registry"] for record in fixtures)
        lines.append("")
        lines.append(
            "- by registry: "
            + ", ".join(f"{name} {count}" for name, count in registry_counts)
        )
        entries = [record for record in fixtures if record["registry"] == "entry"]
        if entries:
            lines.append(
                "- entries by kind: "
                + ", ".join(
                    f"{name} {count}"
                    for name, count in _counts(
                        record["payload"].get("kind") for record in entries
                    )
                )
            )
            adapters = [
                (record["payload"].get("adapter") or {}).get("type")
                for record in entries
                if isinstance(record["payload"].get("adapter"), dict)
            ]
            if adapters:
                lines.append(
                    "- adapters: "
                    + ", ".join(
                        f"{name} {count}" for name, count in _counts(adapters)
                    )
                )
            verbs = [
                hook.get("verb")
                for record in entries
                for slot in sorted(record["payload"].get("hooks") or {})
                for hook in record["payload"]["hooks"][slot] or []
                if isinstance(hook, dict)
            ]
            if verbs:
                lines.append(
                    "- hook verbs: "
                    + ", ".join(f"{name} {count}" for name, count in _counts(verbs))
                )
        curses = [record for record in fixtures if record["registry"] == "curse"]
        if curses:
            lines.append(
                "- curses by hook: "
                + ", ".join(
                    f"{name} {count}"
                    for name, count in _counts(
                        (record["payload"].get("hook") or {}).get("type")
                        for record in curses
                    )
                )
            )
        feats = [record for record in fixtures if record["registry"] == "feat"]
        if feats:
            lines.append(
                "- feats by trigger: "
                + ", ".join(
                    f"{name} {count}"
                    for name, count in _counts(
                        (record["payload"].get("trigger") or {}).get("type")
                        for record in feats
                    )
                )
            )
    else:
        lines.append("No fixtures.")

    lines += [
        "",
        "## Checks beyond JSON Schema",
        "",
        "- registry directories map to schemas; unknown paths are errors",
        "- ids derive from file paths and are unique across the whole dataset",
        "- entries carry an adapter unless their kind is modifier or system",
        "- familiar lifecycle rules (count only for group familiars) hold",
        "- duplicate policy matches the kind (PROJECT_PLAN.md section 6.6)",
        "- `attach_modifier` references resolve to modifier entries",
        "- the gamble table covers rolls 1..20 exactly once",
        "- power-score weights sum to 1.00 and respect their declared bounds",
        "- ticket rolls satisfy min <= avg <= max; removal lists at least one item or tag",
        "- advancement roots have a background and every parent resolves",
        "- each loot table is injected by at most one band file",
        "- every loot modifier file is listed in `global_loot_modifiers.json`",
        "",
        "## Errors",
        "",
    ]
    if errors:
        for message in errors:
            lines.append(f"- {message}")
    else:
        lines.append("None.")

    lines += [
        "",
        "## Provenance",
        "",
        "Schemas and content live in `mod/`; the default config is the answered D3",
        "default; `chaoslab datapack --selftest` proves the validator",
        "rejects malformed input; `chaoslab verify` regenerates this report offline",
        "and pins it in `reports/MANIFEST.sha256`.",
        "",
    ]
    return "\n".join(lines)


def _record_detail(record: dict) -> str:
    payload = record["payload"]
    registry = record["registry"]
    if registry == "module":
        return f"kind {payload.get('kind')}"
    if registry == "entry":
        adapter = payload.get("adapter") or {}
        kind = payload.get("kind")
        if isinstance(adapter, dict) and adapter.get("type"):
            return f"{kind}; adapter {adapter['type']}"
        return str(kind)
    if registry == GLM_REGISTRY:
        if record.get("name") == "global_loot_modifiers":
            return f"{len(payload.get('entries') or [])} modifier(s) listed"
        if payload.get("type") == "gacha:add_ticket":
            return f"ticket injection into {len(payload.get('tables') or [])} table(s)"
        return f"item removal from {len(payload.get('tables') or [])} table(s)"
    return ""


def run(root, *, schema=SCHEMA_DIR, datapack=DATAPACK_DIR, examples=EXAMPLES_DIR, config=CONFIG_DIR, report=REPORT_NAME) -> dict:
    """Validate the contract and write ``reports/datapack_report.md``."""
    root = Path(root)
    result = validate(root, schema=schema, datapack=datapack, examples=examples, config=config)
    path = _resolve(root, report)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(_render(result), encoding="utf-8")
    tmp.replace(path)
    result["report"] = str(path)
    return result


def _check_pack_quests(root) -> list[dict]:
    """Validate the Heracles quest files that ship as pack content.

    Heracles reads ``title``/``subtitle`` with ``ComponentSerialization.FLAT_CODEC``,
    which expects a *string containing JSON*, not a plain string or an object.
    A plain string silently falls back to "New Quest", and an empty ``groups``
    map makes the quest invisible. The task and reward keys are likewise easy
    to get wrong (``advancements``, ``xptype``).
    """
    root = Path(root)
    directory = root / "pack" / "quests"
    row = {
        "path": "pack/quests",
        "kind": "input",
        "status": "valid",
        "detail": "",
        "sha256": None,
    }
    if not directory.is_dir():
        row["detail"] = "no pack quests"
        return [row]
    errors: list[str] = []
    files = sorted(directory.glob("*.json"))
    for path in files:
        rel = f"pack/quests/{path.name}"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{rel}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{rel}: expected a JSON object")
            continue
        display = payload.get("display")
        if not isinstance(display, dict):
            errors.append(f"{rel}: missing display object")
            continue
        for key in ("title", "subtitle"):
            value = display.get(key)
            if value is not None and not isinstance(value, str):
                errors.append(
                    f"{rel}: display.{key} must be a string containing JSON "
                    "(Heracles FLAT_CODEC), not an object"
                )
        groups = display.get("groups")
        if groups is not None and (not isinstance(groups, dict) or not groups):
            errors.append(f"{rel}: display.groups must name at least one group")
        tasks = payload.get("tasks") or {}
        if isinstance(tasks, dict):
            for task_id, task in tasks.items():
                if not isinstance(task, dict):
                    continue
                if task.get("type") == "heracles:advancement" and not isinstance(
                    task.get("advancements"), list
                ):
                    errors.append(
                        f"{rel}: task {task_id!r} must use an 'advancements' list"
                    )
        rewards = payload.get("rewards") or {}
        if isinstance(rewards, dict):
            for reward_id, reward in rewards.items():
                if not isinstance(reward, dict):
                    continue
                if reward.get("type") == "heracles:xp" and "xptype" not in reward:
                    errors.append(f"{rel}: reward {reward_id!r} must use 'xptype'")
    if errors:
        row["status"] = "invalid"
        row["detail"] = "; ".join(errors[:5])
        if len(errors) > 5:
            row["detail"] += f"; +{len(errors) - 5} more"
    else:
        row["detail"] = f"{len(files)} quest file(s) valid"
    row["sha256"] = hashlib.sha256(
        "\n".join(path.name for path in files).encode("utf-8")
    ).hexdigest()
    return [row]


def check_inputs(root) -> list[dict]:
    """Return one gate-input row per contract area."""
    result = validate(root)
    errors = result["errors"]
    rows: list[dict] = []
    counts = {
        "schema": result["schema_files"],
        "datapack": sum(1 for record in result["records"] if record.get("area") == "datapack"),
        "examples": sum(1 for record in result["records"] if record.get("area") == "examples"),
        "config": result["config_files"],
    }
    for label, directory, noun in (
        ("schema", SCHEMA_DIR, "schema"),
        ("datapack", DATAPACK_DIR, "file"),
        ("examples", EXAMPLES_DIR, "fixture"),
        ("config", CONFIG_DIR, "config file"),
    ):
        prefix = Path(directory).as_posix()
        scoped = [
            message
            for message in errors
            if message.startswith(prefix + "/") or message.startswith(prefix + ":")
        ]
        row = {
            "path": directory.as_posix(),
            "kind": "mod contract",
            "status": "valid",
            "detail": "",
            "sha256": None,
        }
        if scoped:
            row["status"] = "invalid"
            shown = "; ".join(scoped[:3])
            if len(scoped) > 3:
                shown += f"; and {len(scoped) - 3} more"
            row["detail"] = shown
        else:
            row["detail"] = f"{counts[label]} {noun}(s) valid"
        rows.append(row)
    rows.extend(_check_pack_quests(root))
    return rows


# --------------------------------------------------------------------------- selftest
def _case_is_valid(schema, data) -> bool:
    schema_errors: list[str] = []
    check_schema(schema, "$", schema_errors)
    if schema_errors:
        return False
    checker = _Checker(schema)
    checker.validate(schema, data, "$")
    return not checker.errors


def selftest() -> list[dict]:
    """Prove the validator accepts valid input and rejects malformed input."""
    cases = [
        ("accepts a matching type", {"type": "string"}, "x", True),
        ("rejects a wrong type", {"type": "string"}, 3, False),
        ("rejects a boolean where an integer is required", {"type": "integer"}, True, False),
        ("accepts a type union with null", {"type": ["string", "null"]}, None, True),
        ("rejects a missing required property", {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}, {}, False),
        ("rejects an unexpected property", {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "integer"}}}, {"a": 1, "b": 2}, False),
        ("validates additionalProperties schemas", {"type": "object", "additionalProperties": {"type": "integer"}}, {"a": "x"}, False),
        ("rejects an enum miss", {"enum": ["a", "b"]}, "c", False),
        ("rejects a const mismatch", {"type": "object", "required": ["k"], "properties": {"k": {"const": "a"}}}, {"k": "b"}, False),
        ("rejects a oneOf with two matches", {"oneOf": [{"type": "number"}, {"type": "integer"}]}, 3, False),
        ("rejects a oneOf with no match", {"oneOf": [{"type": "object"}, {"type": "array"}]}, "x", False),
        ("accepts a matching anyOf", {"anyOf": [{"type": "string"}, {"type": "number"}]}, 4, True),
        ("rejects a numeric maximum", {"type": "number", "maximum": 2.5}, 3, False),
        ("rejects an exclusive minimum", {"type": "number", "exclusiveMinimum": 0}, 0, False),
        ("rejects a pattern miss", {"type": "string", "pattern": "^[a-z]+$"}, "ABC", False),
        ("rejects duplicate items", {"type": "array", "uniqueItems": True, "items": {"type": "integer"}}, [1, 1], False),
        ("rejects too few items", {"type": "array", "minItems": 1}, [], False),
        ("resolves a local reference", {"$defs": {"n": {"type": "integer"}}, "$ref": "#/$defs/n"}, 3, True),
        ("rejects an unresolved reference", {"$ref": "#/$defs/missing"}, 3, False),
        ("rejects an unsupported keyword", {"type": "number", "maximumx": 3}, 3, False),
        ("rejects a boolean-false subschema", {"type": "array", "items": False}, [1], False),
    ]
    results: list[dict] = []
    for name, schema, data, expected in cases:
        actual = _case_is_valid(schema, data)
        results.append(
            {
                "name": name,
                "ok": actual == expected,
                "detail": "" if actual == expected else f"expected valid={expected}, got {actual}",
            }
        )
    return results
