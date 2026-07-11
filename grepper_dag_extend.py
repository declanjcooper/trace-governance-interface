import streamlit as st
import zipfile
import lxml.etree as ET

class StructuralStressTest:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.registry = self._map_registry()

    def _map_registry(self):
        """Extracts the XML structural registry (Ground Truth)."""
        mapping = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    mapping[rel.get('Id')] = rel.get('Target')
        return mapping

    def run_automated_audit(self, ai_generated_content):
        """Programmatically identifies missing structural nodes."""
        missing = {k: v for k, v in self.registry.items() if k not in ai_generated_content}
        fidelity_score = (len(self.registry) - len(missing)) / len(self.registry)
        return {"missing": missing, "score": fidelity_score}

def main():
    st.title("Deterministic Ingestion Stress Test")
    uploaded_file = st.file_uploader("Upload .docx for Stress Test", type=["docx"])

    if uploaded_file:
        stress_tester = StructuralStressTest(uploaded_file)
        
        # AUTOMATED TRIGGER: Instead of waiting for a paste, 
        # the system acknowledges the Ground Truth instantly.
        st.write(f"Registry Loaded: {len(stress_tester.registry)} structural atoms identified.")
        
        # This represents the AI's internal 'hallucination' or ingestion attempt
        # In a full pipeline, this content would be fetched via API
        mock_ai_output = "The document describes regulatory compliance requirements."
        
        st.write("---")
        st.info("Running automated diagnostic against structural ground truth...")
        
        results = stress_tester.run_automated_audit(mock_ai_output)
        
        if results["score"] == 1.0:
            st.success("Verification Passed: Structural integrity maintained.")
        else:
            st.error("Verification Failed: Systemic extraction drift detected.")
            st.write(f"Structural atoms lost during ingestion: {len(results['missing'])}")
            st.table([{"ID": k, "Component": v} for k, v in results["missing"].items()])

if __name__ == "__main__":
    main()
