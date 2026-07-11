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

        # Top zone
        title = Text('โจทย์ข้อ 15: หาอัตราส่วน T1 : T2', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_desc = Text('แขวนมวล 50 kg ไว้ดังรูป จงหาอัตราส่วน T1 : T2', font='TH Sarabun New', font_size=24, color=GRAY_A)
        top_group = VGroup(title, problem_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Middle zone: Diagram
        junc = middle_center
        wall_l = Line(junc + np.array([-2.0, 1.5, 0]), junc + np.array([-2.0, -1.5, 0]), color=GRAY_C)
        wall_r = Line(junc + np.array([2.0, 1.5, 0]), junc + np.array([2.0, -1.5, 0]), color=GRAY_C)
        string1 = Line(junc, junc + np.array([-1.5, 1.5, 0]), color=BLUE_C)
        string2 = Line(junc, junc + np.array([2.0, 0, 0]), color=GREEN_C)
        string3 = Line(junc, junc + np.array([0, -1.5, 0]), color=RED_C)
        block = Rectangle(width=1.0, height=0.8, color=RED_C, fill_opacity=0.3).move_to(junc + np.array([0, -1.5, 0]))
        block_text = Text('50 kg', font='TH Sarabun New', font_size=18, color=WHITE).move_to(block.get_center())

        label_t1 = MathTex(r'T_1', font_size=20, color=BLUE_C).next_to(string1.point_from_proportion(0.5), UP + LEFT, buff=0.1)
        label_t2 = MathTex(r'T_2', font_size=20, color=GREEN_C).next_to(string2.point_from_proportion(0.5), UP, buff=0.1)
        label_w = MathTex(r'W = 500\,\mathrm{N}', font_size=20, color=RED_C).next_to(block, DOWN, buff=0.1)

        angle_arc = Arc(radius=0.4, start_angle=180*DEGREES, angle=-45*DEGREES, arc_center=junc)
        angle_label = MathTex(r'45^\circ', font_size=16, color=YELLOW_C).next_to(angle_arc, UP + LEFT, buff=0.05)

        diagram_group = VGroup(wall_l, wall_r, string1, string2, string3, block, block_text, label_t1, label_t2, label_w, angle_arc, angle_label)
        diagram_group.scale_to_fit_width(frame_width * 0.85)
        diagram_group.scale_to_fit_height(middle_zone_height * 0.85)
        diagram_group.move_to(middle_center)

        self.play(Create(wall_l), Create(wall_r))
        self.play(Create(string1), Create(string2), Create(string3))
        self.play(Create(block), FadeIn(block_text))
        self.play(FadeIn(label_t1), FadeIn(label_t2), FadeIn(label_w))
        self.play(Create(angle_arc), FadeIn(angle_label))
        self.wait(1.5)

        # Bottom zone: Step 1
        step1_title = Text('1. พิจารณาแนวแกน Y (สมดุล):', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = VGroup(
            MathTex(r'\Sigma F_y =', font_size=20),
            MathTex(r'0 \Rightarrow T_1 \sin 45^\circ = W', font_size=20),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq1.scale_to_fit_width(frame_width * 0.88)
        eq2 = VGroup(
            MathTex(r'T_1 \sin 45^\circ =', font_size=20),
            MathTex(r'500\,\mathrm{N} \quad \text{--- (1)}', font_size=26),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq2.scale_to_fit_width(frame_width * 0.88)
        step1_group = VGroup(step1_title, eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(2.5)

        # Bottom zone: Step 2
        step2_title = Text('2. พิจารณาแนวแกน X (สมดุล):', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq3 = VGroup(
            MathTex(r'\Sigma F_x =', font_size=20),
            MathTex(r'0 \Rightarrow T_1 \cos 45^\circ = T_2 \quad \text{--- (2)}', font_size=26),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq3.scale_to_fit_width(frame_width * 0.88)
        step2_group = VGroup(step2_title, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.move_to(bottom_center)

        self.play(FadeOut(step1_group, shift=DOWN*0.15))
        self.play(FadeIn(step2_group, shift=UP*0.15))
        self.wait(2.5)

        # Bottom zone: Step 3
        step3_title = Text('3. หาอัตราส่วน T1 : T2 จากสมการ (2):', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq4 = VGroup(
            Text('จาก (2): ', font='TH Sarabun New', font_size=20, color=WHITE),
            MathTex(r'T_2 = T_1 \cos 45^\circ', font_size=20, color=WHITE)
        ).arrange(RIGHT, buff=0.1)
        eq5 = VGroup(
            MathTex(r'\frac{T_1}{T_2} =', font_size=20),
            MathTex(r'\frac{1}{\cos 45^\circ} = \sqrt{2} \approx 1.414', font_size=20),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq5.scale_to_fit_width(frame_width * 0.88)
        step3_group = VGroup(step3_title, eq4, eq5).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step3_group.scale_to_fit_width(frame_width * 0.88)
        step3_group.move_to(bottom_center)

        self.play(FadeOut(step2_group, shift=DOWN*0.15))
        self.play(FadeIn(step3_group, shift=UP*0.15))
        self.wait(3.0)