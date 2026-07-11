import streamlit as st
import zipfile
import lxml.etree as ET
import pypdf
import pandas as pd

class SchemaComparator:
    def __init__(self, doc_path, pdf_path):
        self.doc_path = doc_path
        self.pdf_path = pdf_path
        self.docx_schema = self._extract_docx_schema()
        self.extracted_lineage = self._simulate_extraction_lineage()

    def _extract_docx_schema(self):
        """Extracts native XML relationship registry from the .docx package."""
        schema = {}
        with zipfile.ZipFile(self.doc_path) as z:
            with z.open('word/_rels/document.xml.rels') as f:
                root = ET.parse(f).getroot()
                ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                for rel in root.findall('.//rels:Relationship', ns):
                    # Explicitly convert to string to ensure Arrow compatibility
                    schema[str(rel.get('Id'))] = str(rel.get('Target'))
        return schema

    def _simulate_extraction_lineage(self):
        """Captures linear sequence inferred by the PDF extraction process."""
        reader = pypdf.PdfReader(self.pdf_path)
        lineage = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            # Explicitly cast all elements to strings
            lineage.append({
                "Step": str(i + 1), 
                "Inferred_Node": str(text[:50].strip())
            })
        return lineage

def main():
    st.set_page_config(layout="wide")
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
        
        # Consistent string-based formatting to prevent Arrow serialization errors
        comparison_data = pd.DataFrame([
            {"Metric": "Registry Nodes", "Source (.docx)": str(len(comp.docx_schema)), "Target (.pdf)": "N/A"},
            {"Metric": "Defined Relationships", "Source (.docx)": str(len(comp.docx_schema)), "Target (.pdf)": "0"},
        ])
        st.table(comparison_data)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### Native XML Registry (Source)")
            source_df = pd.DataFrame([{"ID": k, "Target": v} for k, v in comp.docx_schema.items()])
            st.table(source_df)
            
        with col_b:
            st.write("### Extracted Lineage (Target)")
            st.write("Sequence inferred by spatial processing heuristics:")
            lineage_df = pd.DataFrame(comp.extracted_lineage)
            st.table(lineage_df)

if __name__ == "__main__":
    main()
