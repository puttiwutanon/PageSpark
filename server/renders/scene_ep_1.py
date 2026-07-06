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
        title_text = Text('ตอนที่ 1: อัตราส่วนแรงตึงเชือกในสมดุล', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_text = VGroup(
            Text('แขวนมวล 50 kg ในสถานะสมดุลกล', font='TH Sarabun New', font_size=24, color=GRAY_A),
            Text('จงหาอัตราส่วนของแรงตึงเชือก T1 : T2', font='TH Sarabun New', font_size=24, color=GRAY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        top_group = VGroup(title_text, problem_text).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        if top_group.width > frame_width * 0.88:
            top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(0.8)

        # 2. Middle Zone: Visualization
        knot = Dot(point=middle_center, color=WHITE, radius=0.08)
        t1_arrow = Arrow(start=middle_center, end=middle_center + np.array([-2.2, 2.2, 0]), color=BLUE_C, buff=0)
        t2_arrow = Arrow(start=middle_center, end=middle_center + np.array([2.2, 0, 0]), color=GREEN_C, buff=0)
        w_arrow = Arrow(start=middle_center, end=middle_center + np.array([0, -2.2, 0]), color=RED_C, buff=0)

        t1_label = MathTex(r'T_1', font_size=18, color=BLUE_C).next_to(t1_arrow.get_end(), UP+LEFT, buff=0.1)
        t2_label = MathTex(r'T_2', font_size=18, color=GREEN_C).next_to(t2_arrow.get_end(), RIGHT, buff=0.1)
        w_label = MathTex(r'W = 500\,\mathrm{N}', font_size=18, color=RED_C).next_to(w_arrow.get_end(), DOWN, buff=0.1)

        angle_arc = Arc(radius=0.6, start_angle=np.pi, angle=np.pi/4, arc_center=middle_center, color=YELLOW_C)
        angle_label = MathTex(r'45^\circ', font_size=16, color=YELLOW_C).next_to(angle_arc, UP+LEFT, buff=0.05)

        viz_group = VGroup(knot, t1_arrow, t2_arrow, w_arrow, t1_label, t2_label, w_label, angle_arc, angle_label)
        viz_group.scale_to_fit_height(middle_zone_height * 0.8)
        viz_group.move_to(middle_center)
        self.play(Create(viz_group))
        self.wait(0.8)

        # 3. Bottom Zone: Equations
        step_title = Text('ขั้นตอนการคำนวณ:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'\Sigma F_y = 0 \implies T_1 \sin 45^\circ = 500', font_size=26, color=WHITE)
        eq2 = MathTex(r'\Sigma F_x = 0 \implies T_1 \cos 45^\circ = T_2', font_size=26, color=WHITE)
        eq3 = MathTex(r'\frac{T_1}{T_2} = \frac{1}{\cos 45^\circ} = \sqrt{2} \approx 1.414', font_size=26, color=GREEN_C)

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