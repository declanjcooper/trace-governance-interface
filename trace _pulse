from dataclasses import dataclass, field
import hashlib
import json
from typing import Dict, List
import zipfile

import altair as alt
import lxml.etree as ET
import pandas as pd
import streamlit as st


@dataclass
class ChestnutNode:
    tag: str
    path: str
    text: str = ""
    style_id: str = "Normal"
    children: List["ChestnutNode"] = field(default_factory=list)


class StructuralCompiler:

    def __init__(self, doc_path):
        self.archive = zipfile.ZipFile(doc_path)
        self.ns = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        }
        self.styles = self._load_styles()
        self.schema_matrix = {
            "document/body/p/r/t": "Native_Narrative",
            "document/body/tbl/tr/tc/p/r/t": "Native_Tabular",
            "txbxContent/p/r/t": "Native_Narrative",
        }

    def _load_styles(self):
        styles = {}
        try:
            with self.archive.open("word/styles.xml") as f:
                root = ET.parse(f).getroot()
                for style in root.findall(".//w:style", self.ns):
                    s_id = style.get(
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}styleId"
                    )
                    name = style.find(".//w:name", self.ns)
                    styles[s_id] = (
                        name.get(
                            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
                        )
                        if name is not None
                        else s_id
                    )
        except Exception:
            pass
        return styles

    def build_dag(self, part_name: str) -> ChestnutNode:
        with self.archive.open(part_name) as f:
            root = ET.parse(f).getroot()
            return self._traverse_and_build(root, "root")

    def _traverse_and_build(
        self, element, current_path: str, current_style: str = "Normal"
    ) -> ChestnutNode:
        tag = element.tag.split("}")[-1]
        new_path = f"{current_path}/{tag}"
        if tag == "p":
            pPr = element.find("w:pPr", self.ns)
            if pPr is not None:
                pStyle = pPr.find("w:pStyle", self.ns)
                if pStyle is not None:
                    current_style = pStyle.get(
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
                    )
        text = (
            element.text.strip()
            if element.text and element.text.strip()
            else ""
        )
        node = ChestnutNode(
            tag=tag,
            path=new_path,
            text=text,
            style_id=self.styles.get(current_style, current_style),
        )
        for child in element:
            if isinstance(child.tag, str):
                node.children.append(
                    self._traverse_and_build(child, new_path, current_style)
                )
        return node

    def bifurcate(self, node: ChestnutNode, ledger: Dict):
        is_native = False
        for vector, state in self.schema_matrix.items():
            if node.path.endswith(vector):
                ledger["Validated"].append(
                    {
                        "State": state,
                        "Style": node.style_id,
                        "Path": node.path,
                        "Content": node.text,
                    }
                )
                is_native = True
                break
        if not is_native and node.tag == "t" and node.text:
            ledger["Quarantined"].append(
                {"Path": node.path, "Content": node.text}
            )
        for child in node.children:
            self.bifurcate(child, ledger)


def get_semantic_rank(style_name: str) -> str:
    s = style_name.lower()
    if "heading" in s:
        return "Heading"
    if "table" in s:
        return "Table_Atom"
    if "normal" in s:
        return "Body_Text"
    return "Other"


def to_markdown(ledger_data: List[Dict]) -> str:
    md = ""
    for item in ledger_data:
        if "heading" in item["Style"].lower():
            md += f"### {item['Content']}\n\n"
        else:
            md += f"{item['Content']}\n\n"
    return md


def generate_ledger_manifest_hash(validated_ledger: List[Dict]) -> str:
    """Computes a single deterministic SHA-256 signature for all validated atoms."""
    canonical_bytes = json.dumps(validated_ledger, sort_keys=True).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical_bytes).hexdigest()


def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE")
    st.sidebar.warning("Status: EVALUATIVE ENGINE (v1.1)")
    st.title("Chestnut TRACE: Comparative Governance Engine")

    mode = st.radio(
        "Audit Mode", ["Single SOP Audit", "Template vs. Variant"]
    )

    # Store processed data in session state for tab access
    if "processed_data" not in st.session_state:
        st.session_state.processed_data = {}
    if "quarantined_data" not in st.session_state:
        st.session_state.quarantined_data = {}

    if mode == "Single SOP Audit":
        uploaded_files = st.file_uploader(
            "Upload SOPs", type=["docx"], accept_multiple_files=True
        )
        if uploaded_files:
            for file in uploaded_files:
                compiler = StructuralCompiler(file)
                root = compiler.build_dag("word/document.xml")
                ledger = {"Validated": [], "Quarantined": []}
                compiler.bifurcate(root, ledger)
                st.session_state.processed_data[file.name] = ledger["Validated"]
                st.session_state.quarantined_data[file.name] = ledger[
                    "Quarantined"
                ]

    elif mode == "Template vs. Variant":
        col1, col2 = st.columns(2)
        ref_file = col1.file_uploader("Master Template", type=["docx"])
        var_files = col2.file_uploader(
            "Variants", type=["docx"], accept_multiple_files=True
        )
        if ref_file and var_files:
            for f in [ref_file] + var_files:
                compiler = StructuralCompiler(f)
                root = compiler.build_dag("word/document.xml")
                ledger = {"Validated": [], "Quarantined": []}
                compiler.bifurcate(root, ledger)
                st.session_state.processed_data[f.name] = ledger["Validated"]
                st.session_state.quarantined_data[f.name] = ledger[
                    "Quarantined"
                ]

    # Drill-Down Logic
    if st.session_state.processed_data:
        selected = st.selectbox(
            "Drill down into specific file",
            list(st.session_state.processed_data.keys()),
        )
        data = st.session_state.processed_data[selected]
        quarantined = st.session_state.quarantined_data.get(selected, [])

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Pulse Graph", "Markdown", "JSON", "DDM Matrix Stamp"]
        )

        with tab1:
            df = pd.DataFrame(data)
            if not df.empty:
                df["Category"] = df["Style"].apply(get_semantic_rank)
                chart = (
                    alt.Chart(df.reset_index())
                    .mark_circle(size=80)
                    .encode(
                        x="index",
                        y=alt.Y(
                            "Category",
                            sort=[
                                "Heading",
                                "Body_Text",
                                "Table_Atom",
                                "Other",
                            ],
                        ),
                        color="Category",
                        tooltip=["Style", "Content"],
                    )
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No validated atoms found to render Pulse Graph.")

        with tab2:
            st.markdown(to_markdown(data))

        with tab3:
            st.json(data)

        with tab4:
            manifest_hash = generate_ledger_manifest_hash(data)
            st.markdown("### Document Determinism Matrix (DDM) Anchor")
            st.code(
                f"Root Validated Manifest Hash (SHA-256):\n{manifest_hash}",
                language="text",
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Validated Atoms", len(data))
            with c2:
                st.metric("Quarantined Atoms", len(quarantined))
            with c3:
                integrity_status = (
                    "PASSED" if len(quarantined) == 0 else "ANOMALY DETECTED"
                )
                st.metric("Schema Integrity", integrity_status)

            if quarantined:
                with st.expander("View Quarantined Nodes"):
                    st.json(quarantined)


if __name__ == "__main__":
    main()
