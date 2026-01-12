import json
from pathlib import Path

import streamlit as st
from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE_NAME = "tb.sv.j2"


def list_templates(template_dir: Path) -> list[str]:
    if not template_dir.exists():
        return []
    return sorted([p.name for p in template_dir.glob("*.j2")])


def jinja_env(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,  
        trim_blocks=True,
        lstrip_blocks=True,
    )


def clean_row(row: dict) -> dict:
    # normalize: ensure all expected keys exist and are strings
    keys = ["agent", "interface", "driver", "monitor", "sequencer", "sequence"]
    out = {k: (row.get(k) or "").strip() for k in keys}
    out["instance_name"] = (row.get("instance_name") or "").strip()
    return out


def build_context(tb_name: str, existing_rows: list[dict], new_rows: list[dict]) -> dict:
    tb_name = (tb_name or "").strip()

    existing_agents = []
    for r in existing_rows or []:
        r = clean_row(r)
        # if the row is basically blank, skip it
        if not any([r["instance_name"], r["agent"], r["interface"], r["driver"], r["monitor"], r["sequencer"], r["sequence"]]):
            continue
        # Map to your current template’s expected keys:
        # agent['name'] and agent['instance_name']
        existing_agents.append(
            {
                "kind": "existing",
                "name": r["agent"] or "agent",       
                "instance_name": r["instance_name"] or "agent_i",
                "interface": r["interface"],
                "driver": r["driver"],
                "monitor": r["monitor"],
                "sequencer": r["sequencer"],
                "sequence": r["sequence"],
            }
        )

    new_agents = []
    for r in new_rows or []:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        integrate = bool(r.get("integrate", True))
        inst = (r.get("instance_name") or "").strip()
        if not inst:
            inst = f"{name.lower()}_i"
        new_agents.append(
            {
                "kind": "new",
                "name": name,
                "instance_name": inst,
                "integrate": integrate,
            }
        )

    # Keep tb['agents'] as one list so your current template continues to work
    return {
        "tb": {
            "name": tb_name,
            "agents": existing_agents + new_agents,
            "existing_agents": existing_agents,
            "new_agents": new_agents,
        }
    }


def render(template_name: str, context: dict) -> str:
    env = jinja_env(TEMPLATE_DIR)
    tmpl = env.get_template(template_name)
    return tmpl.render(**context)


# ---------------- UI ----------------

st.set_page_config(page_title="TB Generator", layout="wide")
st.title("UVM TB Generator")

templates = list_templates(TEMPLATE_DIR)
if not templates:
    st.error(
        f"No templates found in: {TEMPLATE_DIR}\n\n"
        "Create a 'templates' folder next to app.py and put your .j2 file(s) there."
    )
    st.stop()

with st.sidebar:
    st.header("Template")
    template_name = st.selectbox(
        "Select template",
        templates,
        index=templates.index(DEFAULT_TEMPLATE_NAME) if DEFAULT_TEMPLATE_NAME in templates else 0,
    )
    st.caption(f"Loaded from: {TEMPLATE_DIR / template_name}")

st.subheader("Testbench")
tb_name = st.text_input("Name", value="")

st.divider()

# Existing Agents section
st.subheader("Existing Agent(s)")

if "existing_agents" not in st.session_state:
    st.session_state.existing_agents = [
        {
            "instance_name": "",
            "agent": "",
            "interface": "",
            "driver": "",
            "monitor": "",
            "sequencer": "",
            "sequence": "",
        }
    ]

existing_rows = st.data_editor(
    st.session_state.existing_agents,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "instance_name": st.column_config.TextColumn("Agent Instance"),
        "agent": st.column_config.TextColumn("Agent"),
        "interface": st.column_config.TextColumn("Interface"),
        "driver": st.column_config.TextColumn("Driver"),
        "monitor": st.column_config.TextColumn("Monitor"),
        "sequencer": st.column_config.TextColumn("Sequencer"),
        "sequence": st.column_config.TextColumn("Sequence"),
    },
    key="existing_agents_editor",
)

st.divider()

# New Agents section
st.subheader("New Agent(s)")

if "new_agents" not in st.session_state:
    st.session_state.new_agents = [
        {"name": "", "instance_name": "", "integrate": True}
    ]

new_rows = st.data_editor(
    st.session_state.new_agents,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "name": st.column_config.TextColumn("Name"),
        "instance_name": st.column_config.TextColumn("Instance (optional)"),
        "integrate": st.column_config.CheckboxColumn("Integrate in tb above", default=True),
    },
    key="new_agents_editor",
)

context = build_context(tb_name, existing_rows, new_rows)

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.subheader("JSON")
    json_text = json.dumps(context, indent=2)
    st.code(json_text, language="json")
    st.download_button(
        "Download JSON",
        data=json_text.encode("utf-8"),
        file_name="tb_inputs.json",
        mime="application/json",
        use_container_width=True,
    )

with col_b:
    st.subheader("Rendered Output (.sv)")
    if not tb_name.strip():
        st.info("Enter a testbench name to render.")
    else:
        try:
            sv_text = render(template_name, context)
            st.code(sv_text, language="systemverilog")

            out_name = f"{context['tb']['name']}_tb.sv"
            st.download_button(
                "Download .sv",
                data=sv_text.encode("utf-8"),
                file_name=out_name,
                mime="text/plain",
                use_container_width=True,
            )
        except Exception as e:
            st.error("Render failed (template referenced a missing key or has a syntax error).")
            st.code(str(e), language="text")

st.caption("Template is loaded from disk. Inputs are stored as JSON and passed into Jinja2 with StrictUndefined.")
