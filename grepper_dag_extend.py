import streamlit as st
import zipfile
import lxml.etree as ET
import pypdf
import pandas as pd
import sys

# Configure the page layout for wide comparison
st.set_page_config(layout="wide")

class SchemaComparator:
    def __init__(self, doc_path, pdf_path):
        self.doc_path = doc_path
        self.pdf_path = pdf_path

    def get_docx_data(self):
        """Extracts the native XML relationship registry from the .docx package."""
        try:
            schema = {}
            with zipfile.ZipFile(self.doc_path) as z:
                with z.open('word/_rels/document.xml.rels') as f:
                    root = ET.parse(f).getroot()
                    ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                    for rel in root.findall('.//rels:Relationship', ns):
                        # Force string conversion for Arrow compatibility
                        schema[str(rel.get('Id'))] = str(rel.get('Target'))
            return schema
        except Exception as e:
            return {"Error": str(e)}

    def get_pdf_data(self):
        """Captures the linear sequence inferred by the PDF extraction process."""
        try:
            reader = pypdf.PdfReader(self.pdf_path)
            lineage = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                # Force string conversion for Arrow compatibility
                lineage.append({
                    "Step": str(i + 1), 
                    "Inferred_Node": str(text[:50].strip())
                })
            return lineage
        except Exception as e:
            return [{"Error": str(e)}]

def main():
    st.title("Schema Comparative Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        docx_file = st.file_uploader("Source .docx", type=["docx"])
    with col2:
        pdf_file = st.file_uploader("Target Archive .pdf", type=["pdf"])

    if docx_file and pdf_file:
        comp = SchemaComparator(docx_file, pdf_file)
        
        docx_schema = comp.get_docx_data()
        pdf_lineage = comp.get_pdf_data()
        
        st.subheader("Analysis Results")
        
        try:
            st.write("### Structural Inventory Comparison")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("**Native XML Registry (Source)**")
                # Ensure data is converted to list of tuples for DataFrame construction
                st.table(pd.DataFrame(list(docx_schema.items()), columns=["ID", "Target"]))
                
            with col_b:
                st.write("**Extracted Lineage (Target)**")
                st.table(pd.DataFrame(pdf_lineage))
                
        except Exception as e:
            st.error(f"Render Error: {e}")

if __name__ == "__main__":
    main()
