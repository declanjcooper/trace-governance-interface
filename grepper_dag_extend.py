import streamlit as st
import zipfile
import lxml.etree as ET

class EnforcementAuditor:
    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.registry = self._map_registry()

    def _map_registry(self):
        mapping = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    mapping[rel.get('Id')] = rel.get('Target')
        return mapping

def main():
    st.title("The 'Brain Smoothing' Auditor")
    uploaded_file = st.file_uploader("Upload Blueprint (.docx)", type=["docx"])

    if uploaded_file:
        auditor = EnforcementAuditor(uploaded_file)
        
        # 1. WHAT THE AI SEES (The Blueprint)
        with st.expander("SEE THE BLUEPRINT (What the AI is ignoring)"):
            st.write("The AI is currently 'smoothing' over these structural atoms:")
            data = [{"ID": k, "Component": v} for k, v in auditor.registry.items()]
            st.table(data)
            st.info("The AI will not mention these in a generic 'summarize' prompt.")

        # 2. THE ACTUAL AI OUTPUT
        llm_response = st.text_area("Paste the AI Output:")
        
        if st.button("Expose the Smoothing"):
            # Logic: Show the human what is missing in the output
            missing = {k: v for k, v in auditor.registry.items() if k not in llm_response}
            
            if not missing:
                st.success("The AI actually referenced the blueprint!")
            else:
                st.error("EXPOSED: The AI ignored the following structural parts:")
                st.table([{"ID": k, "Component": v} for k, v in missing.items()])
                
                # The "Why"
                st.warning("The AI ignored these parts because it is using a 'brain smoothing' "
                           "approach—predicting fluent language rather than validating "
                           "structural integrity.")

if __name__ == "__main__":
    main()
