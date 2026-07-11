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

        title = Text('โจทย์ข้อ 12: คานยื่นและสายเคเบิล', font='TH Sarabun New', font_size=28, color=GOLD_B)
        prob_desc = Text('คานยื่นเบาติดบานพับรับน้ำหนัก 100 N ดึงด้วยเคเบิลทำมุม 30°', font='TH Sarabun New', font_size=22, color=GRAY_A)
        top_group = VGroup(title, prob_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Visualization
        wall = Line(np.array([-1.5, 2.0, 0]) + middle_center, np.array([-1.5, -2.0, 0]) + middle_center, color=GRAY_C, stroke_width=4)
        hinge = Dot(point=np.array([-1.5, 0, 0]) + middle_center, color=GOLD_B, radius=0.12)
        beam = Line(hinge.get_center(), np.array([1.5, 0, 0]) + middle_center, color=BLUE_C, stroke_width=6)
        cable = Line(np.array([1.5, 0, 0]) + middle_center, np.array([-1.5, 1.73, 0]) + middle_center, color=GREEN_C, stroke_width=4)
        
        load = Rectangle(width=0.6, height=0.6, color=RED_C, fill_color=RED_C, fill_opacity=0.3).move_to(np.array([1.5, -0.6, 0]) + middle_center)
        load_line = Line(np.array([1.5, 0, 0]) + middle_center, load.get_top(), color=RED_C, stroke_width=4)

        label_cable = Text('T (30°)', font='TH Sarabun New', font_size=18, color=GREEN_C).next_to(cable.get_center(), UR, buff=0.1)
        label_W = Text('W = 100 N', font='TH Sarabun New', font_size=18, color=RED_C).next_to(load, DOWN, buff=0.1)

        vis_group = VGroup(wall, hinge, beam, cable, load, load_line, label_cable, label_W)
        vis_group.scale_to_fit_width(frame_width * 0.85)
        vis_group.move_to(middle_center)

        self.play(Create(wall), FadeIn(hinge))
        self.play(Create(beam))
        self.play(Create(cable))
        self.play(Create(load_line), Create(load))
        self.play(FadeIn(label_cable), FadeIn(label_W))
        self.wait(1.5)

        # Bottom Zone
        step_title = Text('วิธีทำ: คิดโมเมนต์รอบจุดหมุน (บานพับ)', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'\Sigma \tau = 0 \\implies T \\sin(30^{\circ}) \cdot L = W \cdot L', font_size=26, color=WHITE)
        eq2 = MathTex(r'T \\sin(30^{\circ}) = 100', font_size=26, color=WHITE)
        eq3 = MathTex(r'T = \frac{100}{0.5} = 200\,\mathrm{N}', font_size=26, color=GREEN_C)

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