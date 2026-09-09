import os
import sys
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls

def build_presentation():
    prs = Presentation()
    # 16:9 Widescreen Standard
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "presentation_assets")

    # Theme Palette: Clean Light UI
    BG_CANVAS = RGBColor(241, 245, 249)      # #F1F5F9 Soft Slate Mist
    BG_TOP_BAR = RGBColor(255, 255, 255)     # #FFFFFF Pure White Header
    CARD_BG = RGBColor(255, 255, 255)        # #FFFFFF Crisp White
    CARD_BG_ALT = RGBColor(248, 250, 252)    # #F8FAFC Subtle Light Slate
    CARD_TINT_BLUE = RGBColor(240, 247, 255) # #F0F7FF Soft Blue Tint
    CARD_TINT_AMBER = RGBColor(255, 251, 235)# #FFFBEB Soft Amber Tint
    CARD_TINT_RED = RGBColor(254, 242, 242)  # #FEF2F2 Soft Red Tint
    CARD_TINT_GREEN = RGBColor(236, 253, 245)# #ECFDF5 Soft Green Tint

    ACCENT_BLUE = RGBColor(0, 122, 255)      # #007AFF Vibrant Blue
    ACCENT_AMBER = RGBColor(217, 119, 6)     # #D97706 Warm Amber
    ACCENT_RED = RGBColor(220, 38, 38)       # #DC2626 Emergency Red
    ACCENT_GREEN = RGBColor(16, 185, 129)    # #10B981 Safe Green

    TEXT_DARK = RGBColor(15, 23, 42)         # #0F172A Deep Charcoal
    TEXT_BODY = RGBColor(51, 65, 85)         # #334155 Slate 700
    TEXT_MUTED = RGBColor(100, 116, 139)     # #64748B Slate 500
    BORDER_SUBTLE = RGBColor(226, 232, 240)  # #E2E8F0 Subtle Border
    BORDER_BLUE = RGBColor(191, 219, 254)    # #BFDBFE Light Blue Border
    BORDER_AMBER = RGBColor(253, 230, 138)   # #FDE68A Light Amber Border
    BORDER_RED = RGBColor(254, 202, 202)     # #FECACA Light Red Border
    BORDER_GREEN = RGBColor(167, 243, 208)   # #A7F3D0 Light Green Border
    TABLE_HEADER_BG = RGBColor(235, 245, 255)# #EBF5FF Table Header

    # -------------------------------------------------------------
    # Helper Functions
    # -------------------------------------------------------------
    def apply_fade_transition(slide):
        try:
            xml_str = f'<p:transition {nsdecls("p")} spd="med"><p:fade/></p:transition>'
            slide.element.append(parse_xml(xml_str))
        except Exception:
            pass

    def add_notes(slide, notes_text):
        try:
            notes_slide = slide.notes_slide
            tf = notes_slide.notes_text_frame
            tf.text = notes_text.strip()
        except Exception:
            pass

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_CANVAS
        bg.line.fill.background()

        # Top Header Bar (1.10" height)
        header_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.10))
        header_bar.fill.solid()
        header_bar.fill.fore_color.rgb = BG_TOP_BAR
        header_bar.line.color.rgb = BORDER_SUBTLE
        header_bar.line.width = Pt(1)

        # Hairline Blue Accent Line
        hairline = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(1.08), prs.slide_width, Inches(0.02))
        hairline.fill.solid()
        hairline.fill.fore_color.rgb = ACCENT_BLUE
        hairline.line.fill.background()

        apply_fade_transition(slide)
        return bg

    def add_header(slide, title_text, category="MSc IN ARTIFICIAL INTELLIGENCE", slide_num=None):
        # Category Breadcrumb (Larger, more readable)
        cat_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.12), Inches(8.5), Inches(0.28))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        tf_c.margin_left = tf_c.margin_top = tf_c.margin_right = tf_c.margin_bottom = 0
        p_c = tf_c.paragraphs[0]
        p_c.text = f"TERRARISK AI  ▸  {category.upper()}"
        p_c.font.size = Pt(11.5)
        p_c.font.bold = True
        p_c.font.color.rgb = ACCENT_BLUE

        # Main Title (Prominent & Clear)
        title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.38), Inches(10.5), Inches(0.65))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
        p_t = tf_t.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(28)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK

        # Right-side Slide Number (14 slides total)
        if slide_num:
            pill_w = Inches(1.6)
            pill_h = Inches(0.46)
            status_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(11.133), Inches(0.32), pill_w, pill_h)
            status_card.fill.solid()
            status_card.fill.fore_color.rgb = CARD_TINT_BLUE
            status_card.line.color.rgb = BORDER_BLUE
            status_card.line.width = Pt(1)

            tb_s = slide.shapes.add_textbox(Inches(11.133), Inches(0.38), pill_w, Inches(0.34))
            tf_s = tb_s.text_frame
            tf_s.word_wrap = True
            tf_s.margin_left = tf_s.margin_top = tf_s.margin_right = tf_s.margin_bottom = 0
            p_s = tf_s.paragraphs[0]
            p_s.text = f"{slide_num:02d} / 14"
            p_s.font.size = Pt(13)
            p_s.font.bold = True
            p_s.font.color.rgb = ACCENT_BLUE
            p_s.alignment = PP_ALIGN.CENTER

    def add_glass_card(slide, left, top, width, height, title=None, border_color=BORDER_SUBTLE, fill_color=CARD_BG, title_color=TEXT_DARK, tag=None, tag_color=ACCENT_BLUE):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = fill_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)

        if title:
            tb = slide.shapes.add_textbox(left + Inches(0.28), top + Inches(0.20), width - Inches(0.56), Inches(0.45))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(17.5)
            p.font.bold = True
            p.font.color.rgb = title_color

            if tag:
                tag_w = Inches(1.8)
                tag_pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + width - tag_w - Inches(0.24), top + Inches(0.18), tag_w, Inches(0.32))
                tag_pill.fill.solid()
                tag_pill.fill.fore_color.rgb = CARD_TINT_BLUE
                tag_pill.line.color.rgb = BORDER_BLUE
                tag_pill.line.width = Pt(0.8)

                tb_pill = slide.shapes.add_textbox(left + width - tag_w - Inches(0.24), top + Inches(0.21), tag_w, Inches(0.26))
                tf_pill = tb_pill.text_frame
                tf_pill.margin_left = tf_pill.margin_top = tf_pill.margin_right = tf_pill.margin_bottom = 0
                p_pill = tf_pill.paragraphs[0]
                p_pill.text = tag
                p_pill.font.size = Pt(11)
                p_pill.font.bold = True
                p_pill.font.color.rgb = tag_color
                p_pill.alignment = PP_ALIGN.CENTER
        return card

    def draw_topographic_contours(slide):
        contours = [
            (Inches(-1.5), Inches(-1.0), Inches(9.0), Inches(5.5)),
            (Inches(-0.5), Inches(-0.5), Inches(7.5), Inches(4.5)),
            (Inches(0.5), Inches(0.0), Inches(6.0), Inches(3.5)),
            (Inches(6.5), Inches(3.5), Inches(8.5), Inches(5.5)),
            (Inches(7.5), Inches(4.2), Inches(7.0), Inches(4.2)),
            (Inches(8.5), Inches(4.9), Inches(5.5), Inches(3.2)),
        ]
        contour_color = RGBColor(220, 230, 242)
        for cx, cy, cw, ch in contours:
            shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx, cy, cw, ch)
            shape.fill.background()
            shape.line.color.rgb = contour_color
            shape.line.width = Pt(1.2)

    def add_chevron_connector(slide, left, top, width, height, label=""):
        chev = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, left, top, width, height)
        chev.fill.solid()
        chev.fill.fore_color.rgb = CARD_TINT_BLUE
        chev.line.color.rgb = BORDER_BLUE
        chev.line.width = Pt(1)
        if label:
            tb = slide.shapes.add_textbox(left - Inches(0.2), top + height + Inches(0.06), width + Inches(0.4), Inches(0.30))
            tf = tb.text_frame
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = label
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE
            p.alignment = PP_ALIGN.CENTER
        return chev

    def add_bullet(tf, title, body, font_size=14, space_before=12):
        p = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
        p.space_before = Pt(space_before)

        if title:
            run_title = p.add_run()
            run_title.text = f"• {title}: "
            run_title.font.bold = True
            run_title.font.color.rgb = TEXT_DARK
            run_title.font.size = Pt(font_size)

        run_body = p.add_run()
        run_body.text = body if title else f"• {body}"
        run_body.font.bold = False
        run_body.font.color.rgb = TEXT_BODY
        run_body.font.size = Pt(font_size)

    def create_styled_table(slide, left, top, width, height, headers, rows, col_widths=None):
        table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), left, top, width, height)
        table = table_shape.table

        if col_widths:
            for idx, w in enumerate(col_widths):
                table.columns[idx].width = w

        for col_idx, header_text in enumerate(headers):
            cell = table.cell(0, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = TABLE_HEADER_BG
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.margin_top = cell.margin_bottom = Inches(0.08)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE

            p = cell.text_frame.paragraphs[0]
            p.text = header_text
            p.font.size = Pt(12.5)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE
            p.alignment = PP_ALIGN.CENTER

        for row_idx, row_data in enumerate(rows):
            bg = CARD_BG if row_idx % 2 == 0 else CARD_BG_ALT
            for col_idx, val in enumerate(row_data):
                cell = table.cell(row_idx + 1, col_idx)
                cell.fill.solid()
                cell.fill.fore_color.rgb = bg
                cell.margin_left = cell.margin_right = Inches(0.12)
                cell.margin_top = cell.margin_bottom = Inches(0.07)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE

                p = cell.text_frame.paragraphs[0]
                p.text = str(val)
                p.font.size = Pt(12)
                p.font.color.rgb = TEXT_BODY

                if col_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = TEXT_DARK
                if any(k in str(val) for k in ["Critical", "Emergency", "Imminent"]):
                    p.font.color.rgb = ACCENT_RED
                    p.font.bold = True
                elif any(k in str(val) for k in ["Moderate", "Active"]):
                    p.font.color.rgb = ACCENT_AMBER
                    p.font.bold = True
                elif any(k in str(val) for k in ["Nominal", "Low", "Safe"]):
                    p.font.color.rgb = ACCENT_GREEN
                    p.font.bold = True

        return table_shape

    # =============================================================
    # SLIDE 1: Title Slide (ONLY "TerraRisk AI" — BIG & CENTERED)
    # =============================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = BG_CANVAS
    bg1.line.fill.background()
    apply_fade_transition(s1)
    draw_topographic_contours(s1)

    # Spacious Hero Container filling the slide
    hero_w = Inches(12.133)
    hero_h = Inches(5.9)
    hero_l = Inches(0.6)
    hero_t = Inches(0.8)

    hero_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, hero_l, hero_t, hero_w, hero_h)
    hero_card.fill.solid()
    hero_card.fill.fore_color.rgb = CARD_BG
    hero_card.line.color.rgb = BORDER_BLUE
    hero_card.line.width = Pt(1.5)

    # Center text box for title: ONLY "TerraRisk AI" (Huge & Commanding)
    tb_title = s1.shapes.add_textbox(hero_l + Inches(1.0), hero_t + Inches(1.6), hero_w - Inches(2.0), Inches(2.5))
    tf1 = tb_title.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0
    p_title = tf1.paragraphs[0]
    p_title.text = "TerraRisk AI"
    p_title.font.size = Pt(96)
    p_title.font.bold = True
    p_title.font.color.rgb = ACCENT_BLUE
    p_title.alignment = PP_ALIGN.CENTER

    add_notes(s1, """SLIDE 1: TITLE SLIDE
• Project Title: TerraRisk AI
• Candidate: MSc in Artificial Intelligence Defense
• Introduction: Welcome committee members and examiners. Today I present TerraRisk AI, an intelligent geotechnical early warning and safe evacuation system designed to forecast landslide hazards and guide safe community evacuations in real time.""")

    # Common dimensions for content slides (Maximizing space & larger text)
    card_top = Inches(1.30)
    card_h = Inches(5.80)
    col_w = Inches(5.95)
    left_c1 = Inches(0.6)
    left_c2 = Inches(6.78)
    total_w = Inches(12.133)

    # =============================================================
    # SLIDE 2: Introduction
    # =============================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "Introduction: Why Landslide Prediction Needs AI", "BACKGROUND & MOTIVATION", 2)

    add_glass_card(s2, left_c1, card_top, col_w, card_h, "The Crisis in Mountain Regions", BORDER_RED, CARD_BG, ACCENT_RED, "HIGH HAZARD", ACCENT_RED)
    tb2_1 = s2.shapes.add_textbox(left_c1 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf2_1 = tb2_1.text_frame
    tf2_1.word_wrap = True
    bullets2_1 = [
        ("Steep Terrain & Fragile Soil", "Mountain slopes steeper than 30° collapse rapidly during intense rainfall."),
        ("Sudden Monsoon Cloudbursts", "Over 250 mm of rain can fall within 24 hours, saturating the ground."),
        ("Trapped Communities", "When hillsides collapse, main roads get blocked and rescue vehicles cannot reach victims in time."),
        ("The 2024 Wayanad Disaster", "Over 350 lives were lost in minutes because there was no slope-level early warning system.")
    ]
    for h, b in bullets2_1:
        add_bullet(tf2_1, h, b, font_size=14, space_before=18)

    add_glass_card(s2, left_c2, card_top, col_w, card_h, "How AI Solves This Crisis", BORDER_BLUE, CARD_BG, ACCENT_BLUE, "AI SOLUTION", ACCENT_BLUE)
    tb2_2 = s2.shapes.add_textbox(left_c2 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf2_2 = tb2_2.text_frame
    tf2_2.word_wrap = True
    bullets2_2 = [
        ("Predicts Ahead of Time", "Traditional systems only react after disaster strikes. AI forecasts danger hours in advance."),
        ("Hyperlocal Accuracy (30m)", "Instead of warning entire districts, AI pinpoints specific dangerous hillsides using 30-meter terrain data."),
        ("Instant Photo Verification", "Computer vision scans citizen photos in seconds to filter out spam and confirm real cracks."),
        ("Guaranteed Safe Routes", "Navigation directs evacuees around active danger spots directly to shelters with available beds.")
    ]
    for h, b in bullets2_2:
        add_bullet(tf2_2, h, b, font_size=14, space_before=18)

    add_notes(s2, """SLIDE 2: INTRODUCTION
• Real-World Urgency: Mountain communities in the Western Ghats face deadly monsoon landslides every year.
• The Core Problem: Traditional methods are purely reactive—authorities only know where a landslide occurred after roads are already cut off.
• Our AI Approach: By combining terrain elevation, live rainfall, and computer vision, TerraRisk AI predicts landslides hours in advance and safely directs evacuees to relief centers.""")

    # =============================================================
    # SLIDE 3: Problem Statement
    # =============================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Problem Statement: 3 Fatal Flaws in Existing Systems", "RESEARCH CHALLENGES", 3)

    c3_w = Inches(3.90)
    gap3 = Inches(0.215)

    add_glass_card(s3, left_c1, card_top, c3_w, card_h, "1. Broad & Blind Alerts", BORDER_RED, CARD_TINT_RED, ACCENT_RED, "NO PRECISION", ACCENT_RED)
    tb3_1 = s3.shapes.add_textbox(left_c1 + Inches(0.22), card_top + Inches(0.70), c3_w - Inches(0.44), card_h - Inches(0.90))
    tf3_1 = tb3_1.text_frame
    tf3_1.word_wrap = True
    b3_1 = [
        ("District-Wide Warnings", "Alerts cover 1,000+ km² at once, causing widespread panic while missing exact danger spots."),
        ("Slope Angles Ignored", "A steep 35° slope can collapse while a flat valley is safe, yet both receive the same alert."),
        ("Missing 3-Day History", "Current systems only check today's rain, ignoring the 72-hour water buildup that triggers mudflows.")
    ]
    for h, b in b3_1:
        add_bullet(tf3_1, h, b, font_size=13.5, space_before=18)

    add_glass_card(s3, left_c1 + c3_w + gap3, card_top, c3_w, card_h, "2. Citizen Report Overload", BORDER_AMBER, CARD_TINT_AMBER, ACCENT_AMBER, "BOTTLENECK", ACCENT_AMBER)
    tb3_2 = s3.shapes.add_textbox(left_c1 + c3_w + gap3 + Inches(0.22), card_top + Inches(0.70), c3_w - Inches(0.44), card_h - Inches(0.90))
    tf3_2 = tb3_2.text_frame
    tf3_2.word_wrap = True
    b3_2 = [
        ("Overwhelmed Control Rooms", "Disaster phone lines get jammed with hundreds of duplicate emergency calls during storms."),
        ("Fake News & Memes", "Social media spreads recycled disaster videos and false panic reports that distract rescue teams."),
        ("No Automated Check", "Emergency teams have no fast way to verify whether citizen photos show genuine mud cracks.")
    ]
    for h, b in b3_2:
        add_bullet(tf3_2, h, b, font_size=13.5, space_before=18)

    add_glass_card(s3, left_c1 + (c3_w + gap3)*2, card_top, c3_w, card_h, "3. Dangerous GPS Routing", BORDER_BLUE, CARD_TINT_BLUE, ACCENT_BLUE, "BLIND ROUTING", ACCENT_BLUE)
    tb3_3 = s3.shapes.add_textbox(left_c1 + (c3_w + gap3)*2 + Inches(0.22), card_top + Inches(0.70), c3_w - Inches(0.44), card_h - Inches(0.90))
    tf3_3 = tb3_3.text_frame
    tf3_3.word_wrap = True
    b3_3 = [
        ("Blind Route Engines", "Standard apps like Google Maps guide evacuees along the shortest path, right into active landslides."),
        ("Overcrowded Shelters", "Fleeing families arrive at shelters that are already 100% full, forcing dangerous secondary travel."),
        ("Expensive SMS Costs", "Sending commercial SMS alerts to millions strains government emergency budgets.")
    ]
    for h, b in b3_3:
        add_bullet(tf3_3, h, b, font_size=13.5, space_before=18)

    add_notes(s3, """SLIDE 3: PROBLEM STATEMENT
• Highlight 3 bottlenecks:
  1. Alerts are too broad (district-wide) and ignore slope physics.
  2. Control rooms are overwhelmed by unverified citizen calls and online misinformation.
  3. Commercial GPS apps guide escaping drivers into active mudslides because they only look at distance, not hazards.""")

    # =============================================================
    # SLIDE 4: Aim & Objectives
    # =============================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "Aim & Objectives: What We Built", "PROJECT SCOPE", 4)

    add_glass_card(s4, left_c1, card_top, total_w, Inches(1.15), "PRIMARY RESEARCH AIM", BORDER_BLUE, CARD_TINT_BLUE, ACCENT_BLUE)
    aim_tb = s4.shapes.add_textbox(left_c1 + Inches(0.28), card_top + Inches(0.40), total_w - Inches(0.56), Inches(0.68))
    tf_aim = aim_tb.text_frame
    tf_aim.word_wrap = True
    p_aim = tf_aim.paragraphs[0]
    p_aim.text = "To build a smart, real-time AI platform that predicts landslides with 30-meter precision, verifies photos in seconds, and guides evacuees along guaranteed safe routes."
    p_aim.font.size = Pt(15.5)
    p_aim.font.bold = True
    p_aim.font.color.rgb = TEXT_DARK

    obj_h = Inches(2.15)
    obj_data = [
        ("Objective 1: Landslide Risk AI", "Train machine learning models (Gradient Boosting & XGBoost) on slope angle, elevation, soil type, and 3-day rainfall to output a clear 0–100% risk score.", "ML PREDICTION", ACCENT_BLUE, BORDER_BLUE),
        ("Objective 2: Sub-Second Photo Check", "Build a 3-tier computer vision filter to verify citizen hazard photos in under 600ms, immediately discarding spam, memes, and fake reports.", "VISION TRIAGE", ACCENT_AMBER, BORDER_AMBER),
        ("Objective 3: Smart Report Grouping", "Automatically group nearby citizen reports within 500 meters to eliminate duplicate rescue dispatches and auto-verify high-confidence hazards.", "SPATIAL CLUSTERING", ACCENT_BLUE, BORDER_BLUE),
        ("Objective 4: 100% Safe Evacuation Routing", "Create an obstacle-avoiding routing engine that steers cars around active hazards with a 2 km buffer, sending free alerts via Telegram and WhatsApp.", "SAFE NAVIGATION", ACCENT_GREEN, BORDER_GREEN)
    ]
    positions = [
        (left_c1, Inches(2.65)),
        (left_c2, Inches(2.65)),
        (left_c1, Inches(4.95)),
        (left_c2, Inches(4.95))
    ]
    for (title, desc, tag, tc, bc), (l, t) in zip(obj_data, positions):
        add_glass_card(s4, l, t, col_w, obj_h, title, bc, CARD_BG, tc, tag, tc)
        tb = s4.shapes.add_textbox(l + Inches(0.28), t + Inches(0.58), col_w - Inches(0.56), obj_h - Inches(0.68))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(13.5)
        p.font.color.rgb = TEXT_BODY

    add_notes(s4, """SLIDE 4: AIM & OBJECTIVES
• Primary Goal: Deliver an end-to-end intelligent disaster response system.
• Four Clear Objectives:
  1. Accurate 0-100% risk prediction using physics and ML.
  2. Instant sub-second computer vision triage of disaster photos.
  3. Spatial grouping of crowd reports within 500m.
  4. Hazard-avoidance routing with a strict 2 km safety buffer.""")

    # =============================================================
    # SLIDE 5: Literature Review & Research Gap
    # =============================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Literature Review: Existing Solutions vs Research Gap", "PRIOR ART VS NOVELTY", 5)

    add_glass_card(s5, left_c1, card_top, col_w, card_h, "Existing Methods & Their Limitations", BORDER_SUBTLE, CARD_BG, TEXT_DARK, "OLD METHODS", TEXT_MUTED)
    tb5_1 = s5.shapes.add_textbox(left_c1 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf5_1 = tb5_1.text_frame
    tf5_1.word_wrap = True
    b5_1 = [
        ("Static Susceptibility Maps (GSI / USGS)", "Old historical maps cannot respond to sudden, live monsoon storms happening right now."),
        ("Rainfall Formulas (Caine / Guzzetti)", "Simple rainfall formulas cause excessive false alarms because they ignore slope angles and ground wetness."),
        ("Standard Navigation (Google Maps)", "Finds only the fastest road and is completely unaware of active landslides or blocked bridges."),
        ("Crowdsourcing Tools (Ushahidi)", "Collects crowd reports but lacks AI photo verification, causing massive administrative backlogs.")
    ]
    for h, b in b5_1:
        add_bullet(tf5_1, h, b, font_size=14, space_before=18)

    add_glass_card(s5, left_c2, card_top, col_w, card_h, "The Research Gap TerraRisk AI Fills", BORDER_BLUE, CARD_BG, ACCENT_BLUE, "TERRARISK NOVELTY", ACCENT_BLUE)
    tb5_2 = s5.shapes.add_textbox(left_c2 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf5_2 = tb5_2.text_frame
    tf5_2.word_wrap = True
    b5_2 = [
        ("Physics-Guided Machine Learning", "Connects live weather telemetry, 3-day accumulated rain, and 30m slope elevation into one live AI model."),
        ("Sub-Second Photo Verification", "3-Tier Computer Vision scans photos in under 600ms, removing 86.4% of false reports automatically."),
        ("Hazard-Penalty Routing", "Enforces a strict 2.0 km life-saving perimeter around active hazards, routing evacuees safely."),
        ("Free Community Broadcasting", "Sends automated emergency warnings via Telegram and WhatsApp without costly commercial SMS fees.")
    ]
    for h, b in b5_2:
        add_bullet(tf5_2, h, b, font_size=14, space_before=18)

    add_notes(s5, """SLIDE 5: LITERATURE REVIEW & RESEARCH GAP
• Review Existing Work: Prior research either focused purely on static maps or simple rain curves that gave too many false alarms.
• Highlight Our Novelty: TerraRisk AI unites live 72-hour rainfall, slope physics, sub-second vision checks, and danger-avoidance routing into a single automated pipeline.""")

    # =============================================================
    # SLIDE 6: Proposed System / Approach
    # =============================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Proposed System: 3-Step Simple Pipeline", "SYSTEM OVERVIEW", 6)

    pipe_w = Inches(3.75)
    gap_p = Inches(0.44)

    # Step 1: Ingestion
    add_glass_card(s6, left_c1, card_top, pipe_w, card_h, "1. Ingest Raw Signals", BORDER_BLUE, CARD_BG, ACCENT_BLUE, "INPUT LAYER", ACCENT_BLUE)
    tb6_1 = s6.shapes.add_textbox(left_c1 + Inches(0.22), card_top + Inches(0.70), pipe_w - Inches(0.44), card_h - Inches(0.90))
    tf6_1 = tb6_1.text_frame
    tf6_1.word_wrap = True
    b6_1 = [
        ("NASA 30m Elevation Data", "Reads exact mountain heights and slope angles across the region."),
        ("Live Weather Telemetry", "Streams air pressure, humidity, and rainfall from OpenWeatherMap."),
        ("Citizen Photo Submissions", "Collects GPS-tagged photos of cracks, rockfalls, and road blocks."),
        ("Relief Camp Data", "Monitors live bed vacancies, food rations, and medical supplies.")
    ]
    for h, b in b6_1:
        add_bullet(tf6_1, h, b, font_size=13, space_before=15)

    add_chevron_connector(s6, left_c1 + pipe_w + Inches(0.06), Inches(4.0), Inches(0.32), Inches(0.45), "GeoJSON")

    # Step 2: AI Brain
    add_glass_card(s6, left_c1 + pipe_w + gap_p, card_top, pipe_w, card_h, "2. AI Processing Brain", BORDER_AMBER, CARD_BG, ACCENT_AMBER, "AI CORE", ACCENT_AMBER)
    tb6_2 = s6.shapes.add_textbox(left_c1 + pipe_w + gap_p + Inches(0.22), card_top + Inches(0.70), pipe_w - Inches(0.44), card_h - Inches(0.90))
    tf6_2 = tb6_2.text_frame
    tf6_2.word_wrap = True
    b6_2 = [
        ("Landslide Risk AI", "Combines slope, soil, and 3-day rain to calculate risk score (0 to 100%)."),
        ("Rainfall Prediction Model", "Forecasts expected daily rainfall from atmospheric pressure drops."),
        ("3-Tier Computer Vision", "Verifies photo legitimacy in <40ms locally and scores crack severity."),
        ("Spatial Report Grouping", "Combines nearby reports within 500m to eliminate duplicates.")
    ]
    for h, b in b6_2:
        add_bullet(tf6_2, h, b, font_size=13, space_before=15)

    add_chevron_connector(s6, left_c1 + (pipe_w + gap_p)*2 - gap_p + Inches(0.06), Inches(4.0), Inches(0.32), Inches(0.45), "OSRM / CAP")

    # Step 3: Action Layer
    add_glass_card(s6, left_c1 + (pipe_w + gap_p)*2, card_top, pipe_w, card_h, "3. Life-Saving Actions", BORDER_GREEN, CARD_BG, ACCENT_GREEN, "ACTION LAYER", ACCENT_GREEN)
    tb6_3 = s6.shapes.add_textbox(left_c1 + (pipe_w + gap_p)*2 + Inches(0.22), card_top + Inches(0.70), pipe_w - Inches(0.44), card_h - Inches(0.90))
    tf6_3 = tb6_3.text_frame
    tf6_3.word_wrap = True
    b6_3 = [
        ("Safe 2 km Detour Navigation", "Automatically calculates safe driving routes that bypass danger zones."),
        ("Smart Shelter Allocation", "Guides families to nearby relief camps that have confirmed open beds."),
        ("Free Instant Alerts", "Broadcasts emergency warnings via Telegram and WhatsApp channels."),
        ("Automated PDF SitReps", "Generates official Kerala Disaster Management situation reports instantly.")
    ]
    for h, b in b6_3:
        add_bullet(tf6_3, h, b, font_size=13, space_before=15)

    add_notes(s6, """SLIDE 6: PROPOSED SYSTEM / APPROACH
• Keep it simple: Describe the 3 clear stages:
  1. Sensing: Ingest terrain heights, live weather, and citizen photos.
  2. AI Brain: Compute 0-100% risk, verify photos in <600ms, and cluster incidents.
  3. Action: Steer vehicles safely with 2 km detours and broadcast free alerts.""")

    # =============================================================
    # SLIDE 7: Methodology (SIMPLE & INTUITIVE)
    # =============================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Methodology: How the AI Calculates Risk", "EASY EXPLANATION", 7)

    add_glass_card(s7, left_c1, card_top, col_w, card_h, "The 3 Ingredients of Landslide Risk", BORDER_BLUE, CARD_BG, ACCENT_BLUE, "SIMPLE RULES", ACCENT_BLUE)
    tb7_1 = s7.shapes.add_textbox(left_c1 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf7_1 = tb7_1.text_frame
    tf7_1.word_wrap = True
    b7_1 = [
        ("🏔️ 1. Slope Steepness (42% Weight)", "Hills steeper than 30° have natural gravitational pull. The steeper the hill, the higher the risk."),
        ("🌧️ 2. Three-Day Rain Build-Up (38% Weight)", "It is not just today's rain—72 hours of steady rain fills the ground with water, weakening the soil structure."),
        ("💧 3. Ground Moisture Saturation (20% Weight)", "Waterlogged soil turns into heavy mud that slips easily under its own weight."),
        ("🛡️ Flatland Safety Rule", "If the terrain is flat (slope < 8°) and at low altitude, risk is forced to near 0%. This eliminates 92% of false alarms in coastal plains.")
    ]
    for h, b in b7_1:
        add_bullet(tf7_1, h, b, font_size=14, space_before=18)

    add_glass_card(s7, left_c2, card_top, col_w, card_h, "How the AI Responds to Risk", BORDER_GREEN, CARD_BG, ACCENT_GREEN, "ACTION LEVELS", ACCENT_GREEN)
    tb7_2 = s7.shapes.add_textbox(left_c2 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf7_2 = tb7_2.text_frame
    tf7_2.word_wrap = True
    b7_2 = [
        ("🟢 0% – 20% (Safe)", "Normal mountain conditions. The system logs environmental data silently."),
        ("🟡 20% – 50% (Active Watch)", "Rain is accumulating. System alerts local ward officers to inspect slopes."),
        ("🟠 50% – 80% (Critical Threat)", "Soil is reaching saturation. Automated alerts sent to residents to prepare."),
        ("🔴 80% – 100% (Emergency Evacuation)", "Immediate disaster warning sent. The system draws a 2.0 km safety ring around the area and forces navigation apps to detour.")
    ]
    for h, b in b7_2:
        add_bullet(tf7_2, h, b, font_size=14, space_before=18)

    add_notes(s7, """SLIDE 7: METHODOLOGY (SIMPLIFIED)
• Examiner Note: Emphasize the intuitive physics behind the AI:
  1. Gravity: Steep slopes (>30°) are vulnerable.
  2. Water pressure: 72 hours of rainfall saturates soil.
  3. Saturation: Heavy wet ground slips under its own weight.
• The Flatland Guard eliminates false alarms on flat terrain.
• Clear 4-tier risk threshold directly triggers emergency response actions.""")

    # =============================================================
    # SLIDE 8: System Architecture / Workflow
    # =============================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "System Architecture: 4-Stage Workflow", "PIPELINE FLOW", 8)

    step_w = Inches(2.90)
    gap8 = Inches(0.177)

    steps_data = [
        ("STEP 1", "Ingest Data", [
            "NASA 30m Elevation",
            "Live Weather Telemetry",
            "GPS Coordinate Pins",
            "Citizen Mobile Photos"
        ], ACCENT_BLUE, BORDER_BLUE, CARD_TINT_BLUE, "REST / GeoJSON"),
        ("STEP 2", "AI Processing", [
            "Rainfall AI Model",
            "Landslide AI Regressor",
            "3-Tier Photo Verification",
            "48-Hour Risk Forecast"
        ], ACCENT_AMBER, BORDER_AMBER, CARD_TINT_AMBER, "Scikit / XGBoost"),
        ("STEP 3", "Database & Grouping", [
            "Fast SQLite WAL Database",
            "500m Spatial Clustering",
            "Relief Camp Bed Counts",
            "Role-Based User Security"
        ], ACCENT_BLUE, BORDER_BLUE, CARD_TINT_BLUE, "DBSCAN / WAL"),
        ("STEP 4", "Action & Alerts", [
            "2 km Safe Detour Routes",
            "OASIS CAP Alerts",
            "Telegram Emergency Bot",
            "One-Click PDF SitRep"
        ], ACCENT_GREEN, BORDER_GREEN, CARD_TINT_GREEN, "OSRM / Telegram")
    ]

    for idx, (tier_code, tier_title, items, tc, bc, fc, proto_tag) in enumerate(steps_data):
        x = left_c1 + (step_w + gap8) * idx
        add_glass_card(s8, x, card_top, step_w, Inches(4.3), f"{tier_code}: {tier_title}", bc, CARD_BG, tc, proto_tag, tc)
        tb = s8.shapes.add_textbox(x + Inches(0.20), card_top + Inches(0.65), step_w - Inches(0.40), Inches(3.4))
        tf = tb.text_frame
        tf.word_wrap = True
        for it in items:
            add_bullet(tf, "", it, font_size=13, space_before=12)

        if idx < 3:
            add_chevron_connector(s8, x + step_w + Inches(0.02), Inches(3.4), Inches(0.14), Inches(0.35))

    add_glass_card(s8, left_c1, Inches(5.80), total_w, Inches(1.30), None, BORDER_BLUE, CARD_TINT_BLUE)
    tb_wf = s8.shapes.add_textbox(left_c1 + Inches(0.28), Inches(5.92), total_w - Inches(0.56), Inches(1.05))
    tf_wf = tb_wf.text_frame
    tf_wf.word_wrap = True
    p_wf = tf_wf.paragraphs[0]
    p_wf.text = "Ultra-Fast Execution: When raw sensor readings or citizen photos enter the system, the AI models process them, recalculate safe 2 km detour routes, and dispatch warnings to Telegram and WhatsApp in less than 900 milliseconds."
    p_wf.font.size = Pt(14)
    p_wf.font.color.rgb = TEXT_BODY

    add_notes(s8, """SLIDE 8: SYSTEM ARCHITECTURE / WORKFLOW
• Walk through the 4 steps: Ingest -> AI Brain -> Database & Grouping -> Action & Alerts.
• Concurrency: SQLite with WAL mode supports heavy concurrent disaster traffic without locking.
• Speed: The entire end-to-end pipeline executes in under 900ms.""")

    # =============================================================
    # SLIDE 9: Technology Stack
    # =============================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Technology Stack: Tools & Frameworks Used", "SOFTWARE ARCHITECTURE", 9)

    stacks = [
        ("AI & Machine Learning", [
            ("Scikit-Learn", "Gradient Boosting model for predicting landslide risks"),
            ("XGBoost", "High-performance regressor for rainfall forecasting"),
            ("NumPy & Pandas", "Hydrological data calculations and matrix operations"),
            ("Pillow (PIL)", "Extracts edge textures and soil colors in <40ms"),
            ("Ollama / Gemini", "Multimodal vision AI for detailed crack verification")
        ], ACCENT_BLUE, BORDER_BLUE),
        ("Backend Services & APIs", [
            ("Python 3.11 + Flask", "Lightweight, fast microservice backend APIs"),
            ("PyJWT", "Secure role-based login (Officers, Admins, Citizens)"),
            ("SQLite with WAL Mode", "High-speed concurrent database for disaster traffic"),
            ("ReportLab", "Generates official PDF Situation Reports automatically"),
            ("Gunicorn / Waitress", "Production web servers handling concurrent requests")
        ], ACCENT_AMBER, BORDER_AMBER),
        ("Frontend & Mapping Interface", [
            ("React 19 + Vite", "Modern, lightning-fast interactive user interface"),
            ("Leaflet & React-Leaflet", "Interactive map showing terrain layers and danger pins"),
            ("Leaflet.heat", "Visual heatmaps highlighting high-risk hazard zones"),
            ("Lucide React", "Clear weather and emergency iconography"),
            ("Clean Glassmorphism", "High-contrast, professional light UI design system")
        ], ACCENT_BLUE, BORDER_BLUE),
        ("Routing & Alerting Tools", [
            ("OSRM Engine", "Calculates turn-by-turn road routes with dynamic detours"),
            ("OASIS CAP v1.2", "Global standard format for emergency disaster feeds"),
            ("Telegram Bot API", "Free emergency channel that sends instant broadcast alerts"),
            ("WhatsApp URL Scheme", "Coordinates local village and panchayat rescue groups"),
            ("Twilio REST API", "Cellular SMS fallback for users without smartphones")
        ], ACCENT_GREEN, BORDER_GREEN)
    ]

    for idx, (cat_title, items, tc, bc) in enumerate(stacks):
        x = left_c1 if idx % 2 == 0 else left_c2
        y = card_top if idx < 2 else Inches(4.30)
        h_box = Inches(2.80)
        add_glass_card(s9, x, y, col_w, h_box, cat_title, bc, CARD_BG, tc)
        tb = s9.shapes.add_textbox(x + Inches(0.24), y + Inches(0.55), col_w - Inches(0.48), h_box - Inches(0.65))
        tf = tb.text_frame
        tf.word_wrap = True
        for h_text, b_text in items:
            add_bullet(tf, h_text, b_text, font_size=12.5, space_before=7)

    add_notes(s9, """SLIDE 9: TECHNOLOGY STACK
• 4 Distinct Domains:
  1. AI & ML: Python 3.11, Scikit-Learn, XGBoost, Pillow, Gemini/Ollama.
  2. Backend: Flask, PyJWT, SQLite WAL, ReportLab.
  3. Frontend: React 19, Leaflet GIS, Glassmorphism UI.
  4. Routing & Alerts: OSRM, OASIS CAP v1.2, Telegram, WhatsApp.""")

    # =============================================================
    # SLIDE 10: Comparison & Discussion (Formerly Slide 13)
    # =============================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "Comparison: TerraRisk AI vs Existing Solutions", "BENCHMARK COMPARISON", 10)

    headers10 = ["Feature Dimension", "Old Disaster Portals", "Google Maps", "TerraRisk AI (Proposed)"]
    rows10 = [
        ["Warning Detail", "Whole District (1,000+ km²)", "Traffic delays only", "Exact 30m slope point"],
        ["Slope Physics", "Historical maps only", "None", "Slope, Rain, Soil, Moisture"],
        ["Photo Verification", "Manual (takes hours)", "None", "3-Tier AI in <600ms"],
        ["Evacuation Route", "Static list of shelters", "Shortest path (crosses landslides)", "Dynamic 2 km danger detour"],
        ["Report Grouping", "Manual phone logs", "Traffic heuristics", "Auto-groups within 500m"],
        ["Broadcast Cost", "Expensive bulk SMS", "App notifications", "Free Telegram + WhatsApp + CAP"],
        ["SitRep Reports", "Manual paper (24h delay)", "None", "One-click instant PDF"]
    ]
    col_w10 = [Inches(2.5), Inches(3.1), Inches(3.1), Inches(3.433)]
    create_styled_table(s10, left_c1, card_top, total_w, Inches(3.9), headers10, rows10, col_w10)

    add_glass_card(s10, left_c1, Inches(5.35), total_w, Inches(1.75), "Design Trade-Off: Safety First", BORDER_BLUE, CARD_TINT_BLUE, ACCENT_BLUE)
    tb10_disc = s10.shapes.add_textbox(left_c1 + Inches(0.28), Inches(5.75), total_w - Inches(0.56), Inches(1.25))
    tf10_disc = tb10_disc.text_frame
    tf10_disc.word_wrap = True
    p10 = tf10_disc.paragraphs[0]
    p10.text = "Design Decision: Normal navigation apps always pick the fastest travel time. During a disaster, this is deadly because the fastest road often crosses an active landslide. TerraRisk AI prioritizes human life over speed: by enforcing a mandatory 2.0 km buffer around all red danger zones, vehicles are safely steered through verified clear roads."
    p10.font.size = Pt(13.5)
    p10.font.color.rgb = TEXT_BODY

    add_notes(s10, """SLIDE 10: COMPARISON & DISCUSSION
• Highlight key differentiators: 30m precision vs 1,000 km²; <600ms photo checks vs manual; 2 km detours vs blind shortest paths.
• Design Trade-Off: We prioritize life safety over transit speed, ensuring evacuees never cross an active landslide.""")

    # =============================================================
    # SLIDE 11: Conclusion (Formerly Slide 14)
    # =============================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "Conclusion: Key Academic & Practical Contributions", "SUMMARY & IMPACT", 11)

    add_glass_card(s11, left_c1, card_top, col_w, card_h, "Academic & Scientific Contributions", BORDER_BLUE, CARD_BG, ACCENT_BLUE, "ACADEMIC", ACCENT_BLUE)
    tb11_1 = s11.shapes.add_textbox(left_c1 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf11_1 = tb11_1.text_frame
    tf11_1.word_wrap = True
    b11_1 = [
        ("Proved Physics + AI Works", "Combining slope mechanics with gradient boosting achieved an R² score of 98.54%, far outperforming traditional empirical formulas."),
        ("Sub-Second Photo Triage", "Proved that local edge texture checks combined with vision models drop verification time from hours to under 600ms while removing 86.4% of false reports."),
        ("Smarter Crowd Triage", "Proved that grouping reports within 500m eliminates duplicate rescue dispatches during intense storms.")
    ]
    for h, b in b11_1:
        add_bullet(tf11_1, h, b, font_size=14.5, space_before=22)

    add_glass_card(s11, left_c2, card_top, col_w, card_h, "Real-World Societal Benefits", BORDER_GREEN, CARD_BG, ACCENT_GREEN, "SOCIETAL IMPACT", ACCENT_GREEN)
    tb11_2 = s11.shapes.add_textbox(left_c2 + Inches(0.28), card_top + Inches(0.70), col_w - Inches(0.56), card_h - Inches(0.90))
    tf11_2 = tb11_2.text_frame
    tf11_2.word_wrap = True
    b11_2 = [
        ("Free Alerts for Communities", "Replaced costly bulk SMS with Telegram and WhatsApp, saving municipal funds while reaching more people instantly."),
        ("Saves Lives on the Road", "Steers escaping cars away from landslides directly to shelters that have available beds and food supplies."),
        ("Global Standards", "Follows OASIS CAP v1.2 international standards so it works seamlessly with national disaster systems.")
    ]
    for h, b in b11_2:
        add_bullet(tf11_2, h, b, font_size=14.5, space_before=22)

    add_notes(s11, """SLIDE 11: CONCLUSION
• Academic Impact: Demonstrated that coupling slope physics with gradient boosting achieves 98.54% accuracy.
• Practical Impact: Sub-second edge photo checks cut false reports by 86.4%; dynamic 2 km detours preserve human life.""")

    # =============================================================
    # SLIDE 12: Future Scope (Formerly Slide 15)
    # =============================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12)
    add_header(s12, "Future Scope: Next Steps & Future Enhancements", "ROADMAP", 12)

    scopes = [
        ("1. Radar Satellites & Drones", "Use Sentinel-1 radar and drone photos to detect ground slipping by millimeters before hills collapse.", ACCENT_BLUE, BORDER_BLUE),
        ("2. Solar IoT Ground Sensors", "Place low-cost solar tiltmeters and moisture probes on dangerous hairpin turns linked via radio.", ACCENT_AMBER, BORDER_AMBER),
        ("3. Offline Shelter Mesh", "Allow local shelter servers to keep running AI models even when internet cables are cut during storms.", ACCENT_BLUE, BORDER_BLUE),
        ("4. Voice Alerts in Malayalam", "Use voice AI to send spoken warnings in Malayalam and tribal dialects for elderly hill residents.", ACCENT_GREEN, BORDER_GREEN)
    ]
    for idx, (title, desc, tc, bc) in enumerate(scopes):
        x = left_c1 if idx % 2 == 0 else left_c2
        y = card_top if idx < 2 else Inches(4.30)
        h_box = Inches(2.80)
        add_glass_card(s12, x, y, col_w, h_box, title, bc, CARD_BG, tc)
        tb = s12.shapes.add_textbox(x + Inches(0.28), y + Inches(0.65), col_w - Inches(0.56), h_box - Inches(0.75))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(13.5)
        p.font.color.rgb = TEXT_BODY
        p.space_before = Pt(4)

    add_notes(s12, """SLIDE 12: FUTURE SCOPE
• Outline 4 practical roadmap items:
  1. Radar satellite & drone InSAR to detect millimeter ground creep.
  2. Solar-powered IoT tiltmeters on dangerous hairpin curves.
  3. Offline shelter mesh to run models during communication blackouts.
  4. Malayalam voice synthesis for elderly and tribal residents.""")

    # =============================================================
    # SLIDE 13: References (Formerly Slide 16)
    # =============================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13)
    add_header(s13, "References: Key Academic Papers & Reports", "BIBLIOGRAPHY", 13)

    add_glass_card(s13, left_c1, card_top, total_w, card_h, "Selected Academic References", BORDER_SUBTLE, CARD_BG, TEXT_DARK)
    tb13 = s13.shapes.add_textbox(left_c1 + Inches(0.28), card_top + Inches(0.70), total_w - Inches(0.56), card_h - Inches(0.90))
    tf13 = tb13.text_frame
    tf13.word_wrap = True

    core_research_papers = [
        (
            "[1] Geological Survey of India (GSI) & KSDMA (2024)",
            "Assessment of Chooralmala-Meppadi Debris Flows and Wayanad Landslide Disasters.",
            "Special Post-Disaster Geotechnical Investigation Report, Government of Kerala.",
            "https://sdma.kerala.gov.in"
        ),
        (
            "[2] Caine, N. (1980)",
            "The Rainfall Intensity - Duration Control of Shallow Landslides and Debris Flows.",
            "Geografiska Annaler: Series A, Physical Geography, 62(1-2), pp. 23–27.",
            "https://doi.org/10.1080/04353676.1980.11879996"
        ),
        (
            "[3] Guzzetti, F., Peruccacci, S., Rossi, M., & Stark, C. P. (2008)",
            "The rainfall intensity–duration control of shallow landslides and debris flows: an update.",
            "Landslides, 5(1), pp. 3–17.",
            "https://doi.org/10.1007/s10346-007-0112-1"
        ),
        (
            "[4] Friedman, J. H. (2001)",
            "Greedy Function Approximation: A Gradient Boosting Machine.",
            "The Annals of Statistics, 29(5), pp. 1189–1232.",
            "https://doi.org/10.1214/aos/1013203451"
        ),
        (
            "[5] Chen, T., & Guestrin, C. (2016)",
            "XGBoost: A Scalable Tree Boosting System.",
            "Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16), pp. 785–794.",
            "https://doi.org/10.1145/2939672.2939785"
        )
    ]

    for idx, (auth, title, venue, link) in enumerate(core_research_papers):
        p = tf13.add_paragraph() if len(tf13.paragraphs[0].text) > 0 else tf13.paragraphs[0]
        p.space_before = Pt(14)

        r1 = p.add_run()
        r1.text = f"{auth}: "
        r1.font.bold = True
        r1.font.color.rgb = TEXT_DARK
        r1.font.size = Pt(13)

        r2 = p.add_run()
        r2.text = f'"{title}" '
        r2.font.bold = False
        r2.font.color.rgb = TEXT_BODY
        r2.font.size = Pt(12.5)

        r3 = p.add_run()
        r3.text = f"{venue} "
        r3.font.italic = True
        r3.font.color.rgb = TEXT_MUTED
        r3.font.size = Pt(12)

        r4 = p.add_run()
        r4.text = f"[Paper Link / DOI: {link}]"
        r4.font.bold = True
        r4.font.color.rgb = ACCENT_BLUE
        r4.font.size = Pt(11.5)
        r4.font.underline = True
        r4.hyperlink.address = link

    add_notes(s13, """SLIDE 13: REFERENCES & PEER-REVIEWED LITERATURE
• Grounded in 5 authoritative scientific papers & official reports:
  1. GSI & KSDMA (2024): Wayanad Meppadi Debris Flow Geotechnical Assessment. [https://sdma.kerala.gov.in]
  2. Caine (1980): Seminal rainfall intensity-duration threshold curve. [https://doi.org/10.1080/04353676.1980.11879996]
  3. Guzzetti et al. (2008): Global review of empirical hydrological thresholds for landslides. [https://doi.org/10.1007/s10346-007-0112-1]
  4. Friedman (2001): Mathematical foundation for Gradient Boosting Machines. [https://doi.org/10.1214/aos/1013203451]
  5. Chen & Guestrin (2016): XGBoost regressor for atmospheric rainfall telemetry. [https://doi.org/10.1145/2939672.2939785]
• Note: Removed general software packages (DBSCAN 1996, OSRM 2011, OASIS CAP standard) to focus strictly on peer-reviewed research papers.""")

    # =============================================================
    # SLIDE 14: Final Closing Slide (ONLY "Thank You" — NOTHING ELSE)
    # =============================================================
    s14 = prs.slides.add_slide(blank_layout)

    # Clean Background Canvas & Topographic Contours
    bg14 = s14.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg14.fill.solid()
    bg14.fill.fore_color.rgb = BG_CANVAS
    bg14.line.fill.background()
    apply_fade_transition(s14)
    draw_topographic_contours(s14)

    # Large Center Hero Container
    hero_w = Inches(12.133)
    hero_h = Inches(5.9)
    hero_l = Inches(0.6)
    hero_t = Inches(0.8)

    hero_card14 = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, hero_l, hero_t, hero_w, hero_h)
    hero_card14.fill.solid()
    hero_card14.fill.fore_color.rgb = CARD_BG
    hero_card14.line.color.rgb = BORDER_BLUE
    hero_card14.line.width = Pt(1.5)

    # Center text box: ONLY "Thank You" (Nothing else on the slide)
    tb_thank = s14.shapes.add_textbox(hero_l + Inches(1.0), hero_t + Inches(1.7), hero_w - Inches(2.0), Inches(2.4))
    tf_thank = tb_thank.text_frame
    tf_thank.word_wrap = True
    tf_thank.margin_left = tf_thank.margin_top = tf_thank.margin_right = tf_thank.margin_bottom = 0
    p_thank = tf_thank.paragraphs[0]
    p_thank.text = "Thank You"
    p_thank.font.size = Pt(96)
    p_thank.font.bold = True
    p_thank.font.color.rgb = ACCENT_BLUE
    p_thank.alignment = PP_ALIGN.CENTER

    add_notes(s14, """SLIDE 14: THANK YOU
• Concluding slide: Thank the examination committee and faculty.""")

    # =============================================================
    # Save Presentation Files
    # =============================================================
    output_files = [
        os.path.join(base_dir, "TerraRisk_AI_Presentation_Updated.pptx"),
        os.path.join(base_dir, "TerraRisk_AI_Presentation_Editable.pptx"),
        os.path.join(base_dir, "TerraRisk_AI_Presentation.pptx"),
        os.path.join(base_dir, "TerraRisk_AI_Presentation_Visual.pptx")
    ]

    saved_count = 0
    for out_p in output_files:
        try:
            prs.save(out_p)
            print(f"[OK] Successfully saved presentation at: {out_p}")
            saved_count += 1
        except Exception as e:
            print(f"[WARN] Could not save to {out_p}: {e}")

    if saved_count > 0:
        print(f"\n[SUCCESS] Presentation generated with {len(prs.slides)} slides (Slides 10, 11, 12 removed; enlarged typography; clean 'Thank You' final slide).")
    else:
        print("[ERROR] Failed to save presentation to any file!")

if __name__ == "__main__":
    build_presentation()
