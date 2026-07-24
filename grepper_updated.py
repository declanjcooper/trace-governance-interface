import streamlit as st
import zipfile
import lxml.etree as ET
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ChestnutNode:
    tag: str
    text: Optional[str] = None
    children: List['ChestnutNode'] = field(default_factory=list)
    path: str = ""

class ChestnutCompiler:
    def __init__(self, docx_path: str):
        self.archive = zipfile.ZipFile(docx_path)

    def parse_structure(self, part_name: str) -> ChestnutNode:
        with self.archive.open(part_name) as f:
            root = ET.parse(f).getroot()
            return self._build_dag(root, "root")

    def _build_dag(self, element, path: str) -> ChestnutNode:
        tag = element.tag.split('}')[-1]
        new_path = f"{path} -> {tag}"
        node = ChestnutNode(tag=tag, text=element.text.strip() if element.text else None, path=new_path)
        for i, child in enumerate(element):
            if isinstance(child.tag, str):
                node.children.append(self._build_dag(child, f"{new_path}[{i}]"))
        return node

def main():
    st.title("Chestnut TRACE: Governance Map")
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = ChestnutCompiler(uploaded_file)
        dag = compiler.parse_structure('word/document.xml')
        
        # We now have a machine-readable DAG that can be validated
        st.write("DAG Vector Map Generated.")
        # Here we would inject the logic to audit specific 'paths' 
        # (e.g., checking if 'root -> body -> p -> r -> t' meets compliance)

if __name__ == "__main__":
    main()
