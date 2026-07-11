import streamlit as st
import zipfile
import lxml.etree as ET

class EnforcementAuditor:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.registry = self._extract_registry()

    def _extract_registry(self):
        """Extracts the Ground Truth atoms (IDs) from the doc manifest."""
        atoms = []
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                # We define the blueprint: if the AI doesn't address these, it's garbage
                for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                    atoms.append(rel.get('Id'))
        return atoms

    def audit_fidelity(self, llm_response):
        """Rejects output that fails to reference critical structural atoms."""
        missing_atoms = [atom for atom in self.registry if atom not in llm_response]
        return {
            "is_valid": len(missing_atoms) == 0,
            "missing": missing_atoms,
            "fidelity_score": (len(self.registry) - len(missing_atoms)) / len(self.registry)
        }

def main():
    st.title("Structural Enforcer: Deterministic AI Gatekeeper")
    
    uploaded_file = st.file_uploader("Upload Blueprint (.docx)", type=["docx"])
    
    if uploaded_file:
        auditor = EnforcementAuditor(uploaded_file)
        st.write(f"Blueprint Loaded. Required Atoms: {len(auditor.registry)}")
        
        llm_input = st.text_area("AI Response to Validate:")
        
        if st.button("Enforce Fidelity"):
            report = auditor.audit_fidelity(llm_input)
            
            if report["is_valid"]:
                st.success("Response Valid: Structural integrity maintained.")
            else:
                st.error("RESPONSE REJECTED: Structural Hallucination Detected")
                st.write(f"Missing Atoms: {report['missing']}")
                st.metric("Fidelity Score", f"{report['fidelity_score']:.2%}")

if __name__ == "__main__":
    main()
