import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls

SLIDE_NOTES = [
    # Slide 1
    """SLIDE 1: TITLE SLIDE
• Title: TerraRisk AI
• Candidate: MSc in Artificial Intelligence Defense
• Welcome examiners and committee members. Today I present TerraRisk AI, a real-time geotechnical early warning and safe evacuation system.""",

    # Slide 2
    """SLIDE 2: INTRODUCTION — BACKGROUND & MOTIVATION
• The Crisis: Western Ghats steep mountain terrain (>30° slope) combined with extreme monsoon cloudbursts (>250mm/24h) causes high pore water pressure and sudden catastrophic slope collapse.
• Ground Realities: The July 2024 Wayanad disasters showed that whole communities get isolated within minutes.
• The AI Solution: Proactive dynamic prediction at 30-meter spatial resolution, sub-second photo verification to eliminate misinformation, and intelligent routing that keeps evacuees out of the danger perimeter.""",

    # Slide 3
    """SLIDE 3: PROBLEM STATEMENT — THREE SYSTEMIC FLAWS IN CURRENT DISASTER SYSTEMS
• Flaw 1 (Broad & Blind): Warnings are district-wide (>1,000 km²), failing to account for slope angle and 72-hour cumulative rainfall.
• Flaw 2 (Crowd Bottleneck): Emergency centers are overwhelmed by hundreds of unverified calls, old videos, and panic-induced social media rumors without automated triage.
• Flaw 3 (Dangerous Routing): Standard GPS applications (Google Maps) route drivers purely by shortest travel time, often directing fleeing families straight through active landslide zones.""",

    # Slide 4
    """SLIDE 4: AIM & RESEARCH OBJECTIVES
• Primary Aim: Design, implement, and evaluate an end-to-end geotechnical AI system for real-time landslide risk forecasting, multi-tier photo verification, report clustering, and safe navigation.
• Objective 1: Develop physics-guided ML models (Gradient Boosting & XGBoost) on 5 geotechnical parameters.
• Objective 2: Engineer a 3-tier sub-600ms computer vision pipeline to filter non-disaster photos.
• Objective 3: Implement Haversine spatial clustering (<500m) to group citizen reports and auto-verify hazards.
• Objective 4: Deploy dynamic 2 km hazard detour navigation via OSRM and free multi-channel alerting (Telegram, WhatsApp, OASIS CAP v1.2).""",

    # Slide 5
    """SLIDE 5: LITERATURE REVIEW & RESEARCH GAP
• Prior Art: GSI/USGS static susceptibility maps cannot respond to live storms; empirical rainfall curves (Caine, Guzzetti) generate excessive false positives by ignoring slope mechanics; Ushahidi crowd platforms lack automated computer vision verification.
• TerraRisk AI Novelty: An automated, closed-loop pipeline coupling 72-hour rainfall history with geotechnical slope equilibrium, sub-second local edge CV triage, and dynamic danger avoidance routing.""",

    # Slide 6
    """SLIDE 6: PROPOSED SYSTEM — 3-STAGE END-TO-END PIPELINE
• Stage 1 (Ingestion): NASA SRTM 30m digital elevation, Kerala slope/soil layers, Open-Meteo telemetry, and GPS-tagged citizen incident reports.
• Stage 2 (AI Core): XGBoost rainfall forecasting, Gradient Boosting landslide risk regression, 3-tier CV photo triage, and DBSCAN/Haversine clustering.
• Stage 3 (Action): Dynamic 2.0 km danger detour routing via OSRM, live relief camp capacity tracking, zero-cost Telegram/WhatsApp dispatch, and automated Kerala SDMA PDF SitRep reports.""",

    # Slide 7
    """SLIDE 7: METHODOLOGY — HOW THE AI CALCULATES RISK (SIMPLIFIED)
• 3 Core Ingredients: Slope steepness (>30°), 72-hour continuous rain accumulation, and ground water saturation.
• Flatland Safety Rule: If slope < 8° and low elevation, risk is suppressed by 0.08, eliminating coastal plain false alarms.
• Action Thresholds: 4 risk tiers from Safe (<20%) to Emergency Evacuation (>80%).
• Safety Detour: System draws a 2.0 km safety perimeter around active hazards, routing evacuees safely.""",

    # Slide 8
    """SLIDE 8: SYSTEM ARCHITECTURE & WORKFLOW
• Microservice Topology: Modular design connecting Ingestion, AI Brain, Spatial Clustering, and Dispatch layers.
• Performance: End-to-end processing pipeline executes in under 900ms from sensor ingestion to route recalculation and alert dispatch.
• Concurrency: SQLite with Write-Ahead Logging (WAL) ensures lock-free multi-user performance under heavy disaster traffic.""",

    # Slide 9
    """SLIDE 9: TECHNOLOGY STACK
• Machine Learning: Python 3.11, Scikit-Learn (Gradient Boosting), XGBoost, NumPy, Pandas, Pillow (PIL fast convolution), Ollama / Gemini Vision.
• Backend: Flask 3.1, PyJWT role-based authentication, SQLite (WAL mode), ReportLab (PDF generation).
• Frontend: React 19, Vite, Leaflet GIS, Leaflet.heat, Vanilla CSS Glassmorphism design system.
• Dispatch: OSRM Routing Engine, OASIS CAP v1.2 XML feeds, Telegram Bot API, WhatsApp URL scheme.""",

    # Slide 10 (Formerly Slide 13)
    """SLIDE 10: COMPARISON & DISCUSSION
• Comparative Advantages: TerraRisk AI offers 30m precision vs 1,000 km² district alerts; 5-factor geotechnical physics vs static maps; <600ms automated 3-tier photo triage vs manual review; and dynamic 2.0 km danger detours vs shortest-path GPS routing.
• Engineering Trade-offs: Hybrid edge/cloud architecture balances speed (<40ms local edge) and accuracy (<600ms cloud vision). Routing prioritizes life safety over transit speed.""",

    # Slide 11 (Formerly Slide 14)
    """SLIDE 11: CONCLUSION & CONTRIBUTIONS
• Academic Contribution: Demonstrated that coupling geotechnical slope physics with gradient boosting achieves 0.9854 R² accuracy, significantly outperforming traditional empirical methods.
• Operational Contribution: Proved that local edge texture scanning filters 86.4% of false crowd reports in 38ms, preventing emergency center overload.
• Societal Impact: Zero-cost emergency broadcasting via Telegram/WhatsApp and dynamic 2.0 km detours directly preserve human life during extreme monsoonal disasters.""",

    # Slide 12 (Formerly Slide 15)
    """SLIDE 12: FUTURE SCOPE & RESEARCH EXTENSIONS
• Extension 1: Integration of Sentinel-1 InSAR radar interferometry and drone photogrammetry to monitor millimeter-scale slope creep.
• Extension 2: Deployment of solar-powered IoT wireless mesh sensor nodes (MEMS tiltmeters and soil moisture probes) across high-risk mountain hairpins.
• Extension 3: Offline federated learning at shelter edge nodes when telecommunication backhauls are severed.
• Extension 4: Multilingual voice AI synthesis in Malayalam and regional tribal dialects for emergency audio dispatch.""",

    # Slide 13 (Formerly Slide 16)
    """SLIDE 13: REFERENCES & PEER-REVIEWED LITERATURE
• [1] Geological Survey of India (GSI) & KSDMA (2024): Assessment of Chooralmala-Meppadi Debris Flows and Wayanad Landslide Disasters. [https://sdma.kerala.gov.in]
• [2] Caine, N. (1980): The Rainfall Intensity - Duration Control of Shallow Landslides and Debris Flows. Geografiska Annaler. [https://doi.org/10.1080/04353676.1980.11879996]
• [3] Guzzetti, F. et al. (2008): The rainfall intensity–duration control of shallow landslides and debris flows: an update. Landslides. [https://doi.org/10.1007/s10346-007-0112-1]
• [4] Friedman, J. H. (2001): Greedy Function Approximation: A Gradient Boosting Machine. Annals of Statistics. [https://doi.org/10.1214/aos/1013203451]
• [5] Chen, T. & Guestrin, C. (2016): XGBoost: A Scalable Tree Boosting System. ACM SIGKDD. [https://doi.org/10.1145/2939672.2939785]""",

    # Slide 14 (Formerly Slide 17)
    """SLIDE 14: THANK YOU
• Concluding slide: Thank the examination committee and faculty."""
]

def apply_fade_transition(slide):
    """Adds a native smooth fade slide transition animation to the slide."""
    try:
        xml_str = f'<p:transition {nsdecls("p")} spd="med"><p:fade/></p:transition>'
        slide.element.append(parse_xml(xml_str))
    except Exception as e:
        print(f"Warning: Could not add transition: {e}")

def compile_deck():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    captures_dir = os.path.join(base_dir, "presentation_assets", "slide_captures")

    if not os.path.exists(captures_dir):
        print(f"Error: Captures directory does not exist: {captures_dir}")
        sys.exit(1)

    prs = Presentation()
    # 16:9 Widescreen Standard
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Map the 14 slides from the original captures (omitting 10, 11, 12)
    slide_image_indices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17]

    for new_idx, old_idx in enumerate(slide_image_indices, start=1):
        img_filename = f"slide_{old_idx:02d}.png"
        img_path = os.path.join(captures_dir, img_filename)

        if not os.path.exists(img_path):
            print(f"Error: Missing image capture for slide {old_idx}: {img_path}")
            sys.exit(1)

        slide = prs.slides.add_slide(blank_layout)

        # Place image full bleed across 16:9 widescreen canvas
        slide.shapes.add_picture(img_path, Inches(0), Inches(0), width=prs.slide_width, height=prs.slide_height)

        # Add native smooth fade transition
        apply_fade_transition(slide)

        # Add defense speaker notes to the notes slide
        if new_idx - 1 < len(SLIDE_NOTES):
            notes_slide = slide.notes_slide
            tf = notes_slide.notes_text_frame
            tf.text = SLIDE_NOTES[new_idx - 1].strip()

        print(f"Added Slide {new_idx:02d}/14 (source capture: {img_filename}) with notes.")

    # Primary output paths
    out_path = os.path.join(base_dir, "TerraRisk_AI_MSc_AI_Presentation.pptx")
    visual_path = os.path.join(base_dir, "TerraRisk_AI_Presentation_Visual.pptx")

    saved_files = []
    for path in [out_path, visual_path]:
        try:
            prs.save(path)
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"Successfully compiled: {path} ({file_size_mb:.2f} MB)")
            saved_files.append(path)
        except Exception as e:
            print(f"Could not save to {path}: {e}")

    if not saved_files:
        print("Note: Output files could not be overwritten (may be open in PowerPoint).")

    print(f"\nPresentation compilation complete! {len(slide_image_indices)} slides processed.")

if __name__ == "__main__":
    compile_deck()
