import streamlit as st
import zipfile
import lxml.etree as ET
import json

# Set page config for wide display
st.set_page_config(layout="wide")

def main():
    st.title("Stable Schema Comparative Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        docx_file = st.file_uploader("Source .docx", type=["docx"])
    with col2:
        pdf_file = st.file_uploader("Target Archive .pdf", type=["pdf"])

    if docx_file and pdf_file:
        st.subheader("Structural Analysis")
        
        # 1. Native .docx Registry (Pure Python)
        docx_data = {}
        try:
            with zipfile.ZipFile(docx_file) as z:
                with z.open('word/_rels/document.xml.rels') as f:
                    root = ET.parse(f).getroot()
                    ns = {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                    for rel in root.findall('.//rels:Relationship', ns):
                        docx_data[str(rel.get('Id'))] = str(rel.get('Target'))
        except Exception as e:
            st.error(f"DOCX Parsing Error: {e}")

        # 2. PDF Binary Inspection (Pure Python, No pypdf)
        pdf_data = {"Status": "Binary Inspection Only", "Warning": "No PDF library used to prevent crashes"}
        try:
            # We treat the PDF as a stream of bytes to avoid segmentation faults
            b = pdf_file.getvalue()
            pdf_data["Size_Bytes"] = len(b)
            pdf_data["Has_Xref"] = b"/xref" in b
            pdf_data["Has_Linearized"] = b"/Linearized" in b
        except Exception as e:
            st.error(f"PDF Inspection Error: {e}")

        # 3. Render using JSON (Bypassing Arrow/Table serialization)
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Native XML Registry")
            st.json(docx_data)
        with c2:
            st.write("### PDF Structural Markers")
            st.json(pdf_data)

if __name__ == "__main__":
    main()
