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

        title = Text('โจทย์ข้อ 14: ทรงกลมพิงกำแพงลื่น', font='TH Sarabun New', font_size=28, color=GOLD_B)
        prob_desc = Text('ทรงกลมหนัก 50 N พิงกำแพงลื่น แขวนด้วยเชือกทำมุม 30° กับกำแพง', font='TH Sarabun New', font_size=22, color=GRAY_A)
        top_group = VGroup(title, prob_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Visualization
        wall = Line(np.array([-1.5, 2.0, 0]) + middle_center, np.array([-1.5, -2.0, 0]) + middle_center, color=GRAY_C, stroke_width=4)
        sphere = Circle(radius=1.0, color=BLUE_C, fill_color=BLUE_C, fill_opacity=0.2).move_to(np.array([-0.5, 0, 0]) + middle_center)
        
        string = Line(np.array([-1.5, 1.73, 0]) + middle_center, sphere.get_center(), color=GREEN_C, stroke_width=4)
        
        arrow_W = Arrow(sphere.get_center(), sphere.get_center() + np.array([0, -1.2, 0]), color=RED_C, buff=0, stroke_width=4)
        arrow_N = Arrow(np.array([-1.5, 0, 0]) + middle_center, sphere.get_center(), color=ORANGE, buff=0, stroke_width=4)

        label_cable = Text('T (30°)', font='TH Sarabun New', font_size=18, color=GREEN_C).next_to(string.get_center(), UR, buff=0.1)
        label_W = Text('W = 50 N', font='TH Sarabun New', font_size=18, color=RED_C).next_to(arrow_W, DOWN, buff=0.1)
        label_N = Text('N', font='TH Sarabun New', font_size=18, color=ORANGE).next_to(arrow_N, UP, buff=0.1)

        vis_group = VGroup(wall, sphere, string, arrow_W, arrow_N, label_cable, label_W, label_N)
        vis_group.scale_to_fit_width(frame_width * 0.85)
        vis_group.move_to(middle_center)

        self.play(Create(wall), Create(sphere))
        self.play(Create(string))
        self.play(Create(arrow_W), Create(arrow_N))
        self.play(FadeIn(label_cable), FadeIn(label_W), FadeIn(label_N))
        self.wait(1.5)

        # Bottom Zone
        step_title = Text('วิธีทำ: สมดุลแรงในแนวราบและแนวดิ่ง', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'T \cos(30^{\circ}) = W \implies T = \frac{50}{\cos(30^{\circ})} \approx 57.7\,\mathrm{N}', font_size=26, color=WHITE)
        eq2 = MathTex(r'N = T \sin(30^{\circ}) = 57.7 \cdot 0.5 \approx 28.9\,\mathrm{N}', font_size=26, color=GREEN_C)

        step_group = VGroup(step_title, eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step_group.scale_to_fit_width(frame_width * 0.88)
        step_group.move_to(bottom_center)

        self.play(Write(step_title))
        self.wait(0.8)
        self.play(Write(eq1))
        self.wait(0.8)
        self.play(Write(eq2))
        self.wait(2.0)