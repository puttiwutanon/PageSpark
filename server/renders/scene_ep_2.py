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
        u_x_val = 200
        s_y_val = 2000
        g_val = 10

        # Title
        title = Text('ระเบิดจากเครื่องบิน: ระยะทางและอัตราเร็วสุดท้าย', font='TH Sarabun New', color=GOLD_B, font_size=38)
        title.scale_to_fit_width(frame_width * 0.85)
        title.move_to(top_center)
        self.play(FadeIn(title, shift=UP*0.15), run_time=0.8)
        self.wait(1.5)

        # Axes setup
        x_max_padded = 4000 * 1.2
        y_max_padded = s_y_val * 1.2
        axes = Axes(
            x_range=[0, x_max_padded, 1000],
            y_range=[0, y_max_padded, 500],
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

        # Object and path
        start_point = axes.c2p(0, s_y_val)
        object_dot = Dot(start_point, radius=0.15, color=RED_C)
        object_label = Text('ระเบิด', font='TH Sarabun New', font_size=24, color=WHITE).next_to(object_dot, UP, buff=0.1)

        # Calculate time and s_x first for path
        # s_y = u_y*t + 0.5*g*t^2 => 2000 = 0 + 0.5*10*t^2 => t^2 = 400 => t = 20s
        # s_x = u_x*t = 200 * 20 = 4000m
        t_flight = 20
        s_x_final = 4000
        v_y_final = g_val * t_flight # 10 * 20 = 200 m/s
        v_final_mag = np.sqrt(u_x_val**2 + v_y_final**2) # sqrt(200^2 + 200^2) = 200*sqrt(2)

        def get_projectile_path(t):
            x = u_x_val * t
            y = s_y_val - 0.5 * g_val * t**2
            return axes.c2p(x, y)

        path = ParametricFunction(get_projectile_path, t_range=[0, t_flight, 0.01], color=BLUE_D, stroke_width=3)

        self.play(GrowFromCenter(object_dot), FadeIn(object_label, shift=UP*0.15), run_time=1)
        self.play(MoveAlongPath(object_dot, path), Create(path), run_time=4, rate_func=linear)
        self.play(FadeOut(object_label), run_time=0.5)

        # Initial velocity vector
        ux_vector = Arrow(start=axes.c2p(0, s_y_val), end=axes.c2p(u_x_val/10, s_y_val), buff=0, color=ORANGE, stroke_width=4, tip_length=0.2)
        ux_vector_label = MathTex(r'u_x = 200\,\mathrm{m/s}', color=ORANGE, font_size=28).next_to(ux_vector, UP, buff=0.1)
        self.play(Create(ux_vector), Write(ux_vector_label), run_time=1.5)
        self.wait(1.5)
        self.play(FadeOut(ux_vector), FadeOut(ux_vector_label), run_time=0.8)

        # Part A: Find time (t) and horizontal range (s_x)
        part_a_title = Text('ก. หาระยะทางแนวราบ (s_x)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_sy_general = MathTex(r's_y = u_y t + \frac{1}{2}gt^2', color=BLUE_D, font_size=36)
        eq_sy_sub = MathTex(r'2000 = (0)t + \frac{1}{2}(10)t^2', color=WHITE, font_size=36)
        eq_t_sq = MathTex(r'2000 = 5t^2 \implies t^2 = 400', color=WHITE, font_size=36)
        eq_t_final = MathTex(r't = 20\,\mathrm{s}', color=GREEN_C, font_size=36)
        eq_sx_general = MathTex(r's_x = u_x t', color=BLUE_D, font_size=36)
        eq_sx_sub = MathTex(r's_x = (200)(20)', color=WHITE, font_size=36)
        eq_sx_final = MathTex(r's_x = 4000\,\mathrm{m}', color=GREEN_C, font_size=36)

        part_a_group = VGroup(part_a_title, eq_sy_general, eq_sy_sub, eq_t_sq, eq_t_final, eq_sx_general, eq_sx_sub, eq_sx_final).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        part_a_group.scale_to_fit_width(frame_width * 0.85)
        part_a_group.scale_to_fit_height(bottom_zone_height * 0.9)
        part_a_group.move_to(bottom_center)

        self.play(FadeIn(part_a_title, shift=UP*0.15), run_time=0.8)
        self.play(Write(eq_sy_general), run_time=1.2)
        self.play(Write(eq_sy_sub), run_time=1.2)
        self.play(Write(eq_t_sq), run_time=1)
        self.play(Write(eq_t_final), run_time=1.5)
        self.wait(1.5)
        self.play(Write(eq_sx_general), run_time=1.2)
        self.play(Write(eq_sx_sub), run_time=1.2)
        self.play(Write(eq_sx_final), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(part_a_group, shift=DOWN*0.1), run_time=0.8)

        # Part B: Find final velocity (V)
        part_b_title = Text('ข. หาอัตราเร็วสุดท้าย (V)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_vy_general = MathTex(r'v_y = u_y + gt', color=BLUE_D, font_size=36)
        eq_vy_sub = MathTex(r'v_y = 0 + (10)(20)', color=WHITE, font_size=36)
        eq_vy_final = MathTex(r'v_y = 200\,\mathrm{m/s}', color=GREEN_C, font_size=36)
        eq_v_mag_general = MathTex(r'V = \sqrt{v_x^2 + v_y^2}', color=BLUE_D, font_size=36)
        eq_v_mag_sub = MathTex(r'V = \sqrt{(200)^2 + (200)^2}', color=WHITE, font_size=36)
        eq_v_mag_final = MathTex(r'V = 200\sqrt{2}\,\mathrm{m/s}', color=GREEN_C, font_size=36)

        part_b_group = VGroup(part_b_title, eq_vy_general, eq_vy_sub, eq_vy_final, eq_v_mag_general, eq_v_mag_sub, eq_v_mag_final).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        part_b_group.scale_to_fit_width(frame_width * 0.85)
        part_b_group.scale_to_fit_height(bottom_zone_height * 0.9)
        part_b_group.move_to(bottom_center)

        self.play(FadeIn(part_b_title, shift=UP*0.15), run_time=0.8)
        self.play(Write(eq_vy_general), run_time=1.2)
        self.play(Write(eq_vy_sub), run_time=1.2)
        self.play(Write(eq_vy_final), run_time=1.5)
        self.wait(1.5)
        self.play(Write(eq_v_mag_general), run_time=1.2)
        self.play(Write(eq_v_mag_sub), run_time=1.2)
        self.play(Write(eq_v_mag_final), run_time=1.5)
        self.wait(2)

        # Show final velocity vectors
        end_point_on_axes = axes.c2p(s_x_final, 0)
        vx_vector = Arrow(start=end_point_on_axes, end=axes.c2p(s_x_final + u_x_val/10, 0), buff=0, color=ORANGE, stroke_width=4, tip_length=0.2)
        vy_vector = Arrow(start=end_point_on_axes, end=axes.c2p(s_x_final, -v_y_final/10), buff=0, color=ORANGE, stroke_width=4, tip_length=0.2)
        v_resultant_vector = Arrow(start=end_point_on_axes, end=axes.c2p(s_x_final + u_x_val/10, -v_y_final/10), buff=0, color=RED_C, stroke_width=5, tip_length=0.25)

        vx_label = MathTex(r'v_x = 200\,\mathrm{m/s}', color=ORANGE, font_size=28).next_to(vx_vector, UP, buff=0.1)
        vy_label = MathTex(r'v_y = 200\,\mathrm{m/s}', color=ORANGE, font_size=28).next_to(vy_vector, RIGHT, buff=0.1)
        v_label = MathTex(r'V = 200\sqrt{2}\,\mathrm{m/s}', color=RED_C, font_size=32).next_to(v_resultant_vector, RIGHT, buff=0.1)

        self.play(FadeOut(part_b_group, shift=DOWN*0.1), run_time=0.8)
        self.play(Create(vx_vector), Write(vx_label), Create(vy_vector), Write(vy_label), run_time=1.5)
        self.wait(1)
        self.play(Create(v_resultant_vector), Write(v_label), run_time=1.5)
        self.wait(2)

        self.play(FadeOut(vx_vector), FadeOut(vx_label), FadeOut(vy_vector), FadeOut(vy_label), FadeOut(v_resultant_vector), FadeOut(v_label), FadeOut(axes_group), FadeOut(object_dot), FadeOut(path), FadeOut(title), run_time=1)