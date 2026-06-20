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
        problem_text = Text('โจทย์ข้อ 20: หาระยะห่างคลื่น', font='TH Sarabun New', color=GOLD_B, font_size=38)
        problem_text.scale_to_fit_width(frame_width * 0.85)
        problem_text.move_to(top_center)
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(1.5)

        # --- Graph ---
        x_range_val = [0, 0.5, 0.1]
        y_range_val = [-0.1, 0.1, 0.1]
        axes = Axes(
            x_range=x_range_val,
            y_range=y_range_val,
            x_length=frame_width * 0.7,
            y_length=middle_zone_height * 0.7,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.2,
                'tip_width': 0.12,
                'include_numbers': False,
            },
            x_axis_config={'include_numbers': True, 'font_size': 22, 'color': GRAY_B},
            y_axis_config={'include_numbers': True, 'font_size': 22, 'color': GRAY_B}
        )
        x_label = axes.get_x_axis_label(Text('เวลา (s)', font='TH Sarabun New', font_size=26, color=GRAY_A), edge=RIGHT, buff=0.2)
        y_label = axes.get_y_axis_label(Text('การกระจัด', font='TH Sarabun New', font_size=26, color=GRAY_A), edge=UP, buff=0.2)

        def wave_func(t):
            return 0.1 * np.sin(2 * np.pi * (1/0.4) * t)

        graph = axes.plot(wave_func, color=BLUE_D, stroke_width=3)
        period_line = DashedLine(axes.c2p(0, 0), axes.c2p(0.4, 0), color=GOLD_B, stroke_width=2)
        period_label = MathTex(r'T = 0.4\,\mathrm{s}', color=GOLD_B, font_size=28).next_to(period_line, DOWN, buff=0.2)

        graph_group = VGroup(axes, x_label, y_label, graph, period_line, period_label)
        graph_group.scale_to_fit_height(middle_zone_height * 0.9)
        graph_group.move_to(middle_center)

        self.play(Create(axes), Write(x_label), Write(y_label), run_time=1.5)
        self.play(Create(graph), run_time=2)
        self.play(Create(period_line), FadeIn(period_label, shift=UP*0.15))
        self.wait(2)
        self.play(FadeOut(graph_group, shift=DOWN*0.1))

        # --- Step 1: Find Wavelength (lambda) ---
        step1_title = Text('ขั้นตอนที่ 1: หาความยาวคลื่น (\(\lambda\))', font='TH Sarabun New', color=GOLD_B, font_size=32)
        given_v_val = MathTex(r'v = 2\,\mathrm{m/s}', color=BLUE_D, font_size=32)
        given_T_val = MathTex(r'T = 0.4\,\mathrm{s}', color=BLUE_D, font_size=32)
        eq_lambda_vT = MathTex(r'\lambda = vT', color=BLUE_D, font_size=36)
        eq_sub_lambda = MathTex(r'\lambda = (2\,\mathrm{m/s})(0.4\,\mathrm{s})', color=WHITE, font_size=36)
        eq_lambda_result = MathTex(r'\lambda = 0.8\,\mathrm{m}', color=GREEN_C, font_size=38)

        step1_group = VGroup(step1_title, given_v_val, given_T_val, eq_lambda_vT, eq_sub_lambda, eq_lambda_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15))
        self.play(FadeIn(given_v_val, shift=UP*0.15), FadeIn(given_T_val, shift=UP*0.15))
        self.wait(1)
        self.play(Write(eq_lambda_vT), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_lambda), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_lambda_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step1_group, shift=DOWN*0.1))

        # --- Step 2: Find Distance (Delta x) ---
        step2_title = Text('ขั้นตอนที่ 2: หาระยะห่าง (\(\Delta x\))', font='TH Sarabun New', color=GOLD_B, font_size=32)
        given_dphi_val = MathTex(r'\Delta\phi = \frac{3\pi}{2}\,\mathrm{rad}', color=BLUE_D, font_size=32)
        eq_dphi_dx = MathTex(r'\Delta\phi = \frac{2\pi}{\lambda}\Delta x', color=BLUE_D, font_size=36)
        eq_sub_dx = MathTex(r'\frac{3\pi}{2} = \frac{2\pi}{0.8}\Delta x', color=WHITE, font_size=36)
        eq_solve_dx = MathTex(r'\frac{3}{2} = \frac{2}{0.8}\Delta x', color=WHITE, font_size=36)
        eq_dx_result = MathTex(r'\Delta x = 0.6\,\mathrm{m}', color=GREEN_C, font_size=38)

        step2_group = VGroup(step2_title, given_dphi_val, eq_dphi_dx, eq_sub_dx, eq_solve_dx, eq_dx_result).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step2_group.scale_to_fit_width(frame_width * 0.85)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step2_group.move_to(bottom_center)

        self.play(FadeIn(step2_title, shift=UP*0.15))
        self.play(FadeIn(given_dphi_val, shift=UP*0.15))
        self.wait(1)
        self.play(Write(eq_dphi_dx), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sub_dx), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_solve_dx), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_dx_result), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(step2_group, shift=DOWN*0.1))

        # --- Answer Summary ---
        ans_label = Text('คำตอบ:', font='TH Sarabun New', color=GOLD_B, font_size=38)
        ans_eq = MathTex(r'\Delta x = 0.6\,\mathrm{m}', color=GREEN_C, font_size=44)
        answer_group = VGroup(ans_label, ans_eq).arrange(DOWN, buff=0.4)
        answer_group.scale_to_fit_width(frame_width * 0.85)
        answer_group.scale_to_fit_height(bottom_zone_height * 0.9)
        answer_group.move_to(bottom_center)

        self.play(FadeIn(answer_group, shift=UP*0.15))
        self.wait(2.5)
        self.play(FadeOut(answer_group, shift=DOWN*0.1))
        self.play(FadeOut(problem_text, shift=DOWN*0.1))