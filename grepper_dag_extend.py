import streamlit as st
import zipfile
import lxml.etree as ET

# --- AUDITOR LOGIC ---
class EnforcementAuditor:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.registry = self._extract_registry()

    def _extract_registry(self):
        atoms = []
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                    atoms.append(rel.get('Id'))
        return atoms

    def get_system_prompt(self):
        """Forces the AI to acknowledge the structural blueprint."""
        return f"""
        You are an Auditor AI. You must summarize the document based ONLY on these 
        structural atoms: {', '.join(self.registry)}.
        Constraint: You MUST include the following IDs in your response, 
        demonstrating how they relate to the summary: {', '.join(self.registry)}.
        If you cannot map your summary to these IDs, you must state that the 
        document is structurally incomplete.
        """

    def audit_fidelity(self, llm_response):
        missing_atoms = [atom for atom in self.registry if atom not in llm_response]
        return {
            "is_valid": len(missing_atoms) == 0,
            "missing": missing_atoms,
            "fidelity_score": (len(self.registry) - len(missing_atoms)) / len(self.registry)
        }

# --- STREAMLIT UI ---
def main():
    st.title("Proactive Structural Enforcer")
    uploaded_file = st.file_uploader("Upload Blueprint (.docx)", type=["docx"])

    if uploaded_file:
        auditor = EnforcementAuditor(uploaded_file)
        
        # PROACTIVE STEP: Show the user what the AI will be forced to see
        with st.expander("System Context (What the AI sees)"):
            st.code(auditor.get_system_prompt())

        user_query = st.text_input("Ask a question about the document:")
        
        if st.button("Generate Verified Summary"):
            # Mocking the LLM generation with the forced context
            # In production, replace this with your actual LLM call using get_system_prompt()
            st.info("Generating response with structural enforcement...")
            
            # --- THIS IS WHERE THE LLM GENERATES THE RESPONSE ---
            # llm_response = call_llm(user_query, system_prompt=auditor.get_system_prompt())
            llm_response = "Placeholder: AI must output text including IDs like rId1..." 
            
            # AUTOMATIC AUDIT
            report = auditor.audit_fidelity(llm_response)
            
            if report["is_valid"]:
                st.success("Verified: Integrity Maintained.")
            else:
                st.error("FAILED: Response rejected due to missing structural references.")
                st.write(f"The AI failed to account for: {report['missing']}")

if __name__ == "__main__":
    main()
