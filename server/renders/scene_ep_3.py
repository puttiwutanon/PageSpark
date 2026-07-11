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
        title = Text('โจทย์ข้อ 17: หาระบบสมดุลรอก', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_desc = Text('หาค่ามวล m มากที่สุด และมุม θ ที่ทำให้ระบบยังคงสมดุลได้', font='TH Sarabun New', font_size=24, color=GRAY_A)
        top_group = VGroup(title, problem_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(1.0)

        # Middle zone: Diagram
        junc = middle_center
        string_l = Line(junc, junc + np.array([-1.8, 0, 0]), color=BLUE_C)
        string_d = Line(junc, junc + np.array([0, -1.5, 0]), color=RED_C)
        string_ur = Line(junc, junc + np.array([1.5, 1.5, 0]), color=GREEN_C)

        ceiling = Line(junc + np.array([0.8, 1.5, 0]), junc + np.array([2.2, 1.5, 0]), color=GRAY_C)

        block_l = Rectangle(width=1.0, height=0.7, color=BLUE_C, fill_opacity=0.3).move_to(junc + np.array([-2.3, 0, 0]))
        block_l_text = Text('8 kg', font='TH Sarabun New', font_size=16, color=WHITE).move_to(block_l.get_center())

        block_d = Rectangle(width=0.8, height=0.6, color=RED_C, fill_opacity=0.3).move_to(junc + np.array([0, -1.8, 0]))
        block_d_text = Text('m', font='TH Sarabun New', font_size=16, color=WHITE).move_to(block_d.get_center())

        label_t1_l = MathTex(r'T_1', font_size=20, color=BLUE_C).next_to(string_l.point_from_proportion(0.5), UP, buff=0.05)
        label_t1_d = MathTex(r'T_1', font_size=20, color=RED_C).next_to(string_d.point_from_proportion(0.5), RIGHT, buff=0.05)
        label_t2 = MathTex(r'T_2', font_size=20, color=GREEN_C).next_to(string_ur.point_from_proportion(0.5), UP + LEFT, buff=0.05)

        angle_arc = Arc(radius=0.4, start_angle=0, angle=45*DEGREES, arc_center=junc)
        angle_label = MathTex(r'\theta', font_size=18, color=YELLOW_C).next_to(angle_arc, RIGHT, buff=0.05)

        diagram_group = VGroup(string_l, string_d, string_ur, ceiling, block_l, block_l_text, block_d, block_d_text, label_t1_l, label_t1_d, label_t2, angle_arc, angle_label)
        diagram_group.scale_to_fit_width(frame_width * 0.85)
        diagram_group.scale_to_fit_height(middle_zone_height * 0.85)
        diagram_group.move_to(middle_center)

        self.play(Create(string_l), Create(string_d), Create(string_ur), Create(ceiling))
        self.play(Create(block_l), FadeIn(block_l_text), Create(block_d), FadeIn(block_d_text))
        self.play(FadeIn(label_t1_l), FadeIn(label_t1_d), FadeIn(label_t2))
        self.play(Create(angle_arc), FadeIn(angle_label))
        self.wait(1.5)

        # Bottom zone: Step 1
        step1_title = Text('1. หาแรงตึงเชือก T1 จากมวล 8 kg:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r'T_1 = f_{\max} = \mu N = \mu m_1 g', font_size=20, color=WHITE)
        eq2 = VGroup(
            MathTex(r'T_1 =', font_size=20),
            MathTex(r'0.25 \times 8 \times 10 = 20\,\mathrm{N} \quad \text{--- (1)}', font_size=26),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq2.scale_to_fit_width(frame_width * 0.88)
        step1_group = VGroup(step1_title, eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(2.5)

        # Bottom zone: Step 2
        step2_title = Text('2. หาค่ามวล m จากสมดุลแนวดิ่ง:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq3 = MathTex(r'T_1 = mg \Rightarrow 20 = m(10)', font_size=20, color=WHITE)
        eq4 = MathTex(r'm = 2\,\mathrm{kg}', font_size=20, color=RED_C)
        step2_group = VGroup(step2_title, eq3, eq4).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.move_to(bottom_center)

        self.play(FadeOut(step1_group, shift=DOWN*0.15))
        self.play(FadeIn(step2_group, shift=UP*0.15))
        self.wait(2.5)

        # Bottom zone: Step 3
        step3_title = Text('3. หามุม \theta ที่ปมประสาน:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq5 = VGroup(
            MathTex(r'T_2 \cos \theta =', font_size=20),
            VGroup(MathTex(r'T_1', font_size=20), Text(' และ ', font='TH Sarabun New', font_size=26), MathTex(r'T_2 \sin \theta = T_1', font_size=20)).arrange(RIGHT, buff=0.1),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq5.scale_to_fit_width(frame_width * 0.88)
        eq6 = VGroup(
            MathTex(r'\tan \theta =', font_size=20),
            MathTex(r'\frac{T_1}{T_1} = 1 \Rightarrow \theta = 45^\circ', font_size=20),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        eq6.scale_to_fit_width(frame_width * 0.88)
        step3_group = VGroup(step3_title, eq5, eq6).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step3_group.scale_to_fit_width(frame_width * 0.88)
        step3_group.move_to(bottom_center)

        self.play(FadeOut(step2_group, shift=DOWN*0.15))
        self.play(FadeIn(step3_group, shift=UP*0.15))
        self.wait(3.0)