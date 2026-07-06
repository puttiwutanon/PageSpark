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

        # 1. Top Zone: Title & Problem
        title_text = Text('ตอนที่ 3: สมดุลของระบบสามมวล', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_text = VGroup(
            Text('หาค่ามวล m มากที่สุด และมุม theta', font='TH Sarabun New', font_size=24, color=GRAY_A),
            Text('ที่ทำให้ระบบยังคงอยู่ในสภาวะสมดุลกล', font='TH Sarabun New', font_size=24, color=GRAY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        top_group = VGroup(title_text, problem_text).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        if top_group.width > frame_width * 0.88:
            top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(0.8)

        # 2. Middle Zone: Visualization
        knot = Dot(point=middle_center, color=WHITE, radius=0.08)
        surface = Line(start=middle_center + np.array([-4.0, 0.5, 0]), end=middle_center + np.array([-1.5, 0.5, 0]), color=GRAY_C)
        block = Rectangle(width=1.2, height=0.8, color=BLUE_D, fill_opacity=0.3).move_to(middle_center + np.array([-2.7, 0.9, 0]))
        block_text = Text('8 kg', font='TH Sarabun New', font_size=16, color=WHITE).move_to(block.get_center())

        string1 = Line(start=block.get_right(), end=knot.get_center(), color=GRAY_A)
        string2 = Line(start=knot.get_center(), end=middle_center + np.array([1.8, 1.8, 0]), color=GRAY_A)
        string3 = Line(start=knot.get_center(), end=middle_center + np.array([0, -1.8, 0]), color=GRAY_A)

        mass_m = Rectangle(width=1.0, height=0.8, color=RED_D, fill_opacity=0.3).move_to(middle_center + np.array([0, -2.2, 0]))
        mass_m_text = Text('m', font='TH Sarabun New', font_size=16, color=WHITE).move_to(mass_m.get_center())

        t1_label = MathTex(r'T_1', font_size=18, color=BLUE_C).next_to(string1, UP, buff=0.1)
        t2_label = MathTex(r'T_2', font_size=18, color=GREEN_C).next_to(string2, UR, buff=0.1)
        t3_label = MathTex(r'T_3 = mg', font_size=18, color=RED_C).next_to(string3, RIGHT, buff=0.1)

        angle_arc = Arc(radius=0.6, start_angle=0, angle=np.pi/4, arc_center=middle_center, color=YELLOW_C)
        angle_label = MathTex(r'\theta', font_size=18, color=YELLOW_C).next_to(angle_arc, UR, buff=0.05)

        viz_group = VGroup(knot, surface, block, block_text, string1, string2, string3, mass_m, mass_m_text, t1_label, t2_label, t3_label, angle_arc, angle_label)
        viz_group.scale_to_fit_height(middle_zone_height * 0.8)
        viz_group.move_to(middle_center)
        self.play(Create(viz_group))
        self.wait(0.8)

        # 3. Bottom Zone: Equations
        step_title = Text('ขั้นตอนการคำนวณ:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'T_1 = f_{\max} = 0.25 \times 80 = 20\,\mathrm{N}', font_size=26, color=WHITE)
        eq2 = MathTex(r'\tan\theta = 1 \implies \theta = 45^\circ', font_size=26, color=WHITE)
        eq3 = MathTex(r'm = 2\,\mathrm{kg}', font_size=26, color=GREEN_C)

        step_group = VGroup(step_title, eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step_group.scale_to_fit_width(frame_width * 0.88)
        step_group.scale_to_fit_height(bottom_zone_height * 0.85)
        step_group.move_to(bottom_center)

        self.play(Write(step_title))
        self.wait(0.5)
        self.play(Write(eq1))
        self.wait(0.5)
        self.play(Write(eq2))
        self.wait(0.5)
        self.play(Write(eq3))
        self.wait(1.5)