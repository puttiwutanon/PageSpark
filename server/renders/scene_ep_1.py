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
        title = Text('โจทย์ข้อ 9: อัตราส่วนแรงดึงเชือก', font='TH Sarabun New', font_size=28, color=GOLD_B)
        prob_desc = Text('มวล 10 kg แขวนด้วยเชือก 2 เส้น ยาว 1.5 m และ 2 m ยึดกับเพดานห่างกัน 2.5 m', font='TH Sarabun New', font_size=22, color=GRAY_A)
        top_group = VGroup(title, prob_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Middle Zone: Visualization
        scale_factor = 1.5
        pA = np.array([-1.25 * scale_factor, 1.0, 0]) + middle_center
        pB = np.array([1.25 * scale_factor, 1.0, 0]) + middle_center
        pC = np.array([-0.35 * scale_factor, -0.2 * scale_factor, 0]) + middle_center

        ceiling = Line(pA, pB, color=GRAY_C, stroke_width=4)
        ticks = VGroup()
        for i in range(11):
            t_pos = pA + (pB - pA) * (i / 10)
            ticks.add(Line(t_pos, t_pos + np.array([0.1, 0.1, 0]), color=GRAY_C, stroke_width=2))

        line_AC = Line(pA, pC, color=BLUE_C, stroke_width=4)
        line_BC = Line(pB, pC, color=GREEN_C, stroke_width=4)
        
        mass_line = Line(pC, pC + np.array([0, -1.0, 0]), color=RED_C, stroke_width=4)
        mass_box = Rectangle(width=0.8, height=0.6, color=RED_C, fill_color=RED_C, fill_opacity=0.3).move_to(pC + np.array([0, -1.3, 0]))
        mass_text = Text('10 kg', font='TH Sarabun New', font_size=18, color=WHITE).move_to(mass_box.get_center())

        label_T1 = Text('T1 (1.5 m)', font='TH Sarabun New', font_size=18, color=BLUE_C).next_to(line_AC.get_center(), LEFT, buff=0.1)
        label_T2 = Text('T2 (2.0 m)', font='TH Sarabun New', font_size=18, color=GREEN_C).next_to(line_BC.get_center(), RIGHT, buff=0.1)
        label_W = Text('W = 100 N', font='TH Sarabun New', font_size=18, color=RED_C).next_to(mass_box, DOWN, buff=0.1)

        vis_group = VGroup(ceiling, ticks, line_AC, line_BC, mass_line, mass_box, mass_text, label_T1, label_T2, label_W)
        vis_group.scale_to_fit_width(frame_width * 0.85)
        vis_group.move_to(middle_center)

        self.play(Create(ceiling), Create(ticks))
        self.play(Create(line_AC), Create(line_BC))
        self.play(Create(mass_line), Create(mass_box), Write(mass_text))
        self.play(FadeIn(label_T1), FadeIn(label_T2), FadeIn(label_W))
        self.wait(1.5)

        # Bottom Zone: Equations
        step_title = Text('วิธีทำ: ใช้หลักคล้ายของสามเหลี่ยมแรง', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'\frac{T_1}{\mathrm{BC}} = \frac{T_2}{\mathrm{AC}}', font_size=26, color=WHITE)
        eq2 = MathTex(r'\frac{T_1}{T_2} = \frac{\mathrm{BC}}{\mathrm{AC}}', font_size=26, color=WHITE)
        eq3 = MathTex(r'\frac{T_1}{T_2} = \frac{2.0}{1.5} = \frac{4}{3}', font_size=26, color=GREEN_C)

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