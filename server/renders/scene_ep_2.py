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
        title = Text('โจทย์ข้อ 3: เครื่องบินทิ้งระเบิด', font='TH Sarabun New', font_size=28, color=GOLD_B)
        prob_desc = VGroup(
            Text('บินสูง 2000 m ด้วยความเร็ว 200 m/s', font='TH Sarabun New', font_size=24, color=GRAY_A),
            Text('ก. หาระยะตกแนวราบ ข. หาความเร็วชนพื้น', font='TH Sarabun New', font_size=24, color=GRAY_A)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        
        top_group = VGroup(title, prob_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        if top_group.width > frame_width * 0.88:
            top_group.scale_to_fit_width(frame_width * 0.88)
        top_group.move_to(top_center)
        self.play(FadeIn(top_group, shift=UP*0.15))
        self.wait(0.8)

        # Middle Zone: Visualization
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
            Text('ระยะทาง x (m)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง y (m)', font='TH Sarabun New', font_size=18, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.30
        )
        
        flight_line = Line(
            axes.coords_to_point(-1000, 2000),
            axes.coords_to_point(0, 2000),
            color=GRAY_B,
            stroke_width=2,
            stroke_dash_array=[5, 5]
        )
        
        def traj_func(t):
            x = 200 * t
            y = 2000 - 5 * (t**2)
            return axes.coords_to_point(x, y)
            
        trajectory = ParametricFunction(
            traj_func,
            t_range=[0, 20],
            color=TEAL_C,
            stroke_width=3
        )
        
        dot = Dot(axes.coords_to_point(0, 2000), color=ORANGE, radius=0.08)
        
        axes_group = VGroup(axes, x_label, y_label, flight_line, trajectory, dot)
        axes_group.scale_to_fit_width(frame_width * 0.88)
        axes_group.scale_to_fit_height(middle_zone_height * 0.82)
        axes_group.move_to(middle_center)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(flight_line))
        self.play(Create(trajectory), run_time=2)
        self.play(MoveAlongPath(dot, trajectory), run_time=2)
        self.wait(0.8)

        # Bottom Zone: Equations (Step 1)
        step1_title = Text('ก. หาระยะตกแนวราบ (s_x)', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq1 = MathTex(r's_y = \\frac{1}{2}gt^2 \\Rightarrow 2000 = 5t^2 \\Rightarrow t = 20\\,\\mathrm{s}', font_size=26, color=WHITE)
        eq2 = MathTex(r's_x = v_x t = 200 \\times 20 = 4000\\,\\mathrm{m}', font_size=26, color=GREEN_C)
        
        step1_group = VGroup(step1_title, eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)
        
        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(2.0)
        
        # Bottom Zone: Equations (Step 2)
        self.play(FadeOut(step1_group, shift=DOWN*0.1))
        
        step2_title = Text('ข. หาความเร็วชนพื้น (v)', font='TH Sarabun New', font_size=26, color=GOLD_B)
        eq3 = MathTex(r'v_x = 200\\,\\mathrm{m/s},\\quad v_y = gt = 200\\,\\mathrm{m/s}', font_size=26, color=WHITE)
        eq4 = MathTex(r'v = \\sqrt{v_x^2 + v_y^2} = \\sqrt{200^2 + 200^2}', font_size=26, color=WHITE)
        eq5 = MathTex(r'v = 200\\sqrt{2}\\,\\mathrm{m/s}', font_size=26, color=GREEN_C)
        
        step2_group = VGroup(step2_title, eq3, eq4, eq5).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)
        
        self.play(FadeIn(step2_group, shift=UP*0.15))
        self.wait(2.0)