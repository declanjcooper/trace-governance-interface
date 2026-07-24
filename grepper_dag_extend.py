import streamlit as st
import zipfile
import lxml.etree as ET
from dataclasses import dataclass, field
from typing import List, Set, Tuple

@dataclass
class ChestnutNode:
    tag: str
    path: str
    text: str = ""
    children: List['ChestnutNode'] = field(default_factory=list)

class StructuralAuditor:
    def __init__(self, doc_path):
        self.archive = zipfile.ZipFile(doc_path)

    def build_dag(self, part_name: str) -> ChestnutNode:
        """Parses the XML into a stateful DAG, capturing the absolute vector of every atom."""
        with self.archive.open(part_name) as f:
            root = ET.parse(f).getroot()
            return self._traverse_and_build(root, "root")

    def _traverse_and_build(self, element, current_path: str) -> ChestnutNode:
        # Strip the namespace to build a clean topological vector
        tag = element.tag.split('}')[-1]
        new_path = f"{current_path}/{tag}"
        text_content = element.text.strip() if element.text and element.text.strip() else ""

        node = ChestnutNode(tag=tag, path=new_path, text=text_content)

        for child in element:
            if isinstance(child.tag, str):
                node.children.append(self._traverse_and_build(child, new_path))
                
        return node

class TraceValidator:
    def __init__(self, required_vectors: Set[str]):
        # The SSOT rule set. This dictates where data is legally allowed to exist.
        self.required_vectors = required_vectors

    def evaluate(self, node: ChestnutNode) -> Tuple[List[ChestnutNode], List[ChestnutNode]]:
        """Splits nodes into compliant atoms and structural violations based on lineage."""
        valid = []
        violations = []
        self._check_node(node, valid, violations)
        return valid, violations

    def _check_node(self, node: ChestnutNode, valid: List, violations: List):
        # We target the lowest-level data atoms (text nodes) for compliance
        if node.tag == 't':
            # Check if the node's vector path conforms to the SSOT schema
            if any(node.path.endswith(req) for req in self.required_vectors):
                valid.append(node)
            else:
                violations.append(node)

        # Continue traversing the DAG
        for child in node.children:
            self._check_node(child, valid, violations)

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE: Vector Auditor")
    st.title("Deterministic Structural Auditor")
    st.markdown("Replaces superficial LLM string-matching with rigorous DAG vector validation.")
    
    uploaded_file = st.file_uploader("Upload .docx for Structural Audit", type=["docx"])
    
    if uploaded_file:
        try:
            auditor = StructuralAuditor(uploaded_file)
            root_node = auditor.build_dag('word/document.xml')
            
            # Define the baseline SSOT vectors for compliance.
            # In TRACE, a valid text atom must live exactly at this lineage.
            ssot_vectors = {"body/p/r/t"}
            validator = TraceValidator(required_vectors=ssot_vectors)
            
            st.write("DAG instantiated in memory. Ready for topological evaluation.")
            
            if st.button("Audit DAG Integrity"):
                valid_nodes, violations = validator.evaluate(root_node)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success(f"Compliant Atoms Found: {len(valid_nodes)}")
                    with st.expander("View Compliant Lineages"):
                        # Slicing to first 50 to prevent browser UI lockup on massive files
                        for n in valid_nodes[:50]: 
                            st.code(f"[{n.path}]\n-> {n.text}")
                            
                with col2:
                    if violations:
                        st.error(f"Structural Violations Detected: {len(violations)}")
                        with st.expander("View Orphaned/Violating Lineages"):
                            for v in violations[:50]:
                                st.code(f"[{v.path}]\n-> {v.text}")
                    else:
                        st.success("Zero lineage violations detected.")
                        
        except Exception as e:
            st.error(f"Audit Pipeline Failure: {e}")

if __name__ == "__main__":
    main()
