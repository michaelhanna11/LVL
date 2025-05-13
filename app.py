import streamlit as st
import os
import io
from datetime import datetime
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
import pandas as pd
import base64

# Program details
PROGRAM_VERSION = "1.0 - 2025"
PROGRAM = "Load Combination Calculator to AS 3610.2 (Int):2023"

# Company details
COMPANY_NAME = "tekhne Consulting Engineers"
COMPANY_ADDRESS = ""

# Logo URLs
LOGO_URL = "https://drive.google.com/uc?export=download&id=1VebdT2loVGX57noP9t2GgQhwCNn8AA3h"
FALLBACK_LOGO_URL = "https://onedrive.live.com/download?cid=A48CC9068E3FACE0&resid=A48CC9068E3FACE0%21s252b6fb7fcd04f53968b2a09114d33ed"

def calculate_concrete_load(thickness, reinforcement_percentage):
    """Calculate G_c in kN/m² based on concrete thickness and reinforcement percentage."""
    base_density = 24  # kN/m³
    reinforcement_load = 0.5 * reinforcement_percentage  # kN/m²
    G_c = base_density * thickness + reinforcement_load * thickness
    return G_c

def compute_combinations(G_f, G_c, Q_w, Q_m, Q_h, W_s, W_u, F_w, Q_x, P_c, I, stage, gamma_d):
    """Compute load combinations for a given stage and gamma_d."""
    combinations = []

    if stage == "1":
        comb_1 = (1.35 * G_f, 0.0)
        comb_2 = (gamma_d * (1.2 * G_f + 1.5 * Q_w + 1.5 * Q_m + 1.0 * W_s), gamma_d * (1.5 * Q_h))
        comb_3 = (1.2 * G_f + 1.0 * W_u + 1.5 * F_w, 0.0)
        comb_4 = (0.9 * G_f + 1.0 * W_u + 1.5 * F_w, 0.0)
        comb_5 = (1.0 * G_f + 1.1 * I, 0.0)
        combinations = [comb_1, comb_2, comb_3, comb_4, comb_5]
    
    elif stage == "2":
        comb_6 = (gamma_d * (1.35 * G_f + 1.35 * G_c), 0.0)
        comb_7 = (gamma_d * (1.2 * G_f + 1.2 * G_c + 1.5 * Q_w + 1.5 * Q_m + 1.0 * W_s + 1.5 * F_w + 1.5 * Q_x + 1.0 * P_c), 
                 gamma_d * (1.5 * Q_h))
        comb_8 = (1.0 * G_f + 1.0 * G_c + 1.1 * I, 0.0)
        combinations = [comb_6, comb_7, comb_8]
    
    elif stage == "3":
        comb_9 = (gamma_d * (1.35 * G_f + 1.35 * G_c), 0.0)
        comb_10 = (gamma_d * (1.2 * G_f + 1.2 * G_c + 1.5 * Q_w + 1.5 * Q_m + 1.0 * W_s + 1.5 * F_w + 1.5 * Q_x + 1.0 * P_c),
                  gamma_d * (1.5 * Q_h))
        comb_11 = (1.2 * G_f + 1.2 * G_c + 1.0 * W_u, 0.0)
        comb_12 = (1.0 * G_f + 1.0 * G_c + 1.1 * I, 0.0)
        combinations = [comb_9, comb_10, comb_11, comb_12]
    
    return combinations

def get_combination_description(stage, index):
    """Get the description text for each combination with proper formatting."""
    if stage == "1":
        descriptions = [
            "1: 1.35G<sub>f</sub>",
            "2: 1.2G<sub>f</sub> + 1.5Q<sub>w</sub> + 1.5Q<sub>m</sub> + 1.5Q<sub>h</sub> + 1W<sub>s</sub>",
            "3: 1.2G<sub>f</sub> + 1W<sub>u</sub> + 1.5F<sub>w</sub>",
            "4: 0.9G<sub>f</sub> + 1W<sub>u</sub> + 1.5F<sub>w</sub>",
            "5: 1G<sub>f</sub> + 1.1I"
        ]
    elif stage == "2":
        descriptions = [
            "6: 1.35G<sub>f</sub> + 1.35G<sub>c</sub>",
            "7: 1.2G<sub>f</sub> + 1.2G<sub>c</sub> + 1.5Q<sub>w</sub> + 1.5Q<sub>m</sub> + 1.5Q<sub>h</sub> + 1W<sub>s</sub> + 1.5F<sub>w</sub> + 1.5Q<sub>x</sub> + P<sub>c</sub>",
            "8: 1G<sub>f</sub> + 1G<sub>c</sub> + 1.1I"
        ]
    elif stage == "3":
        descriptions = [
            "9: 1.35G<sub>f</sub> + 1.35G<sub>c</sub>",
            "10: 1.2G<sub>f</sub> + 1.2G<sub>c</sub> + 1.5Q<sub>w</sub> + 1.5Q<sub>m</sub> + 1.5Q<sub>h</sub> + 1W<sub>s</sub> + 1.5F<sub>w</sub> + 1.5Q<sub>x</sub> + P<sub>c</sub>",
            "11: 1.2G<sub>f</sub> + 1.2G<sub>c</sub> + 1.0W<sub>u</sub>",
            "12: 1G<sub>f</sub> + 1G<sub>c</sub> + 1.1I"
        ]
    return descriptions[index] if index < len(descriptions) else f"Combination {index+1}"

def create_results_dataframe(combinations, stage, gamma_d):
    """Create a pandas DataFrame for the results."""
    data = []
    for i, (vertical, horizontal) in enumerate(combinations):
        desc = get_combination_description(stage, i).replace("<sub>", "").replace("</sub>", "")
        data.append({
            "Combination": desc,
            "Vertical Load (kN/m²)": f"{vertical:.2f}",
            "Horizontal Load (kN/m or kN/m²)": f"{horizontal:.2f}",
            "γ_d": f"{gamma_d:.1f}"
        })
    return pd.DataFrame(data)
    
def download_logo():
    """Download company logo for PDF report."""
    logo_file = None
    for url in [LOGO_URL, FALLBACK_LOGO_URL]:
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                logo_file = "company_logo.png"
                with open(logo_file, 'wb') as f:
                    f.write(response.content)
                break
        except Exception:
            continue
    return logo_file if logo_file and os.path.exists(logo_file) else None

def generate_pdf_report(inputs, results, project_number, project_name):
    """Generate a professional PDF report with company branding and header on all pages."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          leftMargin=15*mm, rightMargin=15*mm,
                          topMargin=20*mm, bottomMargin=15*mm)  # Reduced top margin from 30*mm
    
    styles = getSampleStyleSheet()
    
    # Custom styles (adjusted for single-page fit)
    title_style = ParagraphStyle(
        name='Title',
        parent=styles['Title'],
        fontSize=14,  # Reduced from 16
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=8  # Reduced from 12
    )
    
    subtitle_style = ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    heading1_style = ParagraphStyle(
        name='Heading1',
        parent=styles['Heading1'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10
    )
    
    heading2_style = ParagraphStyle(
        name='Heading2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=8
    )
    
    heading3_style = ParagraphStyle(
        name='Heading3',
        parent=styles['Heading3'],
        fontSize=11,  # Reduced from 12
        spaceAfter=4  # Reduced from 6
    )
    
    normal_style = ParagraphStyle(
        name='Normal',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=8
    )
    
    table_header_style = ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )
    
    table_cell_style = ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=8,  # Reduced from 9
        leading=9,   # Reduced from 11
        alignment=TA_LEFT
    )
    
    table_cell_center_style = ParagraphStyle(
        name='TableCellCenter',
        parent=styles['Normal'],
        fontSize=8,  # Reduced from 9
        leading=9,   # Reduced from 11
        alignment=TA_CENTER
    )
    
    elements = []
    
    # Title and project info
    elements.append(Paragraph("Load Combination Report for Falsework Design", title_style))
    elements.append(Paragraph(f"to AS 3610.2 (Int):2023 - Strength Limit State", subtitle_style))
    
    # Cleaned-up project_info string
    project_info = (
        f"<b>Project:</b> {project_name}<br/>"
        f"<b>Number:</b> {project_number}<br/>"
        f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}"
    )
    elements.append(Paragraph(project_info, normal_style))
    elements.append(Spacer(1, 8*mm))  # Reduced from 15*mm
    
    # Input Parameters section
    elements.append(Paragraph("Input Parameters", heading1_style))
    
    input_data = [
        ["Parameter", "Value", "", "Parameter", "Value"]
    ]
    
    input_params = [
        ("Formwork self-weight (G<sub>f</sub>)", f"{inputs['G_f']:.2f} kN/m²"),
        ("Concrete thickness", f"{inputs['thickness']:.2f} m"),
        ("Reinforcement percentage", f"{inputs['reinforcement_percentage']:.1f}%"),
        ("Concrete load (G<sub>c</sub>)", f"{inputs['G_c']:.2f} kN/m²"),
        ("Workers & equipment - Stage 1 (Q<sub>w1</sub>)", f"{inputs['Q_w1']:.2f} kN/m²"),
        ("Workers & equipment - Stage 2 (Q<sub>w2</sub>)", f"{inputs['Q_w2']:.2f} kN/m²"),
        ("Workers & equipment - Stage 3 (Q<sub>w3</sub>)", f"{inputs['Q_w3']:.2f} kN/m²"),
        ("Stacked materials (Q<sub>m</sub>)", f"{inputs['Q_m']:.2f} kN/m²"),
        ("Horizontal imposed load (Q<sub>h</sub>)", f"{inputs['Q_h']:.2f} kN/m"),
        ("Service wind load (W<sub>s</sub>)", f"{inputs['W_s']:.2f} kN/m²"),
        ("Ultimate wind load (W<sub>u</sub>)", f"{inputs['W_u']:.2f} kN/m²"),
        ("Flowing water load (F_w)", f"{inputs['F_w']:.2f} kN/m²"),
        ("Other actions (Q<sub>x</sub>)", f"{inputs['Q_x']:.2f} kN/m²"),
        ("Lateral concrete pressure (P<sub>c</sub>)", f"{inputs['P_c']:.2f} kN/m²"),
        ("Impact load (I)", f"{inputs['I']:.2f} kN/m²")
    ]
    
    for i in range(0, len(input_params), 2):
        row = []
        row.append(Paragraph(input_params[i][0], table_cell_style))
        row.append(Paragraph(input_params[i][1], table_cell_center_style))
        row.append("")
        if i+1 < len(input_params):
            row.append(Paragraph(input_params[i+1][0], table_cell_style))
            row.append(Paragraph(input_params[i+1][1], table_cell_center_style))
        else:
            row.append("")
            row.append("")
        input_data.append(row)
    
    input_table = Table(input_data, colWidths=[60*mm, 30*mm, 10*mm, 60*mm, 30*mm])
    input_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(input_table)
    # Removed PageBreak()
    
    # Results section
    elements.append(Paragraph("Load Combination Results", heading1_style))
    elements.append(Paragraph("Strength Limit State - AS 3610.2 (Int):2023 Table 3.3.1", subtitle_style))
    elements.append(Spacer(1, 6*mm))  # Reduced from 10*mm
    
    for stage in ["1", "2", "3"]:
        if stage not in results:
            continue
            
        data = results[stage]
        stage_title = f"Stage {stage}: {data['description']}"
        elements.append(Paragraph(stage_title, heading2_style))
        elements.append(Spacer(1, 3*mm))  # Reduced from 5*mm
        
        # Critical Members
        elements.append(Paragraph("Critical Members (γ<sub>d</sub> = 1.3)", heading3_style))
        
        critical_data = [[
            Paragraph("Combination", table_header_style),
            Paragraph("Vertical Load<br/>(kN/m²)", table_header_style),
            Paragraph("Horizontal Load<br/>(kN/m or kN/m²)", table_header_style)
        ]]
        
        for i, (vertical, horizontal) in enumerate(data['critical']):
            desc = get_combination_description(stage, i)
            critical_data.append([
                Paragraph(desc, table_cell_style),
                Paragraph(f"{vertical:.2f}", table_cell_center_style),
                Paragraph(f"{horizontal:.2f}", table_cell_center_style)
            ])
        
        critical_table = Table(critical_data, colWidths=[100*mm, 40*mm, 50*mm])
        critical_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(critical_table)
        elements.append(Spacer(1, 6*mm))  # Reduced from 10*mm
        
        # Non-Critical Members
        elements.append(Paragraph("Non-Critical Members (γ<sub>d</sub> = 1.0)", heading3_style))
        
        non_critical_data = [[
            Paragraph("Combination", table_header_style),
            Paragraph("Vertical Load<br/>(kN/m²)", table_header_style),
            Paragraph("Horizontal Load<br/>(kN/m or kN/m²)", table_header_style)
        ]]
        
        for i, (vertical, horizontal) in enumerate(data['non_critical']):
            desc = get_combination_description(stage, i)
            non_critical_data.append([
                Paragraph(desc, table_cell_style),
                Paragraph(f"{vertical:.2f}", table_cell_center_style),
                Paragraph(f"{horizontal:.2f}", table_cell_center_style)
            ])
        
        non_critical_table = Table(non_critical_data, colWidths=[100*mm, 40*mm, 50*mm])
        non_critical_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(non_critical_table)
        
        # Removed PageBreak()
    
    # Header and Footer drawing function
    def draw_header_footer(canvas, doc):
        canvas.saveState()
        
        # Draw Header
        logo_file = download_logo()
        if logo_file:
            try:
                logo = Image(logo_file, width=40*mm, height=15*mm)
                logo.drawOn(canvas, 15*mm, A4[1] - 25*mm)  # Position logo at top-left
            except:
                pass
        
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(60*mm, A4[1] - 15*mm, COMPANY_NAME)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(60*mm, A4[1] - 20*mm, COMPANY_ADDRESS)
        
        # Draw Footer
        canvas.setFont('Helvetica', 8)
        footer_text = f"{PROGRAM} {PROGRAM_VERSION} | {COMPANY_NAME} © | Page {doc.page}"
        canvas.drawCentredString(A4[0]/2.0, 10*mm, footer_text)
        
        canvas.restoreState()
    
    # Build the document with header and footer on all pages
    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    return buffer

def main():
    st.set_page_config(page_title="Load Combination Calculator", layout="wide")
    
    # Initialize session state to preserve results
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'inputs' not in st.session_state:
        st.session_state.inputs = None
    
    st.title("Load Combination Calculator for AS 3610.2 (Int):2023")
    st.markdown("""
    This calculator generates load combinations for formwork design as per AS 3610.2 (Int):2023, 
    specifically following the Strength Limit State requirements outlined in Table 3.3.1.
    """)
    
    with st.sidebar:
        st.header("Project Details")
        project_number = st.text_input("Project Number", "PRJ-001")
        project_name = st.text_input("Project Name", "Sample Project")
        
        st.header("Basic Parameters")
        G_f = st.number_input("Formwork self-weight (G_f, kN/m²)", value=0.6, step=0.1)
        thickness = st.number_input("Concrete thickness (m)", value=0.2, step=0.05)
        reinforcement_percentage = st.number_input("Reinforcement percentage (%)", value=2.0, step=0.5)
        
        st.header("Load Parameters")
        Q_w1 = st.number_input("Workers & equipment for Stage 1 (Q_w1, kN/m²)", value=1.0, step=0.1)
        Q_w2 = st.number_input("Workers, equipment & placement for Stage 2 (Q_w2, kN/m²)", value=2.0, step=0.1)
        Q_w3 = st.number_input("Workers & equipment for Stage 3 (Q_w3, kN/m²)", value=1.0, step=0.1)
        Q_m = st.number_input("Stacked materials (Q_m, kN/m²)", value=2.5, step=0.1)
        Q_h = st.number_input("Horizontal imposed load (Q_h, kN/m)", value=0.0, step=0.1)
        W_s = st.number_input("Service wind load (W_s, kN/m²)", value=0.0, step=0.1)
        W_u = st.number_input("Ultimate wind load (W_u, kN/m²)", value=0.0, step=0.1)
        F_w = st.number_input("Flowing water load (F_w, kN/m²)", value=0.0, step=0.1)
        Q_x = st.number_input("Other actions (Q_x, kN/m²)", value=0.0, step=0.1)
        P_c = st.number_input("Lateral concrete pressure (P_c, kN/m²)", value=0.0, step=0.1)
        I = st.number_input("Impact load (I, kN/m²)", value=0.0, step=0.1)
        
        if st.button("Calculate Load Combinations"):
            inputs = {
                'G_f': G_f,
                'thickness': thickness,
                'reinforcement_percentage': reinforcement_percentage,
                'G_c': calculate_concrete_load(thickness, reinforcement_percentage),
                'Q_w1': Q_w1,
                'Q_w2': Q_w2,
                'Q_w3': Q_w3,
                'Q_m': Q_m,
                'Q_h': Q_h,
                'W_s': W_s,
                'W_u': W_u,
                'F_w': F_w,
                'Q_x': Q_x,
                'P_c': P_c,
                'I': I
            }
            
            # Compute results
            results = {}
            stages = {
                "1": {"Q_w": Q_w1, "description": "Prior to concrete placement"},
                "2": {"Q_w": Q_w2, "description": "During concrete placement"},
                "3": {"Q_w": Q_w3, "description": "After concrete placement"}
            }

            for stage, data in stages.items():
                Q_w = data["Q_w"]
                
                # Critical Members (γ_d = 1.3)
                critical_combinations = compute_combinations(
                    G_f, inputs['G_c'], Q_w, Q_m, Q_h, W_s, W_u,
                    F_w, Q_x, P_c, I, stage, gamma_d=1.3
                )
                
                # Non-Critical Members (γ_d = 1.0)
                non_critical_combinations = compute_combinations(
                    G_f, inputs['G_c'], Q_w, Q_m, Q_h, W_s, W_u,
                    F_w, Q_x, P_c, I, stage, gamma_d=1.0
                )

                results[stage] = {
                    "description": data["description"],
                    "critical": critical_combinations,
                    "non_critical": non_critical_combinations
                }
            
            # Store in session state
            st.session_state.results = results
            st.session_state.inputs = inputs
    
    # Display results from session state
    if st.session_state.results:
        st.header("Load Combination Results")
        
        for stage in ["1", "2", "3"]:
            if stage not in st.session_state.results:
                continue
                
            data = st.session_state.results[stage]
            st.subheader(f"Stage {stage}: {data['description']}")
            
            # Critical Members
            st.markdown("**Critical Members (γ_d = 1.3)**")
            critical_df = create_results_dataframe(data['critical'], stage, 1.3)
            st.dataframe(critical_df, hide_index=True, use_container_width=True)
            
            # Non-Critical Members
            st.markdown("**Non-Critical Members (γ_d = 1.0)**")
            non_critical_df = create_results_dataframe(data['non_critical'], stage, 1.0)
            st.dataframe(non_critical_df, hide_index=True, use_container_width=True)
        
        # Generate PDF and create download link (without button rerun)
        if st.session_state.inputs and st.session_state.results:
            with st.spinner("Generating PDF report..."):
                pdf_buffer = generate_pdf_report(
                    st.session_state.inputs, 
                    st.session_state.results, 
                    project_number, 
                    project_name
                )
                
                # Create download link that won't rerun the script
                b64 = base64.b64encode(pdf_buffer.getvalue()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="Load_Combination_Report_{project_number}.pdf" style="display: inline-block; padding: 0.5em 1em; background-color: #f63366; color: white; border-radius: 0.5em; text-decoration: none;">Download PDF Report</a>'
                st.markdown(href, unsafe_allow_html=True)

    st.header("Slab Formwork Gridwork Design (LVL Beams)")

    with st.expander("Design Gridwork with LVL Beams"):
        st.markdown("### Input Parameters")

        total_load = st.number_input("Total Design Load (from slab above) in kN/m²", value=10.0)

        st.markdown("#### Secondary LVL Joists")
        sec_size = st.text_input("Size (e.g., 100x63 LVL)", value="100x63")
        sec_spacing = st.number_input("Spacing of secondary LVLs (mm)", value=450)
        sec_span = st.number_input("Span of secondary LVLs (mm)", value=1800)

        st.markdown("#### Main LVL Bearers")
        main_size = st.text_input("Size (e.g., 150x75 LVL)", value="150x75")
        main_spacing = st.number_input("Spacing of main LVLs (mm)", value=1200)
        main_span = st.number_input("Span of main LVLs (mm)", value=2400)

        st.markdown("#### Frame Support")
        frame_spacing = st.number_input("Spacing of frames under main LVLs (mm)", value=1200)

        st.markdown("### Calculations")

        w_sec = total_load * sec_spacing / 1000  # kN/m
        M_sec = w_sec * sec_span**2 / (8 * 1e6)  # kNm

        w_main = w_sec * main_spacing / 1000     # kN/m
        M_main = w_main * main_span**2 / (8 * 1e6)  # kNm

        P_frame = w_main * frame_spacing / 1000  # kN

        st.markdown(f"**Secondary LVL** - Load = {w_sec:.2f} kN/m, Bending Moment = {M_sec:.2f} kNm")
        st.markdown(f"**Main LVL** - Load = {w_main:.2f} kN/m, Bending Moment = {M_main:.2f} kNm")
        st.markdown(f"**Load on Each Frame:** {P_frame:.2f} kN")


if __name__ == "__main__":
    main()
