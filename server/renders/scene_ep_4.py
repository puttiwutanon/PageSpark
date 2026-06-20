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
        problem_text = Text('โจทย์ข้อ 22: หาเฟสที่ต่างกันของคลื่นสองขบวน', font='TH Sarabun New', color=GOLD_B, font_size=38)
        problem_text.scale_to_fit_width(frame_width * 0.85)
        problem_text.move_to(top_center)
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(1.5)

        # --- Given Values ---
        given_f1 = MathTex(r'f_1 = 120\,\mathrm{Hz}', color=BLUE_D, font_size=32)
        given_f2 = MathTex(r'f_2 = 122\,\mathrm{Hz}', color=BLUE_D, font_size=32)
        given_t = MathTex(r't = 1.2\,\mathrm{s}', color=BLUE_D, font_size=32)
        given_dphi = MathTex(r'\Delta\phi = ?', color=RED_C, font_size=32)

        given_group = VGroup(given_f1, given_f2, given_t, given_dphi).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        given_group.scale_to_fit_width(frame_width * 0.8)
        given_group.scale_to_fit_height(middle_zone_height * 0.8)
        given_group.move_to(middle_center)
        self.play(FadeIn(given_group, lag_ratio=0.15))
        self.wait(2)
        self.play(FadeOut(given_group, shift=DOWN*0.1))

        # --- Step 1: Calculate number of cycles for each wave ---
        step1_title = Text('ขั้นตอนที่ 1: หาจำนวนรอบคลื่น (N)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_n1 = MathTex(r'N_1 = f_1 t = (120\,\mathrm{Hz})(1.2\,\mathrm{s}) = 144\,\mathrm{รอบ}', color=WHITE, font_size=36)
        eq_n2 = MathTex(r'N_2 = f_2 t = (122\,\mathrm{Hz})(1.2\,\mathrm{s}) = 146.4\,\mathrm{รอบ}', color=WHITE, font_size=36)

        step1_group = VGroup(step1_title, eq_n1, eq_n2).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15))
        self.play(Write(eq_n1), run_time=1.5)
        self.wait(1)
        self.play(Write(eq_n2), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step1_group, shift=DOWN*0.1))

        # --- Step 2: Calculate phase difference ---
        step2_title = Text('ขั้นตอนที่ 2: หาเฟสที่ต่างกัน (\(\Delta\phi\))', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_dn = MathTex(r'\Delta N = N_2 - N_1 = 146.4 - 144 = 2.4\,\mathrm{รอบ}', color=WHITE, font_size=36)
        eq_dphi_dn = MathTex(r'\Delta\phi = \Delta N \times 2\pi', color=BLUE_D, font_size=36)
        eq_sub_dphi = MathTex(r'\Delta\phi = (2.4) \times 2\pi', color=WHITE, font_size=36)
        eq_dphi_result = MathTex(r'\Delta\phi = 4.8\pi\,\mathrm{rad}', color=GREEN_C, font_size=38)

        step2_group = VGroup(step2_title, eq_dn, eq_dphi_dn, eq_sub_dphi, eq_dphi_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step2_group.scale_to_fit_width(frame_width * 0.85)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step2_group.move_to(bottom_center)

        self.play(FadeIn(step2_title, shift=UP*0.15))
        self.play(Write(eq_dn), run_time=1.5)
        self.wait(1)
        self.play(Write(eq_dphi_dn), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_dphi), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_dphi_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step2_group, shift=DOWN*0.1))

        # --- Answer Summary ---
        ans_label = Text('คำตอบ:', font='TH Sarabun New', color=GOLD_B, font_size=38)
        ans_eq = MathTex(r'\Delta\phi = 4.8\pi\,\mathrm{rad}', color=GREEN_C, font_size=44)
        answer_group = VGroup(ans_label, ans_eq).arrange(DOWN, buff=0.4)
        answer_group.scale_to_fit_width(frame_width * 0.85)
        answer_group.scale_to_fit_height(bottom_zone_height * 0.9)
        answer_group.move_to(bottom_center)

        self.play(FadeIn(answer_group, shift=UP*0.15))
        self.wait(2.5)
        self.play(FadeOut(answer_group, shift=DOWN*0.1))
        self.play(FadeOut(problem_text, shift=DOWN*0.1))