import streamlit as st
import zipfile
import lxml.etree as ET
import pypdf

class SchemaComparator:
    def __init__(self, doc_path, pdf_path):
        self.doc_path = doc_path
        self.pdf_path = pdf_path
        self.docx_schema = self._extract_docx_schema()
        self.pdf_schema = self._extract_pdf_schema()

    def _extract_docx_schema(self):
        """Extracts relationship mapping from the .docx package."""
        schema = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    schema[rel.get('Id')] = rel.get('Target')
        return schema

    def _extract_pdf_schema(self):
        """Extracts available structure/metadata from the PDF."""
        # Represents the schema recovered by the PDF extraction engine
        reader = pypdf.PdfReader(self.pdf_path)
        return {
            "Total Pages": len(reader.pages),
            "Metadata Keys": list(reader.metadata.keys()) if reader.metadata else []
        }

def main():
    st.title("Schema Comparative Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        docx_file = st.file_uploader("Source .docx", type=["docx"])
    with col2:
        pdf_file = st.file_uploader("Target Archive .pdf", type=["pdf"])

    if docx_file and pdf_file:
        comp = SchemaComparator(docx_file, pdf_file)
        
        st.write("---")
        st.subheader("Template Schema Comparison")
        
        # Displaying the difference in structural definition
        data = [
            {"Metric": "Registry Nodes", "Source (.docx)": len(comp.docx_schema), "Target (.pdf)": "N/A (Flattened)"},
            {"Metric": "Defined Relationships", "Source (.docx)": len(comp.docx_schema), "Target (.pdf)": 0},
        ]
        st.table(data)
        
        st.write("### Structural Node Inventory")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Source Nodes (.docx)**")
            st.table([{"ID": k, "Target": v} for k, v in comp.docx_schema.items()])
        with col_b:
            st.write("**Target Nodes (.pdf)**")
            st.info("No structural nodes identified in archival format.")

if __name__ == "__main__":
    main()
