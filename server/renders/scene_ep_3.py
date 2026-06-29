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

        # Problem 60 variables
        L_val = 1.20 # m
        f_val = 320 # Hz
        n_val = 3 # From diagram (3 loops) or "ขั้นโอเวอร์โทนที่ 2" (n=3)
        lambda_val = 2 * L_val / n_val # 0.8 m
        v_val = f_val * lambda_val # 256 m/s

        # Top Zone: Problem Statement
        problem_text = VGroup(
            Text('60. เส้นลวดยาว 1.20 เมตร ปลายทั้งสองถูกขึงตึง เมื่อลวดสั่นด้วยความถี่ 320 เฮิรตซ์', font='TH Sarabun New', font_size=28, color=GRAY_A),
            Text('จะเกิดการสั่นพ้องในขั้นโอเวอร์โทนที่ 2 จงหาอัตราเร็วของคลื่นในลวดเส้นนี้', font='TH Sarabun New', font_size=28, color=GRAY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center)
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(1.5)

        # Middle Zone: Visualization - Standing Wave (n=3)
        string_line = Line(start=LEFT*3, end=RIGHT*3, color=WHITE, stroke_width=2)
        left_wall = Line(start=string_line.get_left() + UP*0.5, end=string_line.get_left() + DOWN*0.5, color=GRAY_A, stroke_width=3)
        right_wall = Line(start=string_line.get_right() + UP*0.5, end=string_line.get_right() + DOWN*0.5, color=GRAY_A, stroke_width=3)

        standing_wave_upper = FunctionGraph(
            lambda x: 0.8 * np.sin(3 * np.pi * (x + 3) / 6), # 3 loops over length 6
            x_range=[-3, 3],
            color=BLUE_C
        )
        standing_wave_lower = FunctionGraph(
            lambda x: -0.8 * np.sin(3 * np.pi * (x + 3) / 6),
            x_range=[-3, 3],
            color=BLUE_C
        )
        
        brace_L = BraceBetweenPoints(string_line.get_left(), string_line.get_right(), direction=DOWN)
        L_label = VGroup(
            MathTex(r'L = ', font_size=26, color=GOLD_B),
            MathTex(f'{L_val}\\\,\\\mathrm{{m}}', font_size=26, color=GOLD_B)
        ).arrange(RIGHT, buff=0.1).next_to(brace_L, DOWN, buff=0.1)

        vis_group = VGroup(
            string_line, left_wall, right_wall,
            standing_wave_upper, standing_wave_lower,
            brace_L, L_label
        )
        
        vis_group.scale_to_fit_width(frame_width * 0.88)
        vis_group.scale_to_fit_height(middle_zone_height * 0.82)
        if vis_group.width < frame_width * 0.55:
            vis_group.scale_to_fit_width(frame_width * 0.55)
        if vis_group.height < middle_zone_height * 0.55:
            vis_group.scale_to_fit_height(middle_zone_height * 0.55)
        vis_group.move_to(middle_center)

        self.play(Create(string_line), Create(left_wall), Create(right_wall))
        self.play(Create(standing_wave_upper), Create(standing_wave_lower))
        self.play(GrowFromCenter(brace_L), Write(L_label))
        self.wait(2)

        # Bottom Zone: Calculations
        step1_title = Text('ขั้นตอนที่ 1: หาความยาวคลื่น (λ)', font='TH Sarabun New', font_size=26, color=BLUE_D)
        eq1_text = Text('จากรูปคลื่นนิ่ง 3 ลูป (n=3) หรือ โอเวอร์โทนที่ 2:', font='TH Sarabun New', font_size=26, color=WHITE)
        eq1 = MathTex(r'L = n\\frac{\\lambda}{2}', font_size=26, color=WHITE)
        eq1_sub = MathTex(r'1.20 = 3 \\times \\frac{\\lambda}{2}', font_size=26, color=WHITE)
        eq1_res = MathTex(r'\\lambda = \\frac{2 \\times 1.20}{3} = 0.8\\,\\mathrm{m}', font_size=26, color=GREEN_C)

        step_group1 = VGroup(step1_title, eq1_text, eq1, eq1_sub, eq1_res).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step_group1.scale_to_fit_width(frame_width * 0.88)
        step_group1.scale_to_fit_height(bottom_zone_height * 0.88)
        step_group1.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15))
        self.play(Write(eq1_text))
        self.play(Write(eq1))
        self.wait(1.5)
        self.play(TransformMatchingTex(eq1, eq1_sub))
        self.wait(1.5)
        self.play(TransformMatchingTex(eq1_sub, eq1_res))
        self.wait(2.5)

        step2_title = Text('ขั้นตอนที่ 2: หาอัตราเร็วคลื่น (v)', font='TH Sarabun New', font_size=26, color=BLUE_D)
        eq2 = MathTex(r'v = f\\lambda', font_size=26, color=WHITE)
        eq2_sub = MathTex(r'v = 320 \\times 0.8', font_size=26, color=WHITE)
        
        final_result_text = Text('อัตราเร็ว v = ', font='TH Sarabun New', font_size=26, color=GREEN_C)
        final_result_math = MathTex(r'256\\,\\mathrm{m/s}', font_size=26, color=GREEN_C)
        eq2_res_group = VGroup(final_result_text, final_result_math).arrange(RIGHT, buff=0.1)

        step_group2 = VGroup(step2_title, eq2, eq2_sub, eq2_res_group).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step_group2.scale_to_fit_width(frame_width * 0.88)
        step_group2.scale_to_fit_height(bottom_zone_height * 0.88)
        step_group2.move_to(bottom_center)

        self.play(FadeOut(step_group1, shift=DOWN*0.1), FadeIn(step_group2, shift=UP*0.1))
        self.wait(1.5)
        self.play(Write(eq2))
        self.wait(1.5)
        self.play(TransformMatchingTex(eq2, eq2_sub))
        self.wait(1.5)
        self.play(FadeOut(eq2_sub, shift=DOWN*0.1), FadeIn(eq2_res_group, shift=UP*0.1))
        self.wait(2.5)

        self.play(FadeOut(problem_text, shift=DOWN*0.1), FadeOut(step_group2, shift=DOWN*0.1))
        self.wait(1)