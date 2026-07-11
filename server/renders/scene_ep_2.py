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

        title = Text('โจทย์ข้อ 10: หาความตึงเชือกแขวนกรอบรูป', font='TH Sarabun New', font_size=28, color=GOLD_B)
        prob_desc = Text('กรอบรูปหนัก 10 N แขวนด้วยเชือกทำมุม 120 องศาต่อกันที่จุดกึ่งกลาง', font='TH Sarabun New', font_size=22, color=GRAY_A)
        top_group = VGroup(title, prob_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Visualization
        nail = Dot(point=np.array([0, 1.5, 0]) + middle_center, color=GOLD_B, radius=0.1)
        frame = Rectangle(width=3.0, height=2.0, color=BLUE_C, fill_color=BLUE_C, fill_opacity=0.1).move_to(np.array([0, -1.0, 0]) + middle_center)
        
        p_left = np.array([-1.5, 0, 0]) + middle_center
        p_right = np.array([1.5, 0, 0]) + middle_center
        string_l = Line(nail.get_center(), p_left, color=WHITE, stroke_width=3)
        string_r = Line(nail.get_center(), p_right, color=WHITE, stroke_width=3)

        label_angle = Text('120°', font='TH Sarabun New', font_size=18, color=YELLOW_C).next_to(nail, DOWN, buff=0.2)
        label_W = Text('W = 10 N', font='TH Sarabun New', font_size=18, color=RED_C).next_to(frame, DOWN, buff=0.1)

        vis_group = VGroup(nail, frame, string_l, string_r, label_angle, label_W)
        vis_group.scale_to_fit_width(frame_width * 0.85)
        vis_group.move_to(middle_center)

        self.play(Create(frame), FadeIn(nail))
        self.play(Create(string_l), Create(string_r))
        self.play(FadeIn(label_angle), FadeIn(label_W))
        self.wait(1.5)

        # Bottom Zone
        step_title = Text('วิธีทำ: สมดุลแรงในแนวดิ่ง', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'2T \\sin(30^{\circ}) = W', font_size=26, color=WHITE)
        eq2 = MathTex(r'2T \left(\frac{1}{2}\right) = 10', font_size=26, color=WHITE)
        eq3 = MathTex(r'T = 10\,\mathrm{N}', font_size=26, color=GREEN_C)

        step_group = VGroup(step_title, eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step_group.scale_to_fit_width(frame_width * 0.88)
        step_group.move_to(bottom_center)

        self.play(Write(step_title))
        self.wait(0.8)
        self.play(Write(eq1))
        self.wait(0.8)
        self.play(Write(eq2))
        self.wait(0.8)
        self.play(Write(eq3))
        self.wait(2.0)