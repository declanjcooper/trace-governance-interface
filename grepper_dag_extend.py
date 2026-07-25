"""
Chestnut TRACE: Comparative Governance Engine (v2.5)
Deterministic Structural Compiler with Matrix State Collapse & JSON-LD Graph Export

Dependencies:
    pip install streamlit lxml numpy pandas altair
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

# Tags representing transient wrappers to be stripped during path vector normalization
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
        """Constructs an orthogonal coordinate vector representing the node's topological position.

        Vector: v = [Depth, In_Table, In_Textbox, Is_Leaf]
        """
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
    """Observation Operator (R) that projects structural coordinate vector v_node

    into discrete semantic states via matrix transformation and Softmax evaluation.
    """

    STATES: List[str] = ["Native_Narrative", "Native_Tabular", "Quarantined"]

    def __init__(self) -> None:
        # Basis projection matrix R:
        # Maps [Depth, In_Table, In_Textbox, Is_Leaf] -> [Narrative, Tabular, Quarantined]
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
        """Performs state collapse on the node vector.

        Returns:
            Tuple[str, float]: (Assigned_State, Confidence_Score)
        """
        v: np.ndarray = node.get_coordinate_vector()
        projections: np.ndarray = np.dot(self.R, v)

        # Softmax normalization for numerical stability and probability calculation
        exp_proj: np.ndarray = np.exp(projections - np.max(projections))
        probabilities: np.ndarray = exp_proj / np.sum(exp_proj)

        max_idx: int = int(np.argmax(probabilities))
        confidence: float = float(probabilities[max_idx])

        if confidence < threshold or self.STATES[max_idx] == "Quarantined":
            return "Quarantined", confidence

        return self.STATES[max_idx], confidence


class StructuralCompiler:
    """Parses OOXML container parts into a Chestnut DAG and executes deterministic

    bifurcation using the Resolution Matrix operator.
    """

    def __init__(self, doc_file: Any, doc_name: str) -> None:
        self.doc_name: str = doc_name
        self.archive: zipfile.ZipFile = zipfile.ZipFile(doc_file)
        self.styles: Dict[str, str] = self._load_styles()
        self.resolution_matrix: ResolutionMatrix = ResolutionMatrix()
        self.node_counter: int = 0

    def _load_styles(self) -> Dict[str, str]:
        """Extracts style ID to human-readable style name mappings from word/styles.xml."""
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

    def _generate_node_id(self) -> str:
        """Generates a unique deterministic node identifier for graph references."""
        self.node_counter += 1
        return f"urn:trace:doc:{self.doc_name}:node:{self.node_counter:04d}"

    def build_dag(self, part_name: str = "word/document.xml") -> ChestnutNode:
        """Parses an OOXML XML part into a root ChestnutNode DAG."""
        with self.archive.open(part_name) as f:
            root: ET._Element = ET.parse(f).getroot()
            return self._traverse(root, current_path="", depth=0, parent_id=None)

    def _traverse(
        self,
        element: ET._Element,
        current_path: str,
        depth: int,
        parent_id: Optional[str],
        inherited_style: str = "Normal",
        in_table: bool = False,
        in_textbox: bool = False,
    ) -> ChestnutNode:
        tag: str = element.tag.split("}")[-1] if isinstance(element.tag, str) else ""
        node_id: str = self._generate_node_id()

        # Scope Context Updates
        if tag == "tbl":
            in_table = True
        elif tag == "txbxContent":
            in_textbox = True

        # Style Precedence Resolution
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

        # Construct raw path and normalize by stripping transient nodes
        raw_path: str = f"{current_path}/{tag}" if current_path else tag
        path_segments: List[str] = [
            seg for seg in raw_path.split("/") if seg not in TRANSIENT_TAGS
        ]
        normalized_path: str = "/".join(path_segments)

        # Extract text payload
        text: str = (
            element.text.strip()
            if element.text and element.text.strip()
            else ""
        )

        resolved_style: str = self.styles.get(node_style, node_style)
        node: ChestnutNode = ChestnutNode(
            node_id=node_id,
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

        # Build child DAG recursively
        for child in element:
            if isinstance(child.tag, str):
                node.children.append(
                    self._traverse(
                        child,
                        current_path=raw_path,
                        depth=depth + 1,
                        parent_id=node_id,
                        inherited_style=node_style,
                        in_table=in_table,
                        in_textbox=in_textbox,
                    )
                )

        return node

    def bifurcate(
        self, node: ChestnutNode, ledger: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Recursively traverses the DAG and executes state collapse on leaf text atoms."""
        if node.tag == "t" and node.text:
            state, confidence = self.resolution_matrix.collapse(node)

            record: Dict[str, Any] = {
                "NodeID": node.node_id,
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


# --- JSON-LD Knowledge Graph Exporter ---


def export_to_json_ld(
    file_name: str, validated_atoms: List[Dict[str, Any]]
) -> str:
    """Transforms TRACE validated atoms into a fully compliant JSON-LD Graph document

    preserving tree-DAG edge relations, topological coordinates, and provenance.
    """
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
    """Categorizes OOXML style names into visualization tiers."""
    s: str = style_name.lower()
    if "heading" in s or "title" in s:
        return "Heading"
    if "table" in s or "grid" in s:
        return "Table_Atom"
    if "normal" in s or "body" in s:
        return "Body_Text"
    return "Other"


def to_markdown(ledger_data: List[Dict[str, Any]]) -> str:
    """Transforms validated ledger atoms into structured Markdown."""
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
    st.sidebar.warning("Status: GRAPH RESOLUTION ENGINE (v2.5)")
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

    # Assign state safely
    st.session_state.processed_data = processed

    # Inspection View
    if st.session_state.processed_data:
        st.divider()
        selected_file: str = st.selectbox(
            "Select Document Ledger to Audit",
            list(st.session_state.processed_data.keys()),
        )

        file_ledger = st.session_state.processed_data[selected_file]
        validated_data = file_ledger["Validated"]
        quarantined_data = file_ledger["Quarantined"]

        # Executive Governance Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Validated Atoms", len(validated_data))
        m2.metric("Quarantined Atoms", len(quarantined_data))
        total_atoms: int = len(validated_data) + len(quarantined_data)
        governance_rate: float = (
            (len(validated_data) / total_atoms * 100) if total_atoms > 0 else 0.0
        )
        m3.metric("Governance Score", f"{governance_rate:.1f}%")

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
            if validated_data:
                df = pd.DataFrame(validated_data)
                df["Category"] = df["Style"].apply(get_semantic_rank)
                df["Atom_Index"] = df.index

                chart = (
                    alt.Chart(df)
                    .mark_circle(size=90)
                    .encode(
                        x=alt.X("Atom_Index:Q", title="Sequence Index"),
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
                        size=alt.Size("Confidence:Q", scale=alt.Scale(domain=[0.2, 1.0]), title="Collapse Confidence"),
                        tooltip=["NodeID", "Style", "Confidence", "TopologicalParity", "Path", "Content"],
                    )
                    .properties(height=380)
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No validated atoms available for Pulse Graph visualization.")

        with tab2:
            st.markdown(to_markdown(validated_data))

        with tab3:
            st.json(validated_data)

        with tab4:
            if quarantined_data:
                st.error(
                    f"Quarantine Containment: {len(quarantined_data)} anomalies isolated."
                )
                st.json(quarantined_data)
            else:
                st.success("Zero anomalies detected. Document fully compliant.")

        with tab5:
            json_ld_str: str = export_to_json_ld(selected_file, validated_data)

            st.subheader("Interoperable Knowledge Graph (JSON-LD)")
            st.caption(
                "Export structured RDF graph containing topological invariants, state collapse metrics, and explicit DAG parent-child pointers."
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
