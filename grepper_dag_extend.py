import streamlit as st
import zipfile
import lxml.etree as ET

class StructuralAuditor:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.registry = self._map_registry()

    def _map_registry(self):
        """Maps relationship IDs to their respective document component targets."""
        mapping = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    mapping[rel.get('Id')] = rel.get('Target')
        return mapping

def main():
    st.title("Document Structural Auditor")
    uploaded_file = st.file_uploader("Upload .docx file", type=["docx"])

    if uploaded_file:
        auditor = StructuralAuditor(uploaded_file)
        
        # 1. Display document structural registry
        with st.expander("View Document Structural Registry"):
            st.write("Identified structural components (Relationship IDs):")
            data = [{"ID": k, "Component": v} for k, v in auditor.registry.items()]
            st.table(data)
            st.info("The identified components define the structural integrity of the document.")

        # 2. Input for AI-generated response
        llm_response = st.text_area("Paste AI-generated output for validation:")
        
        if st.button("Audit Structural Fidelity"):
            # Identify missing structural references
            missing = {k: v for k, v in auditor.registry.items() if k not in llm_response}
            
            if not missing:
                st.success("All structural components identified in the output.")
            else:
                st.error("Audit findings: Missing structural component references:")
                st.table([{"ID": k, "Component": v} for k, v in missing.items()])
                
                # Contextual explanation regarding structural validation
                st.warning("The AI output omitted references to identified structural components. "
                           "Probabilistic models may prioritize semantic fluency over "
                           "the verification of underlying document architecture.")

if __name__ == "__main__":
    main()
