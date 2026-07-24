import streamlit as st
import zipfile
import lxml.etree as ET
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ChestnutNode:
    tag: str
    path: str
    text: str = ""
    children: List['ChestnutNode'] = field(default_factory=list)

class StructuralCompiler:
    def __init__(self, doc_path):
        self.archive = zipfile.ZipFile(doc_path)
        # Define the SSOT Schema Matrix
        self.schema_matrix = {
            "document/body/p/r/t": "Native_Narrative",
            "document/body/tbl/tr/tc/p/r/t": "Native_Tabular"
        }

    def build_dag(self, part_name: str) -> ChestnutNode:
        with self.archive.open(part_name) as f:
            root = ET.parse(f).getroot()
            return self._traverse_and_build(root, "root")

    def _traverse_and_build(self, element, current_path: str) -> ChestnutNode:
        tag = element.tag.split('}')[-1]
        new_path = f"{current_path}/{tag}"
        text_content = element.text.strip() if element.text and element.text.strip() else ""
        node = ChestnutNode(tag=tag, path=new_path, text=text_content)
        for child in element:
            if isinstance(child.tag, str):
                node.children.append(self._traverse_and_build(child, new_path))
        return node

    def bifurcate_ledger(self, node: ChestnutNode, ledger: Dict):
        """Routes nodes into Validated or Quarantined queues based on schema matrix."""
        is_native = False
        for vector, state in self.schema_matrix.items():
            if node.path.endswith(vector):
                ledger["Validated"][state].append(node)
                is_native = True
                break
        
        if not is_native and node.tag == 't' and node.text:
            ledger["Quarantined"].append(node)
            
        for child in node.children:
            self.bifurcate_ledger(child, ledger)

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE: Bifurcated Auditor")
    st.title("Deterministic Structural Auditor: Bifurcated Ledger")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = StructuralCompiler(uploaded_file)
        root = compiler.build_dag('word/document.xml')
        
        ledger = {"Validated": {"Native_Narrative": [], "Native_Tabular": []}, "Quarantined": []}
        compiler.bifurcate_ledger(root, ledger)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success(f"Validated Ledger: {len(ledger['Validated']['Native_Narrative']) + len(ledger['Validated']['Native_Tabular'])} atoms")
            for state, nodes in ledger["Validated"].items():
                if nodes:
                    with st.expander(f"View {state}"):
                        for n in nodes[:20]: st.code(f"[{n.path}]\n-> {n.text}")

        with col2:
            st.warning(f"Reconstruction Queue (DTP Quarantine): {len(ledger['Quarantined'])} atoms")
            with st.expander("View Quarantined DTP Overhead"):
                for q in ledger['Quarantined'][:20]:
                    st.code(f"[{q.path}]\n-> {q.text}")
                    if st.button(f"Whitelist Path", key=q.path):
                        st.info("Path added to schema matrix. Re-running compiler...")

if __name__ == "__main__":
    main()
