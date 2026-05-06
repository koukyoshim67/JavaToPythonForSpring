import re
import sys
from pathlib import Path
from typing import Optional


def to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def map_java_type_to_python(java_type: str) -> str:
    t = java_type.strip()
    t = re.sub(r"@\w+\s*", "", t).strip()

    list_match = re.match(r"List<\s*(.+?)\s*>", t)
    map_match = re.match(r"Map<\s*(.+?)\s*,\s*(.+?)\s*>", t)
    opt_match = re.match(r"Optional<\s*(.+?)\s*>", t)

    if list_match:
        inner = map_java_type_to_python(list_match.group(1))
        return f"list[{inner}]"
    if map_match:
        k = map_java_type_to_python(map_match.group(1))
        v = map_java_type_to_python(map_match.group(2))
        return f"dict[{k}, {v}]"
    if opt_match:
        inner = map_java_type_to_python(opt_match.group(1))
        return f"Optional[{inner}]"

    mapping = {
        "String": "str",
        "int": "int",
        "Integer": "int",
        "long": "int",
        "Long": "int",
        "boolean": "bool",
        "Boolean": "bool",
        "double": "float",
        "Double": "float",
        "float": "float",
        "Float": "float",
        "void": "None",
        "Object": "dict",
    }
    return mapping.get(t, t)


def parse_class_name(java_code: str) -> str:
    m = re.search(r"\bclass\s+(\w+)", java_code)
    return m.group(1) if m else "ApiController"


def parse_base_path(java_code: str) -> str:
    m = re.search(r'@RequestMapping\(\s*"([^"]+)"\s*\)', java_code)
    return m.group(1) if m else ""


def parse_endpoint_annotation(method_block: str) -> tuple[Optional[str], Optional[str]]:
    patterns = [
        (r'@GetMapping\(\s*"([^"]*)"\s*\)', "get"),
        (r'@GetMapping\b', "get"),
        (r'@PostMapping\(\s*"([^"]*)"\s*\)', "post"),
        (r'@PostMapping\b', "post"),
        (r'@PutMapping\(\s*"([^"]*)"\s*\)', "put"),
        (r'@PutMapping\b', "put"),
        (r'@DeleteMapping\(\s*"([^"]*)"\s*\)', "delete"),
        (r'@DeleteMapping\b', "delete"),
        (r'@PatchMapping\(\s*"([^"]*)"\s*\)', "patch"),
        (r'@PatchMapping\b', "patch"),
    ]

    for pat, verb in patterns:
        m = re.search(pat, method_block)
        if m:
            path = m.group(1) if m.groups() else ""
            return verb, path
    return None, None


def parse_method_signature(method_block: str) -> Optional[tuple[str, str, str]]:
    m = re.search(
        r"public\s+([\w<>,\s@?]+)\s+(\w+)\s*\((.*?)\)\s*\{",
        method_block,
        re.S,
    )
    if not m:
        return None
    return_type = map_java_type_to_python(" ".join(m.group(1).split()))
    method_name = m.group(2)
    params = " ".join(m.group(3).split())
    return return_type, method_name, params


def parse_params(params_text: str) -> tuple[list[str], list[str], list[str]]:
    fn_params: list[str] = []
    path_vars: list[str] = []
    query_params: list[str] = []

    if not params_text.strip():
        return fn_params, path_vars, query_params

    raw_params = [p.strip() for p in params_text.split(",") if p.strip()]
    for p in raw_params:
        p_clean = re.sub(r"final\s+", "", p).strip()

        req_body = re.search(r"@RequestBody\s+(.+?)\s+(\w+)$", p_clean)
        if req_body:
            j_type, name = req_body.group(1), req_body.group(2)
            py_type = map_java_type_to_python(j_type)
            fn_params.append(f"{name}: {py_type}")
            continue

        path_var = re.search(
            r'@PathVariable(?:\(\s*"([^"]+)"\s*\))?\s+(.+?)\s+(\w+)$', p_clean
        )
        if path_var:
            var_name = path_var.group(1) or path_var.group(3)
            j_type = path_var.group(2)
            py_type = map_java_type_to_python(j_type)
            arg_name = path_var.group(3)
            fn_params.append(f"{arg_name}: {py_type}")
            path_vars.append(var_name)
            continue

        req_param = re.search(
            r'@RequestParam(?:\(\s*"([^"]+)"\s*\))?\s+(.+?)\s+(\w+)$', p_clean
        )
        if req_param:
            q_name = req_param.group(1) or req_param.group(3)
            j_type = req_param.group(2)
            py_type = map_java_type_to_python(j_type)
            arg_name = req_param.group(3)
            fn_params.append(f"{arg_name}: {py_type}")
            query_params.append(q_name)
            continue

        plain = re.match(r"(.+?)\s+(\w+)$", p_clean)
        if plain:
            j_type, name = plain.group(1), plain.group(2)
            py_type = map_java_type_to_python(j_type)
            fn_params.append(f"{name}: {py_type}")

    return fn_params, path_vars, query_params


def ensure_path_params(path: str, fn_params: list[str]) -> str:
    for p in re.findall(r"\{(\w+)\}", path):
        if not any(x.startswith(f"{p}:") for x in fn_params):
            fn_params.append(f"{p}: str")
    return path


def split_method_blocks(java_code: str) -> list[str]:
    blocks: list[str] = []
    annotation_pat = re.compile(
        r"(@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)[\s\S]*?)(?=public\s+[\w<>,\s@?]+\s+\w+\s*\()",
        re.M,
    )
    for m in annotation_pat.finditer(java_code):
        start = m.start()
        sig_match = re.search(
            r"public\s+[\w<>,\s@?]+\s+\w+\s*\(.*?\)\s*\{", java_code[m.end() :], re.S
        )
        if not sig_match:
            continue
        method_start = m.end() + sig_match.start()
        brace_start = m.end() + sig_match.end() - 1

        depth = 0
        end_idx = brace_start
        for i in range(brace_start, len(java_code)):
            if java_code[i] == "{":
                depth += 1
            elif java_code[i] == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        blocks.append(java_code[start : end_idx + 1])
    return blocks


def convert_java_to_fastapi(java_code: str) -> str:
    class_name = parse_class_name(java_code)
    router_name = to_snake(class_name.replace("Controller", "")) or "api"
    base_path = parse_base_path(java_code)

    lines: list[str] = [
        "from typing import Optional",
        "",
        "from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status",
        "from pydantic import BaseModel",
        "",
        "",
        "class ItemDTO(BaseModel):",
        "    id: Optional[int] = None",
        "    name: str",
        "    active: bool = True",
        "",
        "",
        "class Service:",
        "    def __init__(self) -> None:",
        "        self._store: dict[int, ItemDTO] = {}",
        "        self._seq: int = 1",
        "",
        "    def list_items(self) -> list[ItemDTO]:",
        "        return list(self._store.values())",
        "",
        "    def get_item(self, item_id: int) -> ItemDTO:",
        "        item = self._store.get(item_id)",
        "        if item is None:",
        '            raise HTTPException(status_code=404, detail="Item not found")',
        "        return item",
        "",
        "    def create_item(self, payload: ItemDTO) -> ItemDTO:",
        "        item = payload.model_copy(update={\"id\": self._seq})",
        "        self._store[self._seq] = item",
        "        self._seq += 1",
        "        return item",
        "",
        "",
        "def get_service() -> Service:",
        "    if not hasattr(get_service, \"_instance\"):",
        "        get_service._instance = Service()",
        "    return get_service._instance",
        "",
        "",
        f'router = APIRouter(prefix="{base_path}", tags=["{router_name}"])',
        "",
    ]

    method_blocks = split_method_blocks(java_code)
    added_any = False

    for block in method_blocks:
        verb, path = parse_endpoint_annotation(block)
        sig = parse_method_signature(block)
        if not verb or sig is None:
            continue

        return_type, method_name, params_text = sig
        fn_params, _, _ = parse_params(params_text)
        path = path or ""
        path = ensure_path_params(path, fn_params)

        dep = "service: Service = Depends(get_service)"
        all_params = ", ".join(fn_params + [dep]) if fn_params else dep

        status_code = "status.HTTP_200_OK"
        if verb == "post":
            status_code = "status.HTTP_201_CREATED"

        lines.extend(
            [
                f'@router.{verb}("{path}", status_code={status_code})',
                f"def {method_name}({all_params}) -> {return_type}:",
                "    try:",
            ]
        )

        if method_name.lower().startswith("get") and any("id:" in p for p in fn_params):
            id_param = next((p.split(":")[0].strip() for p in fn_params if "id:" in p), "item_id")
            lines.append(f"        return service.get_item({id_param})")
        elif method_name.lower().startswith("list") or method_name.lower().startswith("findall"):
            lines.append("        return service.list_items()")
        elif method_name.lower().startswith("create") or verb == "post":
            body_param = next((p.split(":")[0].strip() for p in fn_params if "DTO" in p or "dto" in p.lower()), None)
            lines.append(f"        return service.create_item({body_param or 'payload'})")
        else:
            lines.append('        raise HTTPException(status_code=501, detail="Not yet implemented")')

        lines.extend(
            [
                "    except HTTPException:",
                "        raise",
                "    except Exception as exc:",
                '        raise HTTPException(status_code=500, detail=str(exc)) from exc',
                "",
            ]
        )
        added_any = True

    if not added_any:
        lines.extend(
            [
                '@router.get("/", status_code=status.HTTP_200_OK)',
                "def list_items(service: Service = Depends(get_service)) -> list[ItemDTO]:",
                "    return service.list_items()",
                "",
                '@router.get("/{item_id}", status_code=status.HTTP_200_OK)',
                "def get_item(item_id: int, service: Service = Depends(get_service)) -> ItemDTO:",
                "    return service.get_item(item_id)",
                "",
                '@router.post("/", status_code=status.HTTP_201_CREATED)',
                "def create_item(payload: ItemDTO, service: Service = Depends(get_service)) -> ItemDTO:",
                "    return service.create_item(payload)",
                "",
            ]
        )

    lines.extend(
        [
            "app = FastAPI(title=\"Converted Spring API\")",
            "app.include_router(router)",
            "",
            "",
            "if __name__ == \"__main__\":",
            "    import uvicorn",
            "",
            '    uvicorn.run(app, host=\"0.0.0.0\", port=8000)',
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: JavaToPython <Arg1:input.java> <Arg2:output.py>")
        sys.exit(1)

    arg1 = Path(sys.argv[1])
    arg2 = Path(sys.argv[2])

    if not arg1.exists():
        print(f"Input file not found: {arg1}")
        sys.exit(1)

    java_code = arg1.read_text(encoding="utf-8")
    python_code = convert_java_to_fastapi(java_code)

    arg2.parent.mkdir(parents=True, exist_ok=True)
    arg2.write_text(python_code, encoding="utf-8")
    print(f"Converted: {arg1} -> {arg2}")


if __name__ == "__main__":
    main()
