import io
import json
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import streamlit as st

# ==========================================
# 1. CORE DATA STRUCTURES & STYLE ENGINE
# ==========================================

@dataclass
class StyleDisplacementVector:
    size_offset_pt: float = 0.0
    weight_delta: int = 0
    italic_delta: int = 0
    is_custom_style: bool = False

    @classmethod
    def from_style_name(cls, style_name: str) -> "StyleDisplacementVector":
        """Factory method to cleanly compute style displacement from style ID."""
        s_lower = style_name.lower()
        if "heading 1" in s_lower:
            return cls(size_offset_pt=9.0, weight_delta=1)
        elif "heading 2" in s_lower:
            return cls(size_offset_pt=5.0, weight_delta=1)
        elif "title" in s_lower:
            return cls(size_offset_pt=12.0, weight_delta=1, is_custom_style=True)
        return cls()

    def magnitude(self) -> float:
        return float(
            np.sqrt(
                (self.size_offset_pt / 2.0) ** 2
                + (self.weight_delta * 1.5) ** 2
                + (self.italic_delta * 1.0) ** 2
                + (2.0 if self.is_custom_style else 0.0)
            )
        )


@dataclass
class AtomNode:
    dewey_id: str
    text_content: str
    style_name: str
    displacement: StyleDisplacementVector
    provenance_status: str = "Unverified"
    children: List["AtomNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dewey_id": self.dewey_id,
            "text_content": self.text_content,
            "style_name": self.style_name,
            "displacement_magnitude": self.displacement.magnitude(),
            "provenance_status": self.provenance_status,
            "children": [c.to_dict() for c in self.children],
        }


# ==========================================
# 2. STRUCTURAL COMPILER & PARSER ENGINE
# ==========================================

class StructuralCompiler:
    def __init__(self, file_bytes: bytes, doc_name: str):
        self.file_bytes = file_bytes
        self.doc_name = doc_name
        self.archive = zipfile.ZipFile(io.BytesIO(file_bytes))

    def build_full_dag(self) -> List[AtomNode]:
        """Parses OOXML document structure concurrently with robust error handling."""
        # Find parts in the docx archive (e.g., word/document.xml or headers/footers)
        part_names = [name for name in self.archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
        
        root_nodes: List[AtomNode] = []
        
        def process_part(idx: int, part_name: str) -> List[AtomNode]:
            local_nodes: List[AtomNode] = []
            try:
                with self.archive.open(part_name) as f:
                    xml_bytes = f.read()
                    root_elem = ET.fromstring(xml_bytes)
                    
                    # Namespace-agnostic element scanning for paragraphs (w:p)
                    for p_idx, elem in enumerate(root_elem.iter(), start=1):
                        if elem.tag.endswith('p'):
                            text_runs = []
                            style_found = "Normal"
                            
                            for sub in elem.iter():
                                if sub.tag.endswith('t') and sub.text:
                                    text_runs.append(sub.text)
                                elif sub.tag.endswith('pStyle'):
                                    # Extract style attribute if available
                                    style_found = sub.attrib.get(list(sub.attrib.keys())[0], "Normal")
                                    
                            combined_text = "".join(text_runs).strip()
                            if combined_text:
                                dewey = f"{idx}.{p_idx}"
                                vector = StyleDisplacementVector.from_style_name(style_found)
                                local_nodes.append(
                                    AtomNode(
                                      dewey_id=dewey,
                                      text_content=combined_text,
                                      style_name=style_found,
                                      displacement=vector,
                                      provenance_status="Deterministic-Parsed"
                                    )
                                )
            except (KeyError, ET.ParseError, zipfile.BadZipFile) as e:
                print(f"Warning: Failed to parse part {part_name} in {self.doc_name}: {e}")
            return local_nodes

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(process_part, idx, name) for idx, name in enumerate(part_names, start=1)]
            for future in futures:
                root_nodes.extend(future.result())

        return root_nodes


# ==========================================
# 3. STREAMLIT INTERFACE & RUNTIME STATE
# ==========================================

def main():
    st.set_page_config(page_title="Chestnut TRACE v5.0.4", layout="wide")
    st.title("Project Chestnut: TRACE Governance Engine (v5.0.4)")
    st.markdown("Deterministic document structural verification and provenance ledger interface.")

    if "processed_data" not in st.session_state:
        st.session_state.processed_data = {}

    uploaded_file = st.file_uploader("Upload OOXML (.docx) Document", type=["docx"])

    if uploaded_file:
        file_name = uploaded_file.name
        if file_name not in st.session_state.processed_data:
            with st.spinner(f"Compiling topological DAG for {file_name}..."):
                compiler = StructuralCompiler(uploaded_file.getvalue(), file_name)
                nodes = compiler.build_full_dag()
                st.session_state.processed_data[file_name] = nodes

        nodes = st.session_state.processed_data[file_name]

        st.sidebar.subheader("Execution Metrics")
        st.sidebar.metric(label="Total Processed Atoms", value=len(nodes))
        
        tab1, tab2 = st.tabs(["Structural Ledger View", "JSON-LD Graph Export"])

        with tab1:
            st.subheader("Extracted Atom Nodes & Style Displacements")
            if not nodes:
                st.info("No text elements found or document layout structure is empty.")
            else:
                for node in nodes:
                    col1, col2, col3 = st.columns([2, 5, 2])
                    with col1:
                        st.code(node.dewey_id)
                    with col2:
                        st.text(node.text_content[:80] + ("..." if len(node.text_content) > 80 else ""))
                    with col3:
                        st.caption(f"Style: {node.style_name} (Mag: {node.displacement.magnitude():.2f})")

        with tab2:
            st.subheader("Interoperable JSON-LD Graph Representation")
            graph_output = {
                "@context": "https://schema.chestnut.local/context.jsonld",
                "@graph": [node.to_dict() for node in nodes]
            }
            st.json(graph_output, expanded=False)

if __name__ == "__main__":
    main()
