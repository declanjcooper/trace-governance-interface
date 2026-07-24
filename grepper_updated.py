import streamlit as st
import zipfile
import lxml.etree as ET
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ChestnutNode:
    tag: str
    text: Optional[str] = None
    children: List['ChestnutNode'] = field(default_factory=list)

class ChestnutCompiler:
    def __init__(self, docx_path: str):
        self.archive = zipfile.ZipFile(docx_path)
        self.ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def parse_part(self, part_name: str) -> ChestnutNode:
        with self.archive.open(part_name) as f:
            root = ET.parse(f).getroot()
            return self._build_tree(root)

    def _build_tree(self, element) -> ChestnutNode:
        tag = element.tag.split('}')[-1]
        node = ChestnutNode(tag=tag, text=element.text.strip() if element.text and element.text.strip() else None)
        for child in element:
            if isinstance(child.tag, str):
                node.children.append(self._build_tree(child))
        return node

def render_tree(node: ChestnutNode, level=0):
    """Recursive visualizer for the structural signature."""
    prefix = "  " * level
    st.text(f"{prefix}└── {node.tag} {f': {node.text}' if node.text else ''}")
    for child in node.children:
        render_tree(child, level + 1)

def main():
    st.title("Chestnut TRACE: Structural Compiler")
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = ChestnutCompiler(uploaded_file)
        tree = compiler.parse_part('word/document.xml')
        st.subheader("Structural Signature (SSOT)")
        render_tree(tree)

if __name__ == "__main__":
    main()
