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

        # --- TOP ZONE: Title & Problem ---
        title = Text('การเคลื่อนที่แบบโพรเจกไทล์แนวราบ', font='TH Sarabun New', font_size=28, color=GOLD_B)
        problem_line1 = Text('ปาวัตถุออกไปในแนวระดับจากที่สูง 80 เมตร', font='TH Sarabun New', font_size=24, color=GRAY_A)
        problem_line2 = Text('ตกห่างจากจุดปาในแนวราบ 20 เมตร จงหาอัตราเร็วต้น', font='TH Sarabun New', font_size=24, color=GRAY_A)
        
        top_group = VGroup(title, problem_line1, problem_line2).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if top_group.width > frame_width * 0.88:
            top_group.scale_to_fit_width(frame_width * 0.88)
        if top_group.height > top_zone_height * 0.88:
            top_group.scale_to_fit_height(top_zone_height * 0.88)
        top_group.move_to(top_center)
        
        self.play(FadeIn(top_group, shift=UP*0.2))
        self.wait(2.0)
        # --- MIDDLE ZONE: Visualization ---
        axes = Axes(
            x_range=[0, 25, 5],
            y_range=[0, 100, 20],
            x_length=5.0,
            y_length=4.0,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            }
        )
        x_label = axes.get_x_axis_label(
            Text('ระยะราบ (m)', font='TH Sarabun New', font_size=16, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.25
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง (m)', font='TH Sarabun New', font_size=16, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.25
        )
        
        height_line = DashedLine(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(0, 80),
            color=RED_C,
            stroke_width=2
        )
        height_label = Text('h = 80 m', font='TH Sarabun New', font_size=14, color=RED_C).next_to(height_line, LEFT, buff=0.1)
        
        range_line = DashedLine(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(20, 0),
            color=BLUE_C,
            stroke_width=2
        )
        range_label = Text('s_x = 20 m', font='TH Sarabun New', font_size=14, color=BLUE_C).next_to(range_line, DOWN, buff=0.1)
        
        axes_group = VGroup(axes, x_label, y_label, height_line, height_label, range_line, range_label)
        axes_group.scale_to_fit_width(frame_width * 0.85)
        axes_group.scale_to_fit_height(middle_zone_height * 0.80)
        axes_group.move_to(middle_center)
        
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label))
        self.wait(1.0)
        self.play(Create(height_line), FadeIn(height_label), Create(range_line), FadeIn(range_label))
        self.wait(1.0)
        
        # Trajectory: x(t) = 5*t, y(t) = 80 - 5*t^2 for t in [0, 4]
        def traj_func(t):
            x = 5.0 * t
            y = 80.0 - 5.0 * (t**2)
            return axes.coords_to_point(x, y)
        
        path = ParametricFunction(traj_func, t_range=[0, 4], color=TEAL_C, stroke_width=4)
        
        # Animate dot moving along trajectory
        dot = Dot(color=YELLOW_C, radius=0.08)
        dot.move_to(axes.coords_to_point(0, 80))
        
        t_tracker = ValueTracker(0)
        dot.add_updater(lambda d: d.move_to(traj_func(t_tracker.get_value())))
        
        self.add(dot)
        self.play(
            Create(path),
            t_tracker.animate.set_value(4),
            run_time=4.0,
            rate_func=linear
        )
        dot.clear_updaters()
        self.wait(2.0)

        # --- BOTTOM ZONE: Step 1 Solve ---
        step1_title = Text('ขั้นตอนที่ 1: หาเวลา (t) จากแนวดิ่ง', font='TH Sarabun New', font_size=24, color=GOLD_B)
        step1_eq1 = MathTex(r's_y = u_y t + \frac{1}{2} g t^2', font_size=24, color=WHITE)
        step1_eq2 = MathTex(r'80 = 0 + \frac{1}{2}(10)t^2', font_size=24, color=WHITE)
        step1_eq3 = MathTex(r'80 = 5t^2 \implies t^2 = 16', font_size=24, color=WHITE)
        step1_eq4 = MathTex(r't = 4\text{ s}', font_size=24, color=GREEN_C)
        
        step1_group = VGroup(step1_title, step1_eq1, step1_eq2, step1_eq3, step1_eq4).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.85)
        step1_group.move_to(bottom_center)
        
        self.play(FadeIn(step1_title, shift=UP*0.1))
        self.wait(1.5)
        self.play(Write(step1_eq1))
        self.wait(2.0)
        self.play(Write(step1_eq2))
        self.wait(2.0)
        self.play(Write(step1_eq3))
        self.wait(2.0)
        self.play(Write(step1_eq4))
        self.wait(3.0)

        # --- BOTTOM ZONE: Step 2 Solve ---
        self.play(FadeOut(step1_group, shift=DOWN*0.1))
        self.wait(0.5)
        
        step2_title = Text('ขั้นตอนที่ 2: หาอัตราเร็วต้น (u_x) จากแนวราบ', font='TH Sarabun New', font_size=24, color=GOLD_B)
        step2_eq1 = MathTex(r's_x = u_x t', font_size=24, color=WHITE)
        step2_eq2 = MathTex(r'20 = u_x (4)', font_size=24, color=WHITE)
        step2_eq3 = MathTex(r'u_x = \frac{20}{4}', font_size=24, color=WHITE)
        ans_label = Text('คำตอบ:', font='TH Sarabun New', font_size=24, color=GOLD_B)
        ans_val = MathTex(r'u_x = 5\text{ m/s}', font_size=24, color=GREEN_C)
        ans_group = VGroup(ans_label, ans_val).arrange(RIGHT, buff=0.2)
        
        step2_group = VGroup(step2_title, step2_eq1, step2_eq2, step2_eq3, ans_group).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        step2_group.scale_to_fit_width(frame_width * 0.85)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.85)
        step2_group.move_to(bottom_center)
        
        self.play(FadeIn(step2_title, shift=UP*0.1))
        self.wait(1.5)
        self.play(Write(step2_eq1))
        self.wait(2.0)
        self.play(Write(step2_eq2))
        self.wait(2.0)
        self.play(Write(step2_eq3))
        self.wait(2.0)
        self.play(FadeIn(ans_group, shift=UP*0.1))
        self.wait(5.0)