import streamlit as st
import zipfile
import lxml.etree as ET

class EnforcementAuditor:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.registry = self._map_registry()

    def _map_registry(self):
        """Maps IDs to their human-readable targets for human comprehension."""
        mapping = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    # Mapping the ID to the specific document part
                    mapping[rel.get('Id')] = rel.get('Target')
        return mapping

    def audit_fidelity(self, llm_response):
        """Checks if the human-readable document parts are acknowledged."""
        missing = {atom: target for atom, target in self.registry.items() if atom not in llm_response}
        return {
            "is_valid": len(missing) == 0,
            "missing": missing,
            "fidelity_score": (len(self.registry) - len(missing)) / len(self.registry)
        }

def main():
    st.title("Proactive Structural Enforcer v2.0")
    uploaded_file = st.file_uploader("Upload Blueprint (.docx)", type=["docx"])

    if uploaded_file:
        auditor = EnforcementAuditor(uploaded_file)
        
        st.write("### Structural Integrity Registry")
        st.write(f"Components required to validate document fidelity: {len(auditor.registry)}")
        
        # User input for the response to audit
        llm_response = st.text_area("AI Response to Validate:")
        
        if st.button("Enforce Fidelity"):
            report = auditor.audit_fidelity(llm_response)
            
            if report["is_valid"]:
                st.success("Response Valid: All structural components accounted for.")
            else:
                st.error("RESPONSE REJECTED: Structural Hallucination Detected")
                
                # Human-readable breakdown
                st.write("The AI failed to account for these critical document parts:")
                data = [{"ID": k, "Component": v} for k, v in report["missing"].items()]
                st.table(data)
                
                st.metric("Fidelity Score", f"{report['fidelity_score']:.2%}")

if __name__ == "__main__":
    main()
