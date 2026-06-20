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
        bottom_center = np.array([0, bottom_zone_bottom, 0]) # Use bottom_zone_bottom for equations to make space for title

        # --- Problem Statement ---
        problem_text = Text('โจทย์ข้อ 21: หาเฟสที่ต่างกัน', font='TH Sarabun New', color=GOLD_B, font_size=38)
        problem_text.scale_to_fit_width(frame_width * 0.85)
        problem_text.move_to(top_center)
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(1.5)

        # --- Given Values ---
        given_f = MathTex(r'f = 40\,\mathrm{Hz}', color=BLUE_D, font_size=32)
        given_v = MathTex(r'v = 10\,\mathrm{m/s}', color=BLUE_D, font_size=32)
        given_dx = MathTex(r'\Delta x = 1.5\,\mathrm{m}', color=BLUE_D, font_size=32)
        given_dphi = MathTex(r'\Delta\phi = ?', color=RED_C, font_size=32)

        given_group = VGroup(given_f, given_v, given_dx, given_dphi).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        given_group.scale_to_fit_width(frame_width * 0.8)
        given_group.scale_to_fit_height(middle_zone_height * 0.8)
        given_group.move_to(middle_center)
        self.play(FadeIn(given_group, lag_ratio=0.15))
        self.wait(2)
        self.play(FadeOut(given_group, shift=DOWN*0.1))

        # --- Step 1: Find Wavelength (lambda) ---
        step1_title = Text('ขั้นตอนที่ 1: หาความยาวคลื่น (\(\lambda\))', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_lambda_vf = MathTex(r'\lambda = \frac{v}{f}', color=BLUE_D, font_size=36)
        eq_sub_lambda = MathTex(r'\lambda = \frac{10\,\mathrm{m/s}}{40\,\mathrm{Hz}}', color=WHITE, font_size=36)
        eq_lambda_result = MathTex(r'\lambda = 0.25\,\mathrm{m}', color=GREEN_C, font_size=38)

        step1_group = VGroup(step1_title, eq_lambda_vf, eq_sub_lambda, eq_lambda_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15))
        self.play(Write(eq_lambda_vf), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_lambda), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_lambda_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step1_group, shift=DOWN*0.1))

        # --- Step 2: Find Phase Difference (Delta phi) ---
        step2_title = Text('ขั้นตอนที่ 2: หาเฟสที่ต่างกัน (\(\Delta\phi\))', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_dphi_dx = MathTex(r'\Delta\phi = \frac{2\pi}{\lambda}\Delta x', color=BLUE_D, font_size=36)
        eq_sub_dphi = MathTex(r'\Delta\phi = \frac{2\pi}{0.25}(1.5)', color=WHITE, font_size=36)
        eq_dphi_result = MathTex(r'\Delta\phi = 12\pi\,\mathrm{rad}', color=GREEN_C, font_size=38)

        step2_group = VGroup(step2_title, eq_dphi_dx, eq_sub_dphi, eq_dphi_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step2_group.scale_to_fit_width(frame_width * 0.85)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step2_group.move_to(bottom_center)

        self.play(FadeIn(step2_title, shift=UP*0.15))
        self.play(Write(eq_dphi_dx), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_dphi), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_dphi_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step2_group, shift=DOWN*0.1))

        # --- Answer Summary ---
        ans_label = Text('คำตอบ:', font='TH Sarabun New', color=GOLD_B, font_size=38)
        ans_eq = MathTex(r'\Delta\phi = 12\pi\,\mathrm{rad}', color=GREEN_C, font_size=44)
        answer_group = VGroup(ans_label, ans_eq).arrange(DOWN, buff=0.4)
        answer_group.scale_to_fit_width(frame_width * 0.85)
        answer_group.scale_to_fit_height(bottom_zone_height * 0.9)
        answer_group.move_to(bottom_center)

        self.play(FadeIn(answer_group, shift=UP*0.15))
        self.wait(2.5)
        self.play(FadeOut(answer_group, shift=DOWN*0.1))
        self.play(FadeOut(problem_text, shift=DOWN*0.1))