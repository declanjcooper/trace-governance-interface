import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import uuid
import datetime
import time
import altair as alt
import pandas as pd
from typing import Dict, Any

# ==========================================
# --- STREAMLIT LIFECYCLE INITIALIZATION ---
# ==========================================
st.set_page_config(page_title="Chestnut Alignment Core", layout="wide", initial_sidebar_state="expanded")

def trigger_rerun():
    """Environment-safe rerun handler."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ==========================================
# --- TOPOLOGICAL ALIGNMENT CORE ---
# ==========================================
CONTRACT_REFERENCE = {
    "target_node": "p",
    "required_properties": ["coi", "hasChild"],
    "max_text_runs": 1, 
    "allowed_formatting": ["regular"] 
}

def generate_dag_vectors(zip_ref: zipfile.ZipFile, filename: str) -> Dict[str, Any]:
    try:
        raw_bytes = zip_ref.read(filename)
        root = ET.fromstring(raw_bytes)
        node_map = {}

        def traverse(node, current_path, parent_id):
            node_id = f"node_{uuid.uuid4().hex[:8]}"
            tag_name = node.tag.split('}')[-1]
            new_path = current_path + [tag_name]
            
            node_data = {
                "@id": node_id,
                "dag_path": " -> ".join(new_path),
                "coi": node.text.strip() if node.text and node.text.strip() else None,
                "parent": parent_id,
                "hasChild": []
            }
            node_map[node_id] = node_data
            for child in node:
                child_id = traverse(child, new_path, node_id)
                node_map[node_id]["hasChild"].append(child_id)
            return node_id

        traverse(root, ["Root"], None)
        return node_map
    except Exception as e:
        st.sidebar.error(f"Ingestion Error: {e}")
        return {}

def evaluate_alignment_strain(node_map: Dict[str, Any]) -> Dict[str, Any]:
    for node in node_map.values():
        node["alignment_status"] = "Equilibrium"
        node["strain_distance_delta"] = 0  
        node["strain_vectors"] = {} 
        node["alignment_notes"] = []
        
        if " -> p" in node.get("dag_path", ""):
            text_runs = [c for c in node.get("hasChild", []) if " -> r" in node_map.get(c, {}).get("dag_path", "")]
            run_count = len(text_runs)
            allowed_runs = CONTRACT_REFERENCE["max_text_runs"]
            
            if run_count > allowed_runs:
                delta = run_count - allowed_runs
                node["alignment_status"] = "Strain"
                node["strain_distance_delta"] = delta
                node["strain_vectors"]["y_axis_hierarchy"] = -delta 
                node["alignment_notes"].append(f"Fragmentation: |Δ| = {delta} ({run_count} runs observed vs {allowed_runs} allowed).")
                
    return node_map

def reconcile_node(node_id: str, node_map: Dict[str, Any]) -> Dict[str, Any]:
    node = node_map[node_id]
    if "reconciliation_history" not in node:
        node["reconciliation_history"] = []
        
    node["reconciliation_history"].append({
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "resolved_delta": node.get("strain_distance_delta", 0),
        "resolved_vectors": node.get("strain_vectors", {}),
        "action": "Vector Collapse: Fragments stitched into single coherent run."
    })
    
    child_runs = [c for c in node.get("hasChild", []) if " -> r" in node_map.get(c, {}).get("dag_path", "")]
    stitched_text = ""
    for r_id in child_runs:
        r_node = node_map.get(r_id, {})
        if r_node.get("coi"):
            stitched_text += r_node["coi"] + " "
            
    node["coi"] = stitched_text.strip() if stitched_text else "[STITCHED PAYLOAD RECOVERED FROM FRAGMENTS]"
    node["alignment_status"] = "Equilibrium"
    node["strain_distance_delta"] = 0
    node["strain_vectors"] = {}
    node["alignment_notes"] = ["System Reconciled: Atom returned to Origin (0,0,0)."]
    
    return node_map

# ==========================================
# --- 2D VISUALIZATION ENGINE ---
# ==========================================
def render_native_simulation(node_data, resolution_progress=0.0):
    start_y = node_data.get("strain_vectors", {}).get("y_axis_hierarchy", 0)
    current_y = start_y + (0.0 - start_y) * resolution_progress
    
    data = pd.DataFrame({
        "X": [0.0, 0.0],
        "Y": [0.0, current_y],
        "Entity": ["Master Contract (0,0)", f"Node {node_data.get('@id', 'Unknown')[:8]}"],
        "State": ["Equilibrium", "Resolved" if resolution_progress == 1.0 else "Strain"]
    })
    
    chart = alt.Chart(data).mark_circle(size=400, opacity=0.8).encode(
        x=alt.X("X", scale=alt.Scale(domain=[-1.5, 1.5]), title="Syntactic Structure (X Axis)"),
        y=alt.Y("Y", scale=alt.Scale(domain=[-1.5, 1.5]), title="Semantic Meaning (Y Axis)"),
        color=alt.Color("State", scale=alt.Scale(
            domain=["Equilibrium", "Strain", "Resolved"],
            range=["gray", "orange", "teal"]
        )),
        tooltip=["Entity", "X", "Y", "State"]
    ).properties(height=400)
    
    return chart

# ==========================================
# --- PEDAGOGICAL CONTROLLER ---
# ==========================================
class PedagogicalController:
    def __init__(self):
        self.step = 1
        self.narrative = {
            1: {"title": "1. Document Ingestion", "text": "Before we look at data, we must establish an orientation. The Master Contract dictates the expected topology."},
            2: {"title": "2. Topological Mapping", "text": "Upload a .docx file. The engine will map the raw XML into a deterministic DAG path."},
            3: {"title": "3. Orthogonal Inspection", "text": "The engine has calculated the distance (Δ) from the origin for all nodes. We now filter the Worklist to display only atoms currently in a state of Strain."},
            4: {"title": "4. Reconciliation Snap", "text": "Engage the reconciliation vector for the strained atoms. Watch the nodes snap back into Equilibrium and disappear from the active Worklist."},
            5: {"title": "5. Information Density", "text": "You have separated the container from the cargo. By flattening the fractured vectors, you created a high-density payload that mitigates the ambiguity causing LLMs to hallucinate."}
        }

    def next(self):
        if self.step < 5: self.step += 1
            
    def prev(self):
        if self.step > 1: self.step -= 1

# ==========================================
# --- UI OBSERVATION LAYER ---
# ==========================================
def main():
    if 'controller' not in st.session_state:
        st.session_state.controller = PedagogicalController()
    
    controller = st.session_state.controller

    with st.sidebar:
        st.title("Chestnut Trainer")
        st.markdown("---")
        
        current_lesson = controller.narrative[controller.step]
        st.subheader(current_lesson["title"])
        st.write(current_lesson["text"])
        st.markdown("---")
        
        if controller.step == 2:
            uploaded_file = st.file_uploader("Upload Document (.docx)", type=["docx"])
            if uploaded_file and st.button("Atomize Data"):
                with zipfile.ZipFile(uploaded_file) as z:
                    st.session_state.node_map = evaluate_alignment_strain(generate_dag_vectors(z, "word/document.xml"))
                controller.next()
                trigger_rerun()

        st.markdown("---")
        col_prev, col_next = st.columns(2)
        if col_prev.button("⬅️ Back") and controller.step > 1:
            controller.prev()
            trigger_rerun()
        if col_next.button("Next ➡️") and controller.step < 5:
            controller.next()
            trigger_rerun()

    st.title("Topological Alignment Core")
    
    if controller.step == 1:
        st.info("Awaiting Document Ingestion... (See Left Panel)")
        st.markdown("### Master Contract (Active)")
        st.json(CONTRACT_REFERENCE)
        
    elif controller.step >= 3 and 'node_map' in st.session_state:
        st.subheader("Orthogonal Alignment Viewer")
        
        st.markdown("##### Diagnostic Worklist")
        filter_option = st.radio("Node Filter:", ["Action Required (Strain Only)", "View All Target Nodes"], horizontal=True)
        
        if filter_option == "Action Required (Strain Only)":
            node_ids = [k for k, v in st.session_state.node_map.items() if " -> p" in v.get("dag_path", "") and v.get("alignment_status") == "Strain"]
        else:
            node_ids = [k for k, v in st.session_state.node_map.items() if " -> p" in v.get("dag_path", "")]
        
        if node_ids:
            selected_id = st.selectbox(f"Select Atom to Inspect ({len(node_ids)} total):", node_ids)
            observed_node = st.session_state.node_map[selected_id]
            
            col_obs, col_con = st.columns(2)
            
            with col_obs:
                st.markdown("#### Document Vector (Observed)")
                st.json(observed_node)
                
            with col_con:
                st.markdown("#### Contract Vector (Required)")
                st.json(CONTRACT_REFERENCE)
                
            st.divider()
            
            if observed_node["alignment_status"] == "Strain":
                st.error(f"❌ STRAIN DETECTED: {', '.join(observed_node['alignment_notes'])}")
                
                st.markdown("### 🔭 Visual Simulation of Reconciliation")
                st.markdown("Observe the geometric friction. Use the slider to introduce structural vectors and force the node back into alignment with the Master Contract.")
                
                resolution_time = st.slider("Resolution Vector Engine", 0.0, 1.0, 0.0, step=0.05, key=f"reconcile_slider_{selected_id}")
                
                chart = render_native_simulation(observed_node, resolution_time)
                st.altair_chart(chart, use_container_width=True)
                
                if controller.step == 4:
                    if st.button("⚡ Execute Final Snap (Write to Contract)", use_container_width=True):
                        st.session_state.node_map = reconcile_node(selected_id, st.session_state.node_map)
                        st.success("✅ SNAP! Fragments stitched. Node returning to Equilibrium...")
                        st.toast("Atom Reconciled Successfully!", icon="✅")
                        time.sleep(1.5) 
                        trigger_rerun()
            else:
                st.success("✅ EQUILIBRIUM: Atom in alignment with Contract.")
        else:
            if filter_option == "Action Required (Strain Only)":
                st.success("🏆 Inbox Zero: No nodes are currently in a state of Strain. The document is aligned.")
            else:
                st.warning("No target nodes found in the current document structure.")

        # --- STEP 5: INFORMATION DENSITY PAYOFF ---
        if controller.step == 5:
            st.divider()
            st.markdown("### 🧠 Concept: The ROI of Information Density")
            st.markdown("By enforcing strict deterministic topology before passing data to an LLM, you stop paying a probabilistic tax on structural boilerplate.")
            
            col_met1, col_met2, col_met3 = st.columns(3)
            col_met1.metric(label="Example Raw XML Payload", value="~11,000 Tokens", delta="High Compute Cost", delta_color="inverse")
            col_met2.metric(label="Density Compression", value="- 40%", delta="Boilerplate Stripped", delta_color="normal")
            col_met3.metric(label="Reconciled DAG Payload", value="~6,600 Tokens", delta="High Signal-to-Noise", delta_color="normal")
            
            st.info("💡 **The Lesson:** An LLM cannot hallucinate on ambiguity that no longer exists. Dense, structurally sound data is the foundation of AI governance.")

if __name__ == "__main__":
    main()
