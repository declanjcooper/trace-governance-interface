import streamlit as st
import zipfile
import lxml.etree as ET
from dataclasses import dataclass, field
from typing import List, Dict
import pandas as pd

@dataclass
class ChestnutNode:
    tag: str
    path: str
    text: str = ""
    children: List['ChestnutNode'] = field(default_factory=list)

class StructuralCompiler:
    def __init__(self):
        # The SSOT Schema Matrix
        self.schema_matrix = {
            "document/body/p/r/t": "Native_Narrative",
            "document/body/tbl/tr/tc/p/r/t": "Native_Tabular"
        }

    def build_dag(self, doc_path: str, part_name: str) -> ChestnutNode:
        with zipfile.ZipFile(doc_path) as archive:
            with archive.open(part_name) as f:
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

    def bifurcate(self, node: ChestnutNode, ledger: Dict):
        is_native = False
        for vector, state in self.schema_matrix.items():
            if node.path.endswith(vector):
                ledger["Validated"].append({"State": state, "Path": node.path, "Content": node.text})
                is_native = True
                break
        
        if not is_native and node.tag == 't' and node.text:
            ledger["Quarantined"].append({"Path": node.path, "Content": node.text})
            
        for child in node.children:
            self.bifurcate(child, ledger)

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE: Governance Engine")
    st.title("Deterministic Governance Engine")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = StructuralCompiler()
        root = compiler.build_dag(uploaded_file, 'word/document.xml')
        
        ledger = {"Validated": [], "Quarantined": []}
        compiler.bifurcate(root, ledger)
        
        # Display Architecture
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Validated Ledger (SSOT)")
            df_valid = pd.DataFrame(ledger["Validated"])
            st.dataframe(df_valid, use_container_width=True)
            
        with col2:
            st.subheader("Reconstruction Queue (Quarantine)")
            st.write("Flagged nodes for schema migration:")
            # Data Editor solves the duplicate key issue by using row indices
            df_quarantine = pd.DataFrame(ledger["Quarantined"])
            edited_df = st.data_editor(df_quarantine, use_container_width=True)
            
            if st.button("Commit Governance Action"):
                st.write("Selected paths marked for structural flattening.")

if __name__ == "__main__":
    main()
