import streamlit as st
import zipfile
import lxml.etree as ET
from typing import List, Dict

# --- UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Chestnut TRACE Compiler")

class ChestnutCompiler:
    def __init__(self, uploaded_file):
        self.file = uploaded_file
        self.ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def get_atomized_nodes(self) -> List[Dict]:
        nodes = []
        try:
            with zipfile.ZipFile(self.file) as z:
                with z.open('word/document.xml') as f:
                    root = ET.parse(f).getroot()
                    # Recursive path-finding logic
                    for body in root.findall('.//w:body', self.ns):
                        for p in body.findall('.//w:p', self.ns):
                            for r in p.findall('.//w:r', self.ns):
                                for t in r.findall('.//w:t', self.ns):
                                    if t.text and t.text.strip():
                                        nodes.append({
                                            "ID": f"node_{hash(t.text + str(len(nodes))) % 1000000}",
                                            "Path": "Root -> document -> body -> p -> r -> t",
                                            "Content": t.text
                                        })
        except Exception as e:
            st.error(f"Traversal Error: {e}")
        return nodes

def main():
    st.title("Chestnut TRACE Compiler")
    uploaded_file = st.file_uploader("Upload .docx for Deterministic Archive", type=["docx"])
    
    if uploaded_file:
        st.subheader("Interrogation Station")
        grep_path = st.text_input("Grep Path", "p -> r -> t")
        
        compiler = ChestnutCompiler(uploaded_file)
        nodes = compiler.get_atomized_nodes()
        
        if nodes:
            st.write(f"Found {len(nodes)} nodes.")
            st.table(nodes)
        else:
            st.warning("No nodes found for the specified path.")

if __name__ == "__main__":
    main()
