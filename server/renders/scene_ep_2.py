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

        # Top Zone Content
        title = Text('โพรเจกไทล์: การทิ้งระเบิดจากเครื่องบิน', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_text = VGroup(
            Text('เครื่องบินบินแนวระดับเร็ว 200 m/s สูงจากพื้น 2000 m', font='TH Sarabun New', font_size=22, color=GRAY_A),
            Text('ก. หาระยะตกแนวราบ  ข. หาอัตราเร็วขณะกระทบพื้น', font='TH Sarabun New', font_size=22, color=GRAY_A)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        top_group = VGroup(title, problem_text).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))

        # Middle Zone Content (Visualization)
        axes = Axes(
            x_range=[0, 5000, 1000],
            y_range=[0, 2500, 500],
            x_length=frame_width * 0.60,
            y_length=middle_zone_height * 0.65,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            }
        )
        x_label = axes.get_x_axis_label(
            Text('ระยะทางแนวราบ (m)', font='TH Sarabun New', font_size=16, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.3
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง (m)', font='TH Sarabun New', font_size=16, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.3
        )

        def traj_func(t):
            return axes.coords_to_point(200 * t, 2000 - 5 * (t**2))

        trajectory = ParametricFunction(traj_func, t_range=[0, 20], color=TEAL_C, stroke_width=4)
        start_dot = Dot(axes.coords_to_point(0, 2000), color=BLUE_C, radius=0.08)
        end_dot = Dot(axes.coords_to_point(4000, 0), color=RED_C, radius=0.08)

        start_label = Text('ปล่อยระเบิด (y = 2000 m)', font='TH Sarabun New', font_size=14, color=BLUE_C).next_to(start_dot, RIGHT, buff=0.1)
        end_label = Text('จุดตก (x = 4000 m)', font='TH Sarabun New', font_size=14, color=RED_C).next_to(end_dot, UP, buff=0.1)

        v_vector = Arrow(
            start=axes.coords_to_point(0, 2000),
            end=axes.coords_to_point(1000, 2000),
            buff=0,
            color=YELLOW_C,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.25
        )
        v_vector_label = MathTex(r'u_x = 200\,\mathrm{m/s}', font_size=18, color=YELLOW_C).next_to(v_vector, UP, buff=0.05)

        axes_group = VGroup(axes, x_label, y_label, trajectory, start_dot, end_dot, start_label, end_label, v_vector, v_vector_label)
        axes_group.scale_to_fit_width(frame_width * 0.88)
        axes_group.scale_to_fit_height(middle_zone_height * 0.82)
        axes_group.move_to(middle_center)

        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(FadeIn(start_dot), FadeIn(start_label))
        self.play(Create(v_vector), Write(v_vector_label))
        self.play(Create(trajectory, run_time=2), FadeIn(end_dot), FadeIn(end_label))
        self.wait(0.8)

        # Bottom Zone Content (Step 1)
        step1_title = Text('ก. หาระยะตกแนวราบ (s_x)', font='TH Sarabun New', font_size=26, color=BLUE_C)
        eq1_1 = MathTex(r's_y = u_y t + \frac{1}{2} g t^2 \\implies 2000 = 0 + 5t^2 \\implies t = 20\,\mathrm{s}', font_size=24, color=WHITE)
        eq1_2 = MathTex(r's_x = u_x t = 200 \times 20 = 4000\,\mathrm{m}', font_size=24, color=GREEN_C)

        step1_group = VGroup(step1_title, eq1_1, eq1_2).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        self.play(Write(step1_title))
        self.play(Write(eq1_1))
        self.wait(0.5)
        self.play(Write(eq1_2))
        self.wait(1.5)

        # Bottom Zone Content (Step 2)
        self.play(FadeOut(step1_group))

        step2_title = Text('ข. หาอัตราเร็วขณะกระทบพื้น (v)', font='TH Sarabun New', font_size=26, color=BLUE_C)
        eq2_1 = MathTex(r'v_x = u_x = 200\,\mathrm{m/s}', font_size=24, color=WHITE)
        eq2_2 = MathTex(r'v_y = u_y + gt = 0 + 10(20) = 200\,\mathrm{m/s}', font_size=24, color=WHITE)
        eq2_3 = MathTex(r'v = \sqrt{v_x^2 + v_y^2} = \sqrt{200^2 + 200^2} = 200\sqrt{2}\,\mathrm{m/s}', font_size=24, color=GREEN_C)

        step2_group = VGroup(step2_title, eq2_1, eq2_2, eq2_3).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        self.play(Write(step2_title))
        self.play(Write(eq2_1))
        self.play(Write(eq2_2))
        self.wait(0.5)
        self.play(Write(eq2_3))
        self.wait(2.0)