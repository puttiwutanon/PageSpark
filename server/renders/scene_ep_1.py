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

        # --- Problem Constants ---
        L1 = 0.4 # meters (40 cm)
        f1 = 20 # Hz
        lambda1 = 2 * L1 # 0.8 meters
        v1 = f1 * lambda1 # 16 m/s

        # --- Mobjects for Hook ---
        problem_text = VGroup(
            Text('ลวดเส้นหนึ่งยาว 40 เซนติเมตร ปลายทั้งสองถูกขึงตึง', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('เมื่อดีดลวดตรงกลางทำให้เส้นลวดสั่นขึ้นลงด้วยความถี่ 20 เฮิรตซ์', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('จงหาอัตราเร็วของคลื่นในลวดเส้นนี้', font='TH Sarabun New', font_size=28, color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center)

        # --- Mobjects for Diagram Explain ---
        # Horizontal line for the string
        string_line = Line(start=[-L1/2, 0, 0], end=[L1/2, 0, 0], color=GRAY_C, stroke_width=2)
        # Standing wave (one loop) - using a sine function for visualization
        def wave_func(x):
            return 0.15 * np.sin(np.pi * (x + L1/2) / L1)
        wave_path = ParametricFunction(lambda t: [t, wave_func(t), 0], t_range=[-L1/2, L1/2], color=TEAL_C, stroke_width=4)
        # Fixed ends (Nodes)
        fixed_end_left = Dot(point=[-L1/2, 0, 0], color=ORANGE, radius=0.08)
        fixed_end_right = Dot(point=[L1/2, 0, 0], color=ORANGE, radius=0.08)
        # Labels for L and lambda/2
        length_brace = Brace(string_line, direction=DOWN, buff=0.1)
        length_label = VGroup(
            MathTex('L = 40\,\mathrm{cm}', font_size=18, color=GRAY_A),
            MathTex('= 0.4\,\mathrm{m}', font_size=18, color=GRAY_A)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.05).next_to(length_brace, DOWN, buff=0.1)

        lambda_brace = Brace(wave_path, direction=UP, buff=0.1)
        lambda_label = MathTex('\\frac{\lambda}{2}', font_size=18, color=GRAY_A).next_to(lambda_brace, UP, buff=0.1)

        wave_diagram_group = VGroup(string_line, wave_path, fixed_end_left, fixed_end_right, length_brace, length_label, lambda_brace, lambda_label)
        if wave_diagram_group.width > frame_width * 0.88:
            wave_diagram_group.scale_to_fit_width(frame_width * 0.88)
        if wave_diagram_group.height > middle_zone_height * 0.82:
            wave_diagram_group.scale_to_fit_height(middle_zone_height * 0.82)
        # Ensure it's not too small (BUG #4-ก)
        if wave_diagram_group.width < frame_width * 0.55:
            wave_diagram_group.scale_to_fit_width(frame_width * 0.55)
        if wave_diagram_group.height < middle_zone_height * 0.55:
            wave_diagram_group.scale_to_fit_height(middle_zone_height * 0.55)
        wave_diagram_group.move_to(middle_center)

        # --- Mobjects for Step 1 ---
        step1_title = VGroup(
            Text('ขั้นตอนที่ 1:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาความยาวคลื่น (\lambda)', font='TH Sarabun New', font_size=26, color=GOLD_B)
        ).arrange(RIGHT, buff=0.15)
        eq_lambda_half = MathTex('L = \\frac{\lambda}{2}', font_size=26, color=WHITE)
        eq_lambda_val = MathTex('\\lambda = 2L = 2(0.4\,\mathrm{m}) = 0.8\,\mathrm{m}', font_size=26, color=WHITE)
        step1_group = VGroup(step1_title, eq_lambda_half, eq_lambda_val).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        if step1_group.width > frame_width * 0.88:
            step1_group.scale_to_fit_width(frame_width * 0.88)
        if step1_group.height > bottom_zone_height * 0.88:
            step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        # --- Mobjects for Step 2 ---
        step2_title = VGroup(
            Text('ขั้นตอนที่ 2:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาอัตราเร็วคลื่น (V)', font='TH Sarabun New', font_size=26, color=GOLD_B)
        ).arrange(RIGHT, buff=0.15)
        eq_v_formula = MathTex('V = f\lambda', font_size=26, color=WHITE)
        eq_v_sub = MathTex('V = (20\,\mathrm{Hz})(0.8\,\mathrm{m})', font_size=26, color=WHITE)
        eq_v_result = MathTex('V = 16\,\mathrm{m/s}', font_size=26, color=GREEN_C)
        step2_group = VGroup(step2_title, eq_v_formula, eq_v_sub, eq_v_result).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        if step2_group.width > frame_width * 0.88:
            step2_group.scale_to_fit_width(frame_width * 0.88)
        if step2_group.height > bottom_zone_height * 0.88:
            step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        # --- Mobjects for CTA ---
        cta_text = Text('ลองฝึกทำโจทย์คลื่นนิ่งข้ออื่นๆ ดูนะครับ!', font='TH Sarabun New', font_size=28, color=WHITE)
        if cta_text.width > frame_width * 0.88:
            cta_text.scale_to_fit_width(frame_width * 0.88)
        if cta_text.height > bottom_zone_height * 0.88:
            cta_text.scale_to_fit_height(bottom_zone_height * 0.88)
        cta_text.move_to(bottom_center)

        # --- Animations ---
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(6.0)

        self.play(
            FadeOut(problem_text, shift=DOWN*0.1),
            Create(wave_diagram_group)
        )
        self.wait(8.0)

        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(8.0)

        self.play(
            FadeOut(step1_group, shift=DOWN*0.1),
            FadeIn(step2_group, shift=UP*0.15)
        )
        self.wait(12.0)

        self.play(
            FadeOut(wave_diagram_group, shift=DOWN*0.1),
            FadeOut(step2_group, shift=DOWN*0.1),
            FadeIn(cta_text, shift=UP*0.15)
        )
        self.wait(6.0)
        self.play(FadeOut(cta_text, shift=DOWN*0.1))