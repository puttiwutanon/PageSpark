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

        # --- Problem Statement ---
        problem_text = Text('โจทย์ข้อ 19: หาอัตราเร็วคลื่น', font='TH Sarabun New', color=GOLD_B, font_size=38)
        problem_text.scale_to_fit_width(frame_width * 0.85)
        problem_text.move_to(top_center)
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(1.5)

        # --- Given Values ---
        given_f = MathTex(r'f = 20\,\mathrm{Hz}', color=BLUE_D, font_size=32)
        given_dphi = MathTex(r'\Delta\phi = \frac{\pi}{6}\,\mathrm{rad}', color=BLUE_D, font_size=32)
        given_dx = MathTex(r'\Delta x = 0.5\,\mathrm{m}', color=BLUE_D, font_size=32)
        given_v = MathTex(r'v = ?', color=RED_C, font_size=32)

        given_group = VGroup(given_f, given_dphi, given_dx, given_v).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        given_group.scale_to_fit_width(frame_width * 0.8)
        given_group.scale_to_fit_height(middle_zone_height * 0.8)
        given_group.move_to(middle_center)
        self.play(FadeIn(given_group, lag_ratio=0.15))
        self.wait(2)
        self.play(FadeOut(given_group, shift=DOWN*0.1))

        # --- Step 1: Find Wavelength (lambda) ---
        step1_title = Text('ขั้นตอนที่ 1: หาความยาวคลื่น (\(\lambda\))', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_dphi_dx = MathTex(r'\Delta\phi = \frac{2\pi}{\lambda}\Delta x', color=BLUE_D, font_size=36)
        eq_sub_values = MathTex(r'\frac{\pi}{6} = \frac{2\pi}{\lambda}(0.5)', color=WHITE, font_size=36)
        eq_solve_lambda = MathTex(r'\frac{1}{6} = \frac{1}{\lambda}', color=WHITE, font_size=36)
        eq_lambda_result = MathTex(r'\lambda = 6\,\mathrm{m}', color=GREEN_C, font_size=38)

        step1_group = VGroup(step1_title, eq_dphi_dx, eq_sub_values, eq_solve_lambda, eq_lambda_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15))
        self.play(Write(eq_dphi_dx), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_values), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_solve_lambda), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_lambda_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step1_group, shift=DOWN*0.1))

        # --- Step 2: Find Wave Speed (v) ---
        step2_title = Text('ขั้นตอนที่ 2: หาอัตราเร็วคลื่น (v)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_v_f_lambda = MathTex(r'v = f\lambda', color=BLUE_D, font_size=36)
        eq_sub_values_v = MathTex(r'v = (20\,\mathrm{Hz})(6\,\mathrm{m})', color=WHITE, font_size=36)
        eq_v_result = MathTex(r'v = 120\,\mathrm{m/s}', color=GREEN_C, font_size=38)

        step2_group = VGroup(step2_title, eq_v_f_lambda, eq_sub_values_v, eq_v_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step2_group.scale_to_fit_width(frame_width * 0.85)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step2_group.move_to(bottom_center)

        self.play(FadeIn(step2_title, shift=UP*0.15))
        self.play(Write(eq_v_f_lambda), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_values_v), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_v_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step2_group, shift=DOWN*0.1))

        # --- Answer Summary ---
        ans_label = Text('คำตอบ:', font='TH Sarabun New', color=GOLD_B, font_size=38)
        ans_eq = MathTex(r'v = 120\,\mathrm{m/s}', color=GREEN_C, font_size=44)
        answer_group = VGroup(ans_label, ans_eq).arrange(DOWN, buff=0.4)
        answer_group.scale_to_fit_width(frame_width * 0.85)
        answer_group.scale_to_fit_height(bottom_zone_height * 0.9)
        answer_group.move_to(bottom_center)

        self.play(FadeIn(answer_group, shift=UP*0.15))
        self.wait(2.5)
        self.play(FadeOut(answer_group, shift=DOWN*0.1))
        self.play(FadeOut(problem_text, shift=DOWN*0.1))