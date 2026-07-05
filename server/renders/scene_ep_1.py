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
        title = Text('โจทย์ข้อ 12: หาค่าน้ำหนัก W ในสภาพสมดุล', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_desc = Text('ระบบเชือกสมดุล มีมวลซ้าย 60 N แขวนอยู่ จงหาค่าน้ำหนัก W', font='TH Sarabun New', font_size=22, color=GRAY_A)
        top_group = VGroup(title, problem_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(0.8)

        # Middle Zone: Force Diagram
        j1 = np.array([-1.5, middle_zone_center_y, 0])
        j2 = np.array([1.5, middle_zone_center_y, 0])
        
        f1_dir = np.array([-np.cos(np.radians(37)), np.sin(np.radians(37)), 0])
        arrow_t1 = Arrow(j1, j1 + f1_dir * 1.5, color=BLUE_C, buff=0, stroke_width=4)
        arrow_t2 = Arrow(j1, j2, color=GREEN_C, buff=0, stroke_width=4)
        arrow_w1 = Arrow(j1, j1 + DOWN * 1.5, color=RED_C, buff=0, stroke_width=4)
        
        f3_dir = np.array([np.cos(np.radians(53)), np.sin(np.radians(53)), 0])
        arrow_t3 = Arrow(j2, j2 + f3_dir * 1.5, color=ORANGE, buff=0, stroke_width=4)
        arrow_w2 = Arrow(j2, j2 + DOWN * 1.5, color=YELLOW_C, buff=0, stroke_width=4)
        
        label_t1 = MathTex(r'T_1', font_size=18, color=BLUE_C).next_to(j1 + f1_dir * 1.5, UP, buff=0.1)
        label_t2 = MathTex(r'T_2', font_size=18, color=GREEN_C).next_to((j1+j2)/2, UP, buff=0.1)
        label_w1 = MathTex(r'60\,\mathrm{N}', font_size=18, color=RED_C).next_to(j1 + DOWN * 1.5, DOWN, buff=0.1)
        label_t3 = MathTex(r'T_3', font_size=18, color=ORANGE).next_to(j2 + f3_dir * 1.5, UP, buff=0.1)
        label_w2 = MathTex(r'W', font_size=18, color=YELLOW_C).next_to(j2 + DOWN * 1.5, DOWN, buff=0.1)
        
        arc1 = Arc(radius=0.4, start_angle=np.pi, angle=np.radians(37), arc_center=j1, color=GRAY_B)
        label_theta1 = MathTex(r'37^{\circ}', font_size=14, color=GRAY_B).next_to(arc1, UP+LEFT, buff=0.05)
        
        arc2 = Arc(radius=0.4, start_angle=0, angle=np.radians(53), arc_center=j2, color=GRAY_B)
        label_theta2 = MathTex(r'53^{\circ}', font_size=14, color=GRAY_B).next_to(arc2, UP+RIGHT, buff=0.05)

        diagram_group = VGroup(
            arrow_t1, arrow_t2, arrow_w1, arrow_t3, arrow_w2,
            label_t1, label_t2, label_w1, label_t3, label_w2,
            arc1, label_theta1, arc2, label_theta2
        )
        diagram_group.scale_to_fit_width(frame_width * 0.85)
        diagram_group.scale_to_fit_height(middle_zone_height * 0.82)
        diagram_group.move_to(middle_center)
        
        self.play(Create(diagram_group))
        self.wait(0.8)

        # Bottom Zone: Step-by-step solving
        step1_title = Text('ขั้นตอนที่ 1: คิดที่จุดเชื่อมต่อซ้าย', font='TH Sarabun New', font_size=26, color=BLUE_C)
        eq1_1 = MathTex(r'\Sigma F_y = 0 \Rightarrow T_1 \sin 37^{\circ} = 60', font_size=26, color=WHITE)
        eq1_2 = MathTex(r'T_1 = \frac{60}{\sin 37^{\circ}} = 100\,\mathrm{N}', font_size=26, color=WHITE)
        eq1_3 = MathTex(r'T_2 = T_1 \cos 37^{\circ} = 100(0.8) = 80\,\mathrm{N}', font_size=26, color=GREEN_C)
        
        step1_group = VGroup(step1_title, eq1_1, eq1_2, eq1_3).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)
        
        self.play(Write(step1_group))
        self.wait(1.5)
        
        self.play(FadeOut(step1_group, shift=DOWN*0.1))
        
        step2_title = Text('ขั้นตอนที่ 2: คิดที่จุดเชื่อมต่อขวา', font='TH Sarabun New', font_size=26, color=ORANGE)
        eq2_1 = MathTex(r'\Sigma F_x = 0 \Rightarrow T_3 \cos 53^{\circ} = T_2 = 80', font_size=26, color=WHITE)
        eq2_2 = MathTex(r'T_3 = \frac{80}{\cos 53^{\circ}} = \frac{400}{3}\,\mathrm{N}', font_size=26, color=WHITE)
        eq2_3 = MathTex(r'W = T_3 \sin 53^{\circ} = \frac{400}{3}(0.8) \approx 106.67\,\mathrm{N}', font_size=26, color=YELLOW_C)
        
        step2_group = VGroup(step2_title, eq2_1, eq2_2, eq2_3).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)
        
        self.play(Write(step2_group))
        self.wait(2.0)