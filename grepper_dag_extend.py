import streamlit as st
import zipfile
import lxml.etree as ET

class StructuralAuditor:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def get_document_nodes(self):
        """Extracts key content/context nodes from the document."""
        nodes = []
        with zipfile.ZipFile(self.doc_path) as z:
            # We target the actual text content nodes, not just structural refs
            with z.open('word/document.xml') as f:
                root = ET.parse(f).getroot()
                # Finding paragraph text nodes as the 'Context'
                for p in root.findall('.//w:t', self.ns):
                    if p.text:
                        nodes.append(p.text)
        return nodes[:10]  # Showing first 10 nodes for verification

def main():
    st.title("Document Context Auditor")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        auditor = StructuralAuditor(uploaded_file)
        nodes = auditor.get_document_nodes()
        
        st.subheader("Document Nodes (The Content)")
        for i, node in enumerate(nodes):
            st.write(f"Node {i}: {node}")
        
        st.divider()
        llm_response = st.text_area("Paste the AI Summary Here:")
        
        if st.button("Audit Omissions"):
            st.subheader("Omission Report")
            for node in nodes:
                if node not in llm_response:
                    st.error(f"Omitted: '{node}'")
                else:
                    st.success(f"Included: '{node}'")

if __name__ == "__main__":
    main()
