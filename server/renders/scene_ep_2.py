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
        title = Text('โจทย์ข้อ 16: หาแรง F บนพื้นฝืด', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_desc = Text('มวล 10 kg วางบนพื้นฝืด μ = 0.3 หาแรง F ที่ทำให้เคลื่อนที่ด้วยความเร็วคงที่', font='TH Sarabun New', font_size=24, color=GRAY_A)
        top_group = VGroup(title, problem_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Middle zone: Diagram
        junc = middle_center
        surface = Line(junc + np.array([-2.5, -0.8, 0]), junc + np.array([2.5, -0.8, 0]), color=GRAY_C)
        block = Rectangle(width=1.6, height=1.0, color=BLUE_C, fill_opacity=0.3).move_to(junc + np.array([0, -0.3, 0]))
        block_text = Text('10 kg', font='TH Sarabun New', font_size=18, color=WHITE).move_to(block.get_center())

        arrow_f = Arrow(start=block.get_center(), end=block.get_center() + np.array([1.8, 1.04, 0]), color=GOLD_B, tip_length=0.15)
        arrow_n = Arrow(start=block.get_top(), end=block.get_top() + np.array([0, 1.2, 0]), color=GREEN_C, tip_length=0.15)
        arrow_w = Arrow(start=block.get_center(), end=block.get_center() + np.array([0, -1.5, 0]), color=RED_C, tip_length=0.15)
        arrow_f_fric = Arrow(start=block.get_left(), end=block.get_left() + np.array([-1.2, 0, 0]), color=ORANGE, tip_length=0.15)

        label_f = MathTex(r'F', font_size=20, color=GOLD_B).next_to(arrow_f.get_end(), UP + RIGHT, buff=0.05)
        label_n = MathTex(r'N', font_size=20, color=GREEN_C).next_to(arrow_n.get_end(), UP, buff=0.05)
        label_w = MathTex(r'W = 100\,\mathrm{N}', font_size=20, color=RED_C).next_to(arrow_w.get_end(), DOWN, buff=0.05)
        label_fric = MathTex(r'f = \mu N', font_size=20, color=ORANGE).next_to(arrow_f_fric.get_end(), LEFT, buff=0.05)

        angle_arc = Arc(radius=0.5, start_angle=0, angle=30*DEGREES, arc_center=block.get_center())
        angle_label = MathTex(r'30^\circ', font_size=16, color=YELLOW_C).next_to(angle_arc, RIGHT, buff=0.05)

        diagram_group = VGroup(surface, block, block_text, arrow_f, arrow_n, arrow_w, arrow_f_fric, label_f, label_n, label_w, label_fric, angle_arc, angle_label)
        diagram_group.scale_to_fit_width(frame_width * 0.85)
        diagram_group.scale_to_fit_height(middle_zone_height * 0.85)
        diagram_group.move_to(middle_center)

        self.play(Create(surface), Create(block), FadeIn(block_text))
        self.play(Create(arrow_f), Create(arrow_n), Create(arrow_w), Create(arrow_f_fric))
        self.play(FadeIn(label_f), FadeIn(label_n), FadeIn(label_w), FadeIn(label_fric))
        self.play(Create(angle_arc), FadeIn(angle_label))
        self.wait(1.5)

        # Bottom zone: Step 1
        step1_title = Text('1. พิจารณาแนวแกน Y (สมดุลดิ่ง):', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = VGroup(
            MathTex(r'N + F \sin 30^\circ =', font_size=20),
            MathTex(r'W \Rightarrow N + 0.5F = 100', font_size=20),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq1.scale_to_fit_width(frame_width * 0.88)
        eq2 = MathTex(r'N = 100 - 0.5F \quad \text{--- (1)}', font_size=20, color=GREEN_C)
        step1_group = VGroup(step1_title, eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(2.5)

        # Bottom zone: Step 2
        step2_title = Text('2. พิจารณาแนวแกน X (ความเร็วคงที่):', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq3 = VGroup(
            MathTex(r'F \cos 30^\circ =', font_size=20),
            MathTex(r'f \Rightarrow F \cos 30^\circ = \mu N', font_size=20),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq3.scale_to_fit_width(frame_width * 0.88)
        eq4 = VGroup(
            MathTex(r'F \cos 30^\circ =', font_size=20),
            MathTex(r'0.3 N \quad \text{--- (2)}', font_size=26),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq4.scale_to_fit_width(frame_width * 0.88)
        step2_group = VGroup(step2_title, eq3, eq4).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.move_to(bottom_center)

        self.play(FadeOut(step1_group, shift=DOWN*0.15))
        self.play(FadeIn(step2_group, shift=UP*0.15))
        self.wait(2.5)

        # Bottom zone: Step 3
        step3_title = Text('3. แทนค่า (1) ใน (2) เพื่อหาแรง F:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq5 = MathTex(r'F \cos 30^\circ = 0.3(100 - 0.5F)', font_size=20, color=WHITE)
        eq6 = VGroup(
            MathTex(r'0.866F =', font_size=20),
            MathTex(r'30 - 0.15F \Rightarrow 1.016F = 30', font_size=20),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq6.scale_to_fit_width(frame_width * 0.88)
        eq7 = VGroup(
            VGroup(MathTex(r'F \approx 29.5\,\mathrm{N} \quad (', font_size=20), Text('หรือ', font_size=20), MathTex(r'30', font_size=20)).arrange(RIGHT, buff=0.08),
            VGroup(MathTex(r'\mathrm{N}', font_size=20), Text('เมื่อใช้', font_size=20), MathTex(r'\sqrt{3} \approx 1.7)', font_size=26)).arrange(RIGHT, buff=0.08),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq7.scale_to_fit_width(frame_width * 0.88)
        step3_group = VGroup(step3_title, eq5, eq6, eq7).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step3_group.scale_to_fit_width(frame_width * 0.88)
        step3_group.move_to(bottom_center)

        self.play(FadeOut(step2_group, shift=DOWN*0.15))
        self.play(FadeIn(step3_group, shift=UP*0.15))
        self.wait(3.0)