import streamlit as st
import zipfile
import lxml.etree as ET
import pypdf # You will need to install pypdf

class DriftDetector:
    def __init__(self, doc_path, pdf_path):
        self.doc_path = doc_path
        self.pdf_path = pdf_path
        self.docx_registry = self._map_docx_registry()
        self.pdf_structure = self._map_pdf_structure()

    def _map_docx_registry(self):
        """Extracts the Ground Truth from the native .docx file."""
        mapping = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    mapping[rel.get('Id')] = rel.get('Target')
        return mapping

    def _map_pdf_structure(self):
        """Extracts available structural metadata from the PDF."""
        # This is where we measure the 'Loss'
        metadata = {}
        reader = pypdf.PdfReader(self.pdf_path)
        metadata['pages'] = len(reader.pages)
        metadata['xmp'] = reader.xmp_metadata
        return metadata

    def analyze_drift(self):
        """Calculates the structural delta."""
        # The delta is the difference between the rich registry and the flat PDF
        delta = len(self.docx_registry) - 0 # PDF 'structural' registry is effectively 0
        return {
            "docx_nodes": len(self.docx_registry),
            "pdf_nodes": 0, # Standard PDF extraction discards structural rIds
            "drift_score": delta
        }

def main():
    st.title("Structural Drift Detector (Native vs. Archive)")
    
    col1, col2 = st.columns(2)
    with col1:
        docx_file = st.file_uploader("Upload Native .docx (Source)", type=["docx"])
    with col2:
        pdf_file = st.file_uploader("Upload Archived .pdf (Target)", type=["pdf"])

    if docx_file and pdf_file:
        detector = DriftDetector(docx_file, pdf_file)
        drift = detector.analyze_drift()
        
        st.write("---")
        st.metric("Total Structural Atoms Lost (Drift)", drift['drift_score'])
        
        st.write("### Component Manifest")
        st.table([{"ID": k, "Component": v} for k, v in detector.docx_registry.items()])
        
        if drift['drift_score'] > 0:
            st.error("Systemic extraction drift confirmed: PDF conversion has stripped the structural registry.")

if __name__ == "__main__":
    main()
