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
        bottom_center = np.array([0, bottom_zone_bottom + bottom_zone_height * 0.5, 0])

        # Problem values
        s_y_val = 50
        u_val = 25
        theta_deg = 37
        g_val = 10
        cos_37 = 0.8
        sin_37 = 0.6

        # Title
        title = Text('ปาก้อนหินมุมก้ม: เวลาและระยะทาง', font='TH Sarabun New', color=GOLD_B, font_size=38)
        title.scale_to_fit_width(frame_width * 0.85)
        title.move_to(top_center)
        self.play(FadeIn(title, shift=UP*0.15), run_time=0.8)
        self.wait(1.5)

        # Axes setup
        x_max_padded = 100 * 1.2
        y_max_padded = s_y_val * 1.2
        axes = Axes(
            x_range=[0, x_max_padded, 20],
            y_range=[0, y_max_padded, 10],
            x_length=frame_width * 0.75,
            y_length=middle_zone_height * 0.75,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.2,
                'tip_width': 0.12,
                'include_numbers': False,
            },
            x_axis_config={'include_numbers': True, 'font_size': 22, 'color': GRAY_B},
            y_axis_config={'include_numbers': True, 'font_size': 22, 'color': GRAY_B},
        )
        axes.add_coordinates()

        x_label = Text('ระยะทางแนวราบ (m)', font='TH Sarabun New', font_size=26, color=GRAY_A)
        y_label = Text('ความสูง (m)', font='TH Sarabun New', font_size=26, color=GRAY_A)
        x_label.next_to(axes.get_x_axis().get_end(), DOWN, buff=0.1)
        y_label.next_to(axes.get_y_axis().get_end(), LEFT, buff=0.1)

        axes_group = VGroup(axes, x_label, y_label)
        axes_group.scale_to_fit_height(middle_zone_height * 0.88)
        axes_group.move_to(middle_center)
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label), run_time=2)

        # Building and object
        building_height = s_y_val
        building_width = 10
        building = Rectangle(width=building_width, height=building_height, color=GRAY_A, fill_opacity=0.5)
        building.move_to(axes.c2p(-building_width/2, building_height/2))
        building.align_to(axes.get_origin(), DOWN)
        building.shift(LEFT * (building_width/2 + 0.5)) # Shift left to make space for projectile

        start_point = axes.c2p(0, s_y_val)
        object_dot = Dot(start_point, radius=0.15, color=RED_C)
        object_label = Text('ก้อนหิน', font='TH Sarabun New', font_size=24, color=WHITE).next_to(object_dot, UP, buff=0.1)

        self.play(FadeIn(building), GrowFromCenter(object_dot), FadeIn(object_label, shift=UP*0.15), run_time=1.5)

        # Initial velocity vector and components
        u_x_init = u_val * cos_37 # 25 * 0.8 = 20
        u_y_init = -u_val * sin_37 # -25 * 0.6 = -15 (negative for downward)

        u_vector = Arrow(start=start_point, end=axes.c2p(u_x_init/2, s_y_val + u_y_init/2), buff=0, color=ORANGE, stroke_width=4, tip_length=0.2)
        ux_vector = Arrow(start=start_point, end=axes.c2p(u_x_init/2, s_y_val), buff=0, color=BLUE_D, stroke_width=3, tip_length=0.15)
        uy_vector = Arrow(start=start_point, end=axes.c2p(0, s_y_val + u_y_init/2), buff=0, color=BLUE_D, stroke_width=3, tip_length=0.15)

        u_label = MathTex(r'u = 25\,\mathrm{m/s}', color=ORANGE, font_size=28).next_to(u_vector, UP+RIGHT, buff=0.1)
        theta_label = MathTex(r'\theta = 37^\circ', color=ORANGE, font_size=28).next_to(u_vector, DOWN+RIGHT, buff=0.1)
        ux_label = MathTex(r'u_x', color=BLUE_D, font_size=24).next_to(ux_vector, DOWN, buff=0.1)
        uy_label = MathTex(r'u_y', color=BLUE_D, font_size=24).next_to(uy_vector, LEFT, buff=0.1)

        self.play(Create(u_vector), Write(u_label), Write(theta_label), run_time=1.5)
        self.wait(1)
        self.play(Create(ux_vector), Write(ux_label), Create(uy_vector), Write(uy_label), run_time=1.5)
        self.wait(1.5)
        self.play(FadeOut(u_vector), FadeOut(u_label), FadeOut(theta_label), FadeOut(ux_vector), FadeOut(ux_label), FadeOut(uy_vector), FadeOut(uy_label), run_time=1)

        # Calculate time and s_x for path
        # -50 = -15t + 0.5*10*t^2 => 5t^2 - 15t - 50 = 0 => t^2 - 3t - 10 = 0 => (t-5)(t+2) = 0 => t = 5s
        # s_x = u_x * t = 20 * 5 = 100m
        t_flight = 5
        s_x_final = 100

        def get_projectile_path(t):
            x = u_x_init * t
            y = s_y_val + u_y_init * t - 0.5 * g_val * t**2
            return axes.c2p(x, y)

        path = ParametricFunction(get_projectile_path, t_range=[0, t_flight, 0.01], color=BLUE_D, stroke_width=3)

        self.play(MoveAlongPath(object_dot, path), Create(path), run_time=4, rate_func=linear)
        self.play(FadeOut(object_label), run_time=0.5)

        # Part A: Find time (t)
        part_a_title = Text('ก. หาเวลา (t)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_ux = MathTex(r'u_x = u\cos\theta = 25\cos37^\circ = 25(0.8) = 20\,\mathrm{m/s}', color=WHITE, font_size=32)
        eq_uy = MathTex(r'u_y = -u\sin\theta = -25\sin37^\circ = -25(0.6) = -15\,\mathrm{m/s}', color=WHITE, font_size=32)
        eq_sy_general = MathTex(r's_y = u_y t + \frac{1}{2}gt^2', color=BLUE_D, font_size=36)
        eq_sy_sub = MathTex(r'-50 = (-15)t + \frac{1}{2}(10)t^2', color=WHITE, font_size=36)
        eq_quadratic = MathTex(r'5t^2 - 15t - 50 = 0', color=WHITE, font_size=36)
        eq_quadratic_simp = MathTex(r't^2 - 3t - 10 = 0', color=WHITE, font_size=36)
        eq_factor = MathTex(r'(t-5)(t+2) = 0', color=WHITE, font_size=36)
        eq_t_final = MathTex(r't = 5\,\mathrm{s}', color=GREEN_C, font_size=36)

        part_a_group = VGroup(part_a_title, eq_ux, eq_uy, eq_sy_general, eq_sy_sub, eq_quadratic, eq_quadratic_simp, eq_factor, eq_t_final).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        part_a_group.scale_to_fit_width(frame_width * 0.85)
        part_a_group.scale_to_fit_height(bottom_zone_height * 0.9)
        part_a_group.move_to(bottom_center)

        self.play(FadeIn(part_a_title, shift=UP*0.15), run_time=0.8)
        self.play(Write(eq_ux), run_time=1.2)
        self.play(Write(eq_uy), run_time=1.2)
        self.wait(1)
        self.play(Write(eq_sy_general), run_time=1.2)
        self.play(Write(eq_sy_sub), run_time=1.2)
        self.play(Write(eq_quadratic), run_time=1)
        self.play(Write(eq_quadratic_simp), run_time=1)
        self.play(Write(eq_factor), run_time=1)
        self.play(Write(eq_t_final), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(part_a_group, shift=DOWN*0.1), run_time=0.8)

        # Part B: Find horizontal range (s_x)
        part_b_title = Text('ข. หาระยะทางแนวราบ (s_x)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_sx_general = MathTex(r's_x = u_x t', color=BLUE_D, font_size=36)
        eq_sx_sub = MathTex(r's_x = (20)(5)', color=WHITE, font_size=36)
        eq_sx_final = MathTex(r's_x = 100\,\mathrm{m}', color=GREEN_C, font_size=36)

        part_b_group = VGroup(part_b_title, eq_sx_general, eq_sx_sub, eq_sx_final).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        part_b_group.scale_to_fit_width(frame_width * 0.85)
        part_b_group.scale_to_fit_height(bottom_zone_height * 0.9)
        part_b_group.move_to(bottom_center)

        self.play(FadeIn(part_b_title, shift=UP*0.15), run_time=0.8)
        self.play(Write(eq_sx_general), run_time=1.2)
        self.play(Write(eq_sx_sub), run_time=1.2)
        self.play(Write(eq_sx_final), run_time=1.5)
        self.wait(2)

        # Show s_x label on graph
        sx_line = DashedLine(axes.c2p(s_x_final, 0), axes.c2p(0, 0), color=GRAY_B, stroke_width=1.5, dashed_ratio=0.5)
        sx_label = MathTex(r's_x = 100\,\mathrm{m}', color=GOLD_B, font_size=28).next_to(sx_line, DOWN, buff=0.2)
        self.play(FadeOut(part_b_group, shift=DOWN*0.1), run_time=0.8)
        self.play(Create(sx_line), Write(sx_label), run_time=1.5)
        self.wait(2)

        self.play(FadeOut(sx_line), FadeOut(sx_label), FadeOut(axes_group), FadeOut(object_dot), FadeOut(path), FadeOut(title), FadeOut(building), run_time=1)