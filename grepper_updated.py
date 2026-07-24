import streamlit as st
import zipfile
import lxml.etree as ET
from typing import List, Dict

class DocumentAuditor:
    """
    Teaches the flow: 
    1. Extract -> 2. Represent (Nodes) -> 3. Compare (Audit).
    """
    def __init__(self, uploaded_file):
        self.file = uploaded_file
        # XML Namespace for Office Open XML
        self.ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def get_nodes(self) -> List[Dict[str, str]]:
        """Parses document.xml and builds a structured list of text nodes."""
        nodes = []
        with zipfile.ZipFile(self.file) as z:
            with z.open('word/document.xml') as f:
                root = ET.parse(f).getroot()
                
                # We traverse the hierarchy to maintain context
                for i, text_node in enumerate(root.findall('.//w:t', self.ns)):
                    if text_node.text and text_node.text.strip():
                        nodes.append({
                            "id": f"node_{i}",
                            "text": text_node.text.strip()
                        })
        return nodes

def main():
    st.title("Document Structural Auditor")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        auditor = DocumentAuditor(uploaded_file)
        nodes = auditor.get_nodes()
        
        st.subheader(f"Extracted {len(nodes)} Structural Nodes")
        
        # Display nodes in a table for clarity
        st.table(nodes)
        
        # Audit phase
        llm_summary = st.text_area("Paste AI Summary for Comparison:")
        
        if st.button("Run Audit"):
            if not llm_summary:
                st.warning("Please paste a summary to audit against.")
                return
            
            # Simple audit logic: Membership check
            for node in nodes:
                if node['text'] in llm_summary:
                    st.success(f"Verified: '{node['text']}' is present.")
                else:
                    st.error(f"Missing: '{node['text']}' was not found in the summary.")

if __name__ == "__main__":
    main()
