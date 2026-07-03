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

        # Top Zone: Title & Problem
        title = Text('โพรเจกไทล์: ปาวัตถุแนวราบ', font='TH Sarabun New', font_size=28, color=GOLD_B)
        prob_line1 = Text('ปาวัตถุจากที่สูง 80 m ตกห่างจากจุดปา 20 m', font='TH Sarabun New', font_size=24, color=GRAY_A)
        prob_line2 = Text('จงหาอัตราเร็วต้นในแนวราบ (u_x)', font='TH Sarabun New', font_size=24, color=GRAY_A)
        top_group = VGroup(title, prob_line1, prob_line2).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if top_group.width > frame_width * 0.88:
            top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Middle Zone: Visualization (Axes + Trajectory)
        axes = Axes(
            x_range=[0, 25, 5],
            y_range=[0, 90, 10],
            x_length=frame_width * 0.60,
            y_length=middle_zone_height * 0.65,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            }
        )
        x_label = axes.get_x_axis_label(
            Text('ระยะทางราบ (m)', font='TH Sarabun New', font_size=16, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.3
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง (m)', font='TH Sarabun New', font_size=16, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.3
        )

        def traj(t):
            return axes.coords_to_point(5 * t, 80 - 5 * t**2)
        
        path = ParametricFunction(traj, t_range=[0, 4], color=TEAL_C, stroke_width=4)
        start_dot = Dot(axes.coords_to_point(0, 80), color=RED_C, radius=0.08)
        end_dot = Dot(axes.coords_to_point(20, 0), color=GREEN_C, radius=0.08)
        
        vis_group = VGroup(axes, x_label, y_label, path, start_dot, end_dot)
        vis_group.scale_to_fit_width(frame_width * 0.88)
        vis_group.scale_to_fit_height(middle_zone_height * 0.82)
        vis_group.move_to(middle_center)
        
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label))
        self.play(Create(path), FadeIn(start_dot), FadeIn(end_dot))
        self.wait(1.0)

        # Bottom Zone: Equations & Steps
        step1_title = Text('ขั้นตอนที่ 1: หาเวลา (t) จากแนวดิ่ง', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1_1 = MathTex(r's_y = u_y t + \\frac{1}{2} g t^2', font_size=26, color=WHITE)
        eq1_2 = MathTex(r'80 = 0 + \\frac{1}{2}(10)t^2', font_size=26, color=WHITE)
        eq1_3 = MathTex(r't^2 = 16 \\Rightarrow t = 4\\,\\mathrm{s}', font_size=26, color=GREEN_C)
        
        step1_group = VGroup(step1_title, eq1_1, eq1_2, eq1_3).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.move_to(bottom_center)
        
        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(2.0)
        
        step2_title = Text('ขั้นตอนที่ 2: หาอัตราเร็วแนวราบ (u_x)', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq2_1 = MathTex(r's_x = u_x t', font_size=26, color=WHITE)
        eq2_2 = MathTex(r'20 = u_x (4)', font_size=26, color=WHITE)
        eq2_3 = MathTex(r'u_x = 5\\,\\mathrm{m/s}', font_size=26, color=GREEN_C)
        
        step2_group = VGroup(step2_title, eq2_1, eq2_2, eq2_3).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.move_to(bottom_center)
        
        self.play(FadeOut(step1_group, shift=DOWN*0.15))
        self.play(FadeIn(step2_group, shift=UP*0.15))
        self.wait(2.0)