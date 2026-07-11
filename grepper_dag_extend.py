import streamlit as st
import zipfile
import lxml.etree as ET
from typing import Dict, Any

# ==========================================
# --- TOPOLOGICAL AUDITOR ENGINE ---
# ==========================================
class TopologicalAuditor:
    def __init__(self, doc_path: str):
        self.doc_path = doc_path
        self.ns = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'p': 'http://schemas.openxmlformats.org/package/2006/relationships'
        }
        self.registry: Dict[str, str] = {}
        self.atom_graph: Dict[str, Any] = {}

    def atomize(self):
        """Ingests and maps the package topology as the Ground Truth SSOT."""
        with zipfile.ZipFile(self.doc_path) as z:
            # 1. Blueprint Validation
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                for rel in root.findall('.//p:Relationship', self.ns):
                    self.registry[rel.get('Id')] = rel.get('Target')
            
            # 2. Structural Atomization
            self._build_atom_graph(z)
        return self.atom_graph

    def _build_atom_graph(self, z):
        """Captures XML parts as immutable spatial coordinates."""
        for r_id, target in self.registry.items():
            part_path = f"word/{target}"
            if part_path in z.namelist():
                with z.open(part_path) as f:
                    tree = ET.parse(f)
                    self.atom_graph[r_id] = {
                        "target": target,
                        "node_count": len(tree.xpath('//*')),
                        "xml_structure": ET.tostring(tree.getroot(), encoding='unicode')[:500] # Preview
                    }

    def audit_discrepancy(self, llm_stream: str, atom_id: str) -> float:
        """Quantifies Structural Entropy: Delta between Ground Truth and LLM output."""
        atom = self.atom_graph.get(atom_id)
        if not atom: return 1.0
        
        # Entropy Calculation: Deviation in structural markers
        # Logic: (Length delta / Ground Truth length)
        atom_text = atom.get("xml_structure", "")
        return abs(len(atom_text) - len(llm_stream)) / (len(atom_text) + 1)

# ==========================================
# --- STREAMLIT UI: ENTROPY EXPOSURE ---
# ==========================================
def main():
    st.set_page_config(page_title="Chestnut Entropy Auditor", layout="wide")
    st.title("🔭 Entropy Exposure System")
    
    with st.sidebar:
        uploaded_file = st.file_uploader("Upload Document Blueprint (.docx)", type=["docx"])
        if uploaded_file and st.button("Perform Audit"):
            auditor = TopologicalAuditor(uploaded_file)
            st.session_state.audit_data = auditor.atomize()
            st.session_state.auditor = auditor
            st.success("Topology Atomized.")

    if 'audit_data' in st.session_state:
        st.subheader("Structural Ground Truth")
        st.write(st.session_state.audit_data)
        
        st.divider()
        st.subheader("Expose Brain Smoothing")
        llm_input = st.text_area("Paste LLM Smoothed Output:")
        
        if st.button("Audit Fidelity"):
            for atom_id, data in st.session_state.audit_data.items():
                entropy = st.session_state.auditor.audit_discrepancy(llm_input, atom_id)
                st.metric(f"Entropy Score (Atom: {atom_id})", f"{entropy:.4f}")

if __name__ == "__main__":
    main()
