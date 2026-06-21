import numpy as np
from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_height = 16.0
config.frame_width = 9.0
config.frame_rate = 60

class PhysicsScene(Scene):
    def construct(self):
        self.camera.background_color = '#1C1C2E'
        frame_height = config.frame_height
        frame_width = config.frame_width
        top_zone_height = frame_height * 0.20
        middle_zone_height = frame_height * 0.45
        bottom_zone_height = frame_height * 0.35
        top_zone_top = frame_height / 2
        top_zone_bottom = top_zone_top - top_zone_height
        top_zone_center_y = (top_zone_top + top_zone_bottom) / 2
        middle_zone_top = top_zone_bottom
        middle_zone_bottom = middle_zone_top - middle_zone_height
        middle_zone_center_y = (middle_zone_top + middle_zone_bottom) / 2
        bottom_zone_top = middle_zone_bottom
        bottom_zone_bottom = bottom_zone_top - bottom_zone_height
        bottom_zone_center_y = (bottom_zone_top + bottom_zone_bottom) / 2
        top_center = np.array([0, top_zone_center_y, 0])
        middle_center = np.array([0, middle_zone_center_y, 0])
        bottom_center = np.array([0, bottom_zone_center_y, 0])

        # --- Problem 22 Variables ---
        f1_val = 120  # Hz
        f2_val = 122  # Hz
        t_val = 1.2  # s

        # --- Calculations ---
        # Step 1: Find phi1
        # phi1 = 2*pi*f1*t
        phi1_val = 2 * np.pi * f1_val * t_val

        # Step 2: Find phi2
        # phi2 = 2*pi*f2*t
        phi2_val = 2 * np.pi * f2_val * t_val

        # Step 3: Find delta_phi_total
        # delta_phi_total = phi2 - phi1
        delta_phi_total_val = phi2_val - phi1_val

        # --- Episode 4: Problem 22 ---
        # 1. Problem Text (Top Zone)
        problem_text_mobjects = VGroup(
            Text('คลื่นต่อเนื่องสองขบวน มีความถี่ 120 Hz และ 122 Hz', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('เริ่มเคลื่อนที่ออกจากจุดเดียวกันด้วยเฟสตรงกัน', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('เมื่อเวลา 1.2 วินาที คลื่นทั้งสองจะมีเฟสต่างกันเท่าไร', font='TH Sarabun New', font_size=28, color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

        if problem_text_mobjects.width > frame_width * 0.88:
            problem_text_mobjects.scale_to_fit_width(frame_width * 0.88)
        if problem_text_mobjects.height > top_zone_height * 0.88:
            problem_text_mobjects.scale_to_fit_height(top_zone_height * 0.88)
        problem_text_mobjects.move_to(top_center)

        self.play(FadeIn(problem_text_mobjects, shift=UP*0.15))
        self.wait(12.5)

        # 2. Visualization (Middle Zone) - Two waves with slightly different frequencies
        t_display_range = 0.05
        axes = Axes(
            x_range=[0, t_display_range, t_display_range/2],
            y_range=[-1.1, 1.1, 0.5],
            x_length=frame_width * 0.60,
            y_length=middle_zone_height * 0.65,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            },
            x_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B,
                            'numbers_to_exclude': [0]},
            y_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B,
                            'numbers_to_exclude': [0]},
        )
        x_label = axes.get_x_axis_label(
            Text('เวลา (s)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )
        y_label = axes.get_y_axis_label(
            Text('การกระจัด', font='TH Sarabun New', font_size=18, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.30
        )
        axes_labels = VGroup(x_label, y_label)

        wave_path1 = axes.plot(
            lambda t: np.sin(2 * np.pi * f1_val * t),
            color=BLUE_C,
            stroke_width=3
        )
        wave_path2 = axes.plot(
            lambda t: np.sin(2 * np.pi * f2_val * t),
            color=ORANGE,
            stroke_width=3
        )

        f1_label = MathTex(r'f_1 = 120 \text{ Hz}', font_size=20, color=BLUE_C).next_to(axes, UR, buff=0.5)
        f2_label = MathTex(r'f_2 = 122 \text{ Hz}', font_size=20, color=ORANGE).next_to(f1_label, DOWN, buff=0.2, aligned_edge=LEFT)
        t_label = MathTex(r't = 1.2 \text{ s}', font_size=20, color=YELLOW_C).next_to(f2_label, DOWN, buff=0.2, aligned_edge=LEFT)

        wave_group = VGroup(axes, axes_labels, wave_path1, wave_path2, f1_label, f2_label, t_label)

        if wave_group.width > frame_width * 0.88:
            wave_group.scale_to_fit_width(frame_width * 0.88)
        if wave_group.height > middle_zone_height * 0.82:
            wave_group.scale_to_fit_height(middle_zone_height * 0.82)
        if wave_group.width < frame_width * 0.55:
            wave_group.scale_to_fit_width(frame_width * 0.55)
        if wave_group.height < middle_zone_height * 0.55:
            wave_group.scale_to_fit_height(middle_zone_height * 0.55)
        wave_group.move_to(middle_center)

        self.play(
            Create(axes),
            Create(axes_labels),
            Create(wave_path1),
            Create(wave_path2),
            FadeIn(f1_label, shift=UP*0.1),
            FadeIn(f2_label, shift=UP*0.1),
            FadeIn(t_label, shift=UP*0.1)
        )
        self.wait(25.5)

        # 3. Solution Steps (Bottom Zone)
        # Step 1: Find phase for wave 1 (phi1)
        step1_title = VGroup(
            Text('ขั้นตอนที่ 1:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาเฟสของคลื่นขบวนที่ 1 (\\(\phi_1\\))', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15)

        eq_phi_f1 = MathTex(r'\phi_1 = 2\pi f_1 t', font_size=26, color=BLUE_C)
        eq_sub_phi1 = MathTex(
            r'\phi_1 = 2\pi (120) (1.2)', font_size=26, color=WHITE
        )
        eq_ans_phi1 = MathTex(
            r'\phi_1 = 288\pi \text{ rad}', font_size=26, color=GREEN_C
        )

        step1_group = VGroup(step1_title, eq_phi_f1, eq_sub_phi1, eq_ans_phi1).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        
        if step1_group.width > frame_width * 0.88:
            step1_group.scale_to_fit_width(frame_width * 0.88)
        if step1_group.height > bottom_zone_height * 0.88:
            step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        self.play(
            FadeIn(step1_group[0], shift=UP*0.15),
            Write(step1_group[1])
        )
        self.wait(2.0)
        self.play(Write(step1_group[2]))
        self.wait(2.0)
        self.play(Write(step1_group[3]))
        self.wait(13.5)

        # Step 2: Find phase for wave 2 (phi2)
        step2_title = VGroup(
            Text('ขั้นตอนที่ 2:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาเฟสของคลื่นขบวนที่ 2 (\\(\phi_2\\))', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15)

        eq_phi_f2 = MathTex(r'\phi_2 = 2\pi f_2 t', font_size=26, color=BLUE_C)
        eq_sub_phi2 = MathTex(
            r'\phi_2 = 2\pi (122) (1.2)', font_size=26, color=WHITE
        )
        eq_ans_phi2 = MathTex(
            r'\phi_2 = 292.8\pi \text{ rad}', font_size=26, color=GREEN_C
        )

        step2_group = VGroup(step2_title, eq_phi_f2, eq_sub_phi2, eq_ans_phi2).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        
        if step2_group.width > frame_width * 0.88:
            step2_group.scale_to_fit_width(frame_width * 0.88)
        if step2_group.height > bottom_zone_height * 0.88:
            step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        self.play(
            FadeOut(step1_group, shift=DOWN*0.1),
            FadeIn(step2_group[0], shift=UP*0.15),
            Write(step2_group[1])
        )
        self.wait(2.0)
        self.play(Write(step2_group[2]))
        self.wait(2.0)
        self.play(Write(step2_group[3]))
        self.wait(13.5)

        # Step 3: Find total phase difference (delta_phi_total)
        step3_title = VGroup(
            Text('ขั้นตอนที่ 3:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาผลต่างเฟสรวม (\\(\Delta \phi\\))', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15)

        eq_dphi_total = MathTex(r'\Delta \phi = |\phi_2 - \phi_1|', font_size=26, color=BLUE_C)
        eq_sub_dphi_total = MathTex(
            r'\Delta \phi = |292.8\pi - 288\pi|', font_size=26, color=WHITE
        )
        eq_ans_dphi_total = MathTex(
            r'\Delta \phi = 4.8\pi \text{ rad}', font_size=26, color=GREEN_C
        )

        step3_group = VGroup(step3_title, eq_dphi_total, eq_sub_dphi_total, eq_ans_dphi_total).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        
        if step3_group.width > frame_width * 0.88:
            step3_group.scale_to_fit_width(frame_width * 0.88)
        if step3_group.height > bottom_zone_height * 0.88:
            step3_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step3_group.move_to(bottom_center)

        self.play(
            FadeOut(step2_group, shift=DOWN*0.1),
            FadeIn(step3_group[0], shift=UP*0.15),
            Write(step3_group[1])
        )
        self.wait(2.0)
        self.play(Write(step3_group[2]))
        self.wait(2.0)
        self.play(Write(step3_group[3]))
        self.wait(13.5)

        # 4. Call to Action
        cta_text_lines = VGroup(
            Text('ดังนั้น เมื่อเวลาผ่านไป 1.2 วินาที คลื่นทั้งสอง', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('จะมีเฟสต่างกัน 4.8 พาย เรเดียนครับ', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('โจทย์ข้อนี้แสดงให้เห็นว่าความถี่ที่ต่างกันเพียงเล็กน้อย', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('ก็ทำให้เฟสของคลื่นเปลี่ยนไปมากได้', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('ถ้าอยากเห็นภาพฟิสิกส์แบบนี้อีก อย่าลืมติดตาม pageSpark นะครับ', font='TH Sarabun New', font_size=28, color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

        if cta_text_lines.width > frame_width * 0.88:
            cta_text_lines.scale_to_fit_width(frame_width * 0.88)
        if cta_text_lines.height > bottom_zone_height * 0.88:
            cta_text_lines.scale_to_fit_height(bottom_zone_height * 0.88)
        cta_text_lines.move_to(bottom_center)

        self.play(
            FadeOut(step3_group, shift=DOWN*0.1),
            FadeIn(cta_text_lines, shift=UP*0.15)
        )
        self.wait(19.0)

        self.play(
            FadeOut(problem_text_mobjects, shift=UP*0.1),
            FadeOut(wave_group, shift=UP*0.1),
            FadeOut(cta_text_lines, shift=UP*0.1)
        )
        self.wait(0.5)