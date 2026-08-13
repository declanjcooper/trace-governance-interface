"""
Chestnut TRACE: Comparative Governance Engine (v3.1 - Dewey Topological Edition)
Adaptive Multi-Persona Governance Engine with Parameterized Node Coalescing,
Hierarchical Dewey Coordinate Generator, & Graph Export
"""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import altair as alt
import lxml.etree as ET
import numpy as np
import pandas as pd
import streamlit as st

# WordprocessingML Namespace Constant
NS_W: str = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MAP: Dict[str, str] = {"w": NS_W}

TRANSIENT_TAGS: set[str] = {
    "smartTag",
    "hyperlink",
    "bookmarkStart",
    "bookmarkEnd",
    "proofErr",
    "permStart",
    "permEnd",
}


@dataclass
class ChestnutNode:
    """DAG Node representing an OOXML structural element and its topological metadata."""

    node_id: str
    dewey_id: str
    tag: str
    path: str
    normalized_path: str
    text: str = ""
    style_id: str = "Normal"
    depth: int = 0
    in_table: bool = False
    in_textbox: bool = False
    parent_id: Optional[str] = None
    children: List["ChestnutNode"] = field(default_factory=list)

    def get_coordinate_vector(self) -> np.ndarray:
        """Constructs a deterministic coordinate vector anchored by Dewey depth."""
        is_leaf: float = 1.0 if not self.children else 0.0
        return np.array(
            [
                float(self.depth),
                1.0 if self.in_table else 0.0,
                1.0 if self.in_textbox else 0.0,
                is_leaf,
            ],
            dtype=np.float64,
        )


class ResolutionMatrix:
    """Observation Operator (R) that projects coordinate vector v_node into semantic states."""

    STATES: List[str] = ["Native_Narrative", "Native_Tabular", "Quarantined"]

    def __init__(self) -> None:
        self.R: np.ndarray = np.array(
            [
                [-0.05, -0.80, 0.50, 0.80],   # Native_Narrative Weight Vector
                [0.10, 1.50, -0.50, 0.80],    # Native_Tabular Weight Vector
                [0.00, -0.20, -0.20, -0.50],  # Anomaly Baseline
            ],
            dtype=np.float64,
        )

    def collapse(
        self, node: ChestnutNode, threshold: float = 0.20
    ) -> Tuple[str, float]:
        v: np.ndarray = node.get_coordinate_vector()
        projections: np.ndarray = np.dot(self.R, v)

        exp_proj: np.ndarray = np.exp(projections - np.max(projections))
        probabilities: np.ndarray = exp_proj / np.sum(exp_proj)

        max_idx: int = int(np.argmax(probabilities))
        confidence: float = float(probabilities[max_idx])

        if confidence < threshold or self.STATES[max_idx] == "Quarantined":
            return "Quarantined", confidence

        return self.STATES[max_idx], confidence


class StructuralCompiler:
    """Parses OOXML container parts into a Chestnut DAG using explicit Dewey Decimal indexing."""

    def __init__(self, doc_file: Any, doc_name: str) -> None:
        self.doc_name: str = doc_name
        self.archive: zipfile.ZipFile = zipfile.ZipFile(doc_file)
        self.styles: Dict[str, str] = self._load_styles()
        self.resolution_matrix: ResolutionMatrix = ResolutionMatrix()

    def _load_styles(self) -> Dict[str, str]:
        styles: Dict[str, str] = {}
        try:
            with self.archive.open("word/styles.xml") as f:
                root: ET._Element = ET.parse(f).getroot()
                for style in root.findall(".//w:style", NS_MAP):
                    s_id: Optional[str] = style.get(f"{{{NS_W}}}styleId")
                    name_elem: Optional[ET._Element] = style.find(".//w:name", NS_MAP)
                    if s_id:
                        styles[s_id] = (
                            name_elem.get(f"{{{NS_W}}}val")
                            if name_elem is not None
                            else s_id
                        )
        except (KeyError, ET.ParseError):
            pass
        return styles

    def _generate_node_id(self, dewey_id: str) -> str:
        return f"urn:trace:doc:{self.doc_name}:node:dewey:{dewey_id}"

    def build_dag(self, part_name: str = "word/document.xml") -> ChestnutNode:
        with self.archive.open(part_name) as f:
            root: ET._Element = ET.parse(f).getroot()
            # Root node initiates Dewey coordinate "1"
            return self._traverse(
                root, current_path="", depth=0, parent_id=None, dewey_id="1"
            )

    def _traverse(
        self,
        element: ET._Element,
        current_path: str,
        depth: int,
        parent_id: Optional[str],
        dewey_id: str,
        inherited_style: str = "Normal",
        in_table: bool = False,
        in_textbox: bool = False,
    ) -> ChestnutNode:
        tag: str = element.tag.split("}")[-1] if isinstance(element.tag, str) else ""
        node_id: str = self._generate_node_id(dewey_id)

        if tag == "tbl":
            in_table = True
        elif tag == "txbxContent":
            in_textbox = True

        node_style: str = inherited_style
        if tag == "p":
            p_style: Optional[ET._Element] = element.find("w:pPr/w:pStyle", NS_MAP)
            if p_style is not None:
                val: Optional[str] = p_style.get(f"{{{NS_W}}}val")
                if val:
                    node_style = val
        elif tag == "r":
            r_style: Optional[ET._Element] = element.find("w:rPr/w:rStyle", NS_MAP)
            if r_style is not None:
                val: Optional[str] = r_style.get(f"{{{NS_W}}}val")
                if val:
                    node_style = val

        raw_path: str = f"{current_path}/{tag}" if current_path else tag
        path_segments: List[str] = [
            seg for seg in raw_path.split("/") if seg not in TRANSIENT_TAGS
        ]
        normalized_path: str = "/".join(path_segments)

        text: str = (
            element.text.strip()
            if element.text and element.text.strip()
            else ""
        )

        resolved_style: str = self.styles.get(node_style, node_style)
        node: ChestnutNode = ChestnutNode(
            node_id=node_id,
            dewey_id=dewey_id,
            tag=tag,
            path=raw_path,
            normalized_path=normalized_path,
            text=text,
            style_id=resolved_style,
            depth=depth,
            in_table=in_table,
            in_textbox=in_textbox,
            parent_id=parent_id,
        )

        # Child branch index generation for Dewey hierarchy
        child_counter = 1
        for child in element:
            if isinstance(child.tag, str):
                child_dewey = f"{dewey_id}.{child_counter}"
                node.children.append(
                    self._traverse(
                        child,
                        current_path=raw_path,
                        depth=depth + 1,
                        parent_id=node_id,
                        dewey_id=child_dewey,
                        inherited_style=node_style,
                        in_table=in_table,
                        in_textbox=in_textbox,
                    )
                )
                child_counter += 1

        return node

    def bifurcate(
        self, node: ChestnutNode, ledger: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        if node.tag == "t" and node.text:
            state, confidence = self.resolution_matrix.collapse(node)

            record: Dict[str, Any] = {
                "NodeID": node.node_id,
                "DeweyID": node.dewey_id,
                "DeweyDepth": node.depth,
                "ParentID": node.parent_id,
                "State": state,
                "Confidence": round(confidence, 4),
                "Style": node.style_id,
                "Path": node.normalized_path,
                "Content": node.text,
                "TopologicalParity": -1 if node.in_table or node.in_textbox else 1,
            }

            if state != "Quarantined":
                ledger["Validated"].append(record)
            else:
                ledger["Quarantined"].append(record)

        for child in node.children:
            self.bifurcate(child, ledger)


# --- Node Coalescing Transformation ---


def coalesce_atoms(
    atoms: List[Dict[str, Any]], strict_parent_matching: bool = True
) -> List[Dict[str, Any]]:
    """Coalesces adjacent sibling ChestnutAtoms while preserving Dewey topological boundaries."""
    if not atoms:
        return []

    coalesced: List[Dict[str, Any]] = []
    current_node = dict(atoms[0])

    for next_node in atoms[1:]:
        same_path = current_node.get("Path") == next_node.get("Path")
        same_style = current_node.get("Style") == next_node.get("Style")

        if strict_parent_matching:
            same_scope = current_node.get("ParentID") == next_node.get("ParentID")
        else:
            same_scope = same_path and same_style

        if same_path and same_style and same_scope:
            text1 = current_node.get("Content", "")
            text2 = next_node.get("Content", "")

            # Preserve range interval for Dewey coordinates on coalescing
            dewey_start = current_node["DeweyID"].split("-")[0]
            dewey_end = next_node["DeweyID"].split("-")[-1]
            current_node["DeweyID"] = f"{dewey_start}-{dewey_end}"

            if text2 in [".", ",", ";", ":", "s", "s.", " "]:
                current_node["Content"] = f"{text1}{text2}"
            else:
                current_node["Content"] = f"{text1} {text2}".strip()
        else:
            coalesced.append(current_node)
            current_node = dict(next_node)

    coalesced.append(current_node)
    return coalesced


# --- JSON-LD Exporter ---


def export_to_json_ld(
    file_name: str, validated_atoms: List[Dict[str, Any]]
) -> str:
    graph_nodes: List[Dict[str, Any]] = []

    for atom in validated_atoms:
        schema_type: str = (
            "DigitalDocumentSection"
            if "Heading" in atom["Style"]
            else "TextDigitalDocument"
        )

        ld_node: Dict[str, Any] = {
            "@id": atom["NodeID"],
            "@type": [schema_type, "trace:ChestnutAtom"],
            "schema:name": atom["Style"],
            "schema:text": atom["Content"],
            "trace:deweyCoordinate": atom["DeweyID"],
            "trace:deweyDepth": atom["DeweyDepth"],
            "trace:normalizedPath": atom["Path"],
            "trace:collapseConfidence": atom["Confidence"],
            "trace:semanticState": atom["State"],
            "trace:topologicalParity": atom["TopologicalParity"],
        }

        if atom.get("ParentID"):
            ld_node["trace:hasParent"] = {"@id": atom["ParentID"]}

        graph_nodes.append(ld_node)

    json_ld_document: Dict[str, Any] = {
        "@context": {
            "schema": "https://schema.org/",
            "trace": "https://trace.chestnut.org/schema/v2/",
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@id": f"urn:trace:doc:{file_name}",
        "@type": ["schema:DigitalDocument", "prov:Entity"],
        "schema:name": file_name,
        "trace:governanceStatus": "Validated",
        "@graph": graph_nodes,
    }

    return json.dumps(json_ld_document, indent=2)


# --- Helper Methods ---


def get_semantic_rank(style_name: str) -> str:
    s: str = style_name.lower()
    if "heading" in s or "title" in s:
        return "Heading"
    if "table" in s or "grid" in s:
        return "Table_Atom"
    if "normal" in s or "body" in s:
        return "Body_Text"
    return "Other"


def to_markdown(ledger_data: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in ledger_data:
        style: str = item["Style"].lower()
        content: str = item["Content"]
        if "heading 1" in style:
            lines.append(f"# {content}\n")
        elif "heading 2" in style:
            lines.append(f"## {content}\n")
        elif "heading 3" in style:
            lines.append(f"### {content}\n")
        else:
            lines.append(f"{content}\n")
    return "\n".join(lines)


# --- Streamlit Engine Application ---


def main() -> None:
    st.set_page_config(layout="wide", page_title="Chestnut TRACE Engine")

    # --- Sidebar Persona & View Controls ---
    st.sidebar.title("TRACE Control Surface")

    persona_mode = st.sidebar.selectbox(
        "User Profile / Preset View",
        [
            "Knowledge Worker (Reader Mode)",
            "System Auditor (Lossless Mode)",
            "Developer (Graph & Vector Mode)",
        ],
    )

    st.sidebar.divider()
    st.sidebar.subheader("Granular View Toggles")

    # Dynamic toggle defaults based on selected persona
    default_coalesce = persona_mode == "Knowledge Worker (Reader Mode)"
    default_show_vector = persona_mode == "Developer (Graph & Vector Mode)"
    default_show_ids = persona_mode != "Knowledge Worker (Reader Mode)"
    default_strict_parent = persona_mode == "System Auditor (Lossless Mode)"

    enable_coalesce = st.sidebar.toggle(
        "Enable Node Coalescing (Consolidate Runs)", value=default_coalesce
    )
    strict_parent_matching = st.sidebar.toggle(
        "Strict Parent Container Matching", value=default_strict_parent
    )
    show_vector_details = st.sidebar.toggle(
        "Show Vector Coordinates & Parity", value=default_show_vector
    )
    show_node_ids = st.sidebar.toggle(
        "Show Node IDs & Parent Links", value=default_show_ids
    )

    st.title("Chestnut TRACE: Comparative Governance Engine")

    mode: str = st.radio(
        "Audit Mode", ["Single SOP Audit", "Template vs. Variant"], horizontal=True
    )

    processed: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    if mode == "Single SOP Audit":
        uploaded_files = st.file_uploader(
            "Upload SOPs",
            type=["docx"],
            accept_multiple_files=True,
            key="single_upload",
        )
        if uploaded_files:
            for file in uploaded_files:
                compiler = StructuralCompiler(file, file.name)
                root = compiler.build_dag("word/document.xml")
                ledger: Dict[str, List[Dict[str, Any]]] = {
                    "Validated": [],
                    "Quarantined": [],
                }
                compiler.bifurcate(root, ledger)
                processed[file.name] = ledger

    elif mode == "Template vs. Variant":
        col1, col2 = st.columns(2)
        ref_file = col1.file_uploader(
            "Master Template", type=["docx"], key="ref_upload"
        )
        var_files = col2.file_uploader(
            "Variants", type=["docx"], accept_multiple_files=True, key="var_upload"
        )

        if ref_file and var_files:
            for file in [ref_file] + var_files:
                compiler = StructuralCompiler(file, file.name)
                root = compiler.build_dag("word/document.xml")
                ledger: Dict[str, List[Dict[str, Any]]] = {
                    "Validated": [],
                    "Quarantined": [],
                }
                compiler.bifurcate(root, ledger)
                processed[file.name] = ledger

    st.session_state.processed_data = processed

    # Inspection View
    if st.session_state.processed_data:
        st.divider()
        selected_file: str = st.selectbox(
            "Select Document Ledger to Audit",
            list(st.session_state.processed_data.keys()),
        )

        file_ledger = st.session_state.processed_data[selected_file]
        raw_validated = file_ledger["Validated"]
        quarantined_data = file_ledger["Quarantined"]

        # Apply Coalescing based on toggle configuration
        display_validated = (
            coalesce_atoms(
                raw_validated, strict_parent_matching=strict_parent_matching
            )
            if enable_coalesce
            else raw_validated
        )

        # Executive Governance Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Display Atoms", len(display_validated))
        m2.metric("Raw Structural Atoms", len(raw_validated))
        m3.metric("Quarantined Atoms", len(quarantined_data))
        total_atoms: int = len(raw_validated) + len(quarantined_data)
        governance_rate: float = (
            (len(raw_validated) / total_atoms * 100) if total_atoms > 0 else 0.0
        )
        m4.metric("Governance Score", f"{governance_rate:.1f}%")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "Pulse Graph",
                "Markdown Preview",
                "Validated Ledger",
                "Quarantine Audit",
                "Graph / JSON-LD Export",
            ]
        )

        with tab1:
            if display_validated:
                df = pd.DataFrame(display_validated)
                df["Category"] = df["Style"].apply(get_semantic_rank)

                # Topological Pulse Plot mapped to Dewey Coordinate Sequence
                chart = (
                    alt.Chart(df)
                    .mark_circle(size=95)
                    .encode(
                        x=alt.X(
                            "DeweyID:N",
                            sort=None,
                            title="Dewey Coordinate Topology Sequence",
                        ),
                        y=alt.Y(
                            "Category:N",
                            sort=[
                                "Heading",
                                "Body_Text",
                                "Table_Atom",
                                "Other",
                            ],
                            title="Semantic Category",
                        ),
                        color=alt.Color("Category:N", legend=alt.Legend(title="Category")),
                        size=alt.Size(
                            "Confidence:Q",
                            scale=alt.Scale(domain=[0.2, 1.0]),
                            title="Collapse Confidence",
                        ),
                        tooltip=[
                            "NodeID",
                            "DeweyID",
                            "DeweyDepth",
                            "Style",
                            "Confidence",
                            "TopologicalParity",
                            "Path",
                            "Content",
                        ],
                    )
                    .properties(height=380)
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No validated atoms available for Pulse Graph visualization.")

        with tab2:
            st.markdown(to_markdown(display_validated))

        with tab3:
            # Filter ledger columns based on toggles
            df_ledger = pd.DataFrame(display_validated)
            cols_to_show = ["Content", "Style"]

            if show_node_ids:
                cols_to_show = ["DeweyID", "NodeID", "ParentID"] + cols_to_show
            if show_vector_details:
                cols_to_show += ["DeweyDepth", "Path", "TopologicalParity", "Confidence", "State"]

            st.dataframe(df_ledger[cols_to_show], use_container_width=True)

        with tab4:
            if quarantined_data:
                st.error(
                    f"Quarantine Containment: {len(quarantined_data)} anomalies isolated."
                )
                st.json(quarantined_data)
            else:
                st.success("Zero anomalies detected. Document fully compliant.")

        with tab5:
            json_ld_str: str = export_to_json_ld(selected_file, display_validated)

            st.subheader("Interoperable Knowledge Graph (JSON-LD)")
            st.caption(
                "Export structured RDF graph containing Dewey coordinates, topological invariants, state collapse metrics, and explicit DAG parent-child pointers."
            )

            st.download_button(
                label="Download JSON-LD Graph Document",
                data=json_ld_str,
                file_name=f"{selected_file}_trace_graph.jsonld",
                mime="application/ld+json",
            )

            st.json(json_ld_str)


if __name__ == "__main__":
    main()
