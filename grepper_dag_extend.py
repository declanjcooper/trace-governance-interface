import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import uuid
import datetime
import time
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any

# ==========================================
# --- STREAMLIT LIFECYCLE INITIALIZATION ---
# ==========================================
# MUST be at the absolute top of the global scope to prevent lifecycle errors.
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
                # Using the specific Y-axis hierarchy vector for our 3D mapping
                node["strain_vectors"]["y_axis_hierarchy"] = -delta 
                node["alignment_notes"].append(f"Fragmentation: |Δ| = {delta} ({run_count} runs observed vs {allowed_runs} allowed).")
                
    return node_map

def reconcile_node(node_id: str, node_map: Dict[str, Any]) -> Dict[str, Any]:
    """The 'Snap'. Stitches child fragments and logs the vector collapse."""
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
# --- 3D VISUALIZATION ENGINE ---
# ==========================================
def render_reconciliation_simulation(node_data, resolution_progress=0.0):
    """
    Renders the 3-6-1 topology and animates the strain resolution.
    resolution_progress: 0.0 = Strained, 1.0 = Equilibrium (Origin)
    """
    strain = node_data.get("strain_vectors", {})
    start_x = strain.get("x_axis_structure", 0)
    start_y = strain.get("y_axis_hierarchy", 0)
    start_z = strain.get("z_axis_context", 0)
    
    start_pos = np.array([start_x, start_y, start_z])
    origin = np.array([0.0, 0.0, 0.0])
    
    current_pos = start_pos + (origin - start_pos) * resolution_progress
    
    fig = go.Figure()

    # Draw the Axes
    axis_config = [
        ([-1.5, 1.5], [0, 0], [0, 0], "X-Axis (Syntactic)", "gray"),
        ([0, 0], [-1.5, 1.5], [0, 0], "Y-Axis (Semantic)", "gray"),
        ([0, 0], [0, 0], [-1.5, 1.5], "Z-Axis (Context)", "gray")
    ]
    for x, y, z, name, color in axis_config:
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines", line=dict(color=color, width=2, dash="dot"), name=name, hoverinfo="skip"))

    # Plot the Origin
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode="markers", marker=dict(size=8, color="white", symbol="diamond"), name="Master Contract (0,0,0)"))

    # Plot the Content of Interest
    node_color = "cyan" if resolution_progress == 1.0 else "orange"
    node_label = "Equilibrium" if resolution_progress == 1.0 else f"Strain Δ={node_data.get('strain_distance_delta', 0)}"
    
    fig.add_trace(go.Scatter3d(
        x=[current_pos[0]], y=[current_pos[1]], z=[current_pos[2]],
        mode="markers+text", marker=dict(size=12, color=node_color),
        text=[f"{node_data.get('@id')} ({node_label})"], textposition="top center", name="Current Node State"
    ))

    # Draw the Friction Line
    if resolution_progress < 1.0:
        fig.add_trace(go.Scatter3d(
            x=[0, current_pos[0]], y=[0, current_pos[1]], z=[0, current_pos[2]],
            mode="lines", line=dict(color="orange", width=5), name="Friction (Δ)"
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-1.5, 1.5], title="Structure"),
            yaxis=dict(range=[-1.5, 1.5], title="Meaning"),
            zaxis=dict(range=[-1.5, 1.5], title="Context"),
            aspectmode="cube"
        ),
        margin=dict(l=0, r=0, b=0, t=0), height=500,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

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
            4: {"title": "4. Reconciliation Snap", "text": "Engage the reconciliation vector for the strained atoms. Watch the nodes snap back into Equilibrium and disappear from the active Worklist."}
        }

    def next(self):
        if self.step < 4: self.step += 1
            
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
        if col_next.button("Next ➡️") and controller.step < 4:
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
