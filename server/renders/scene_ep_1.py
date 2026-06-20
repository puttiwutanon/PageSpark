from manim import *
import numpy as np

class PhysicsScene(Scene):
    def construct(self):
        self.camera.background_color = '#1C1C2E'

        config.pixel_width = 1080
        config.pixel_height = 1920
        config.frame_rate = 60

        frame_height = config.frame_height
        frame_width = config.frame_width

        top_zone_height = frame_height * 0.20
        middle_zone_height = frame_height * 0.45
        bottom_zone_height = frame_height * 0.35

        top_zone_top = frame_height / 2
        top_zone_bottom = top_zone_top - top_zone_height
        top_zone_center = (top_zone_top + top_zone_bottom) / 2

        middle_zone_top = top_zone_bottom
        middle_zone_bottom = middle_zone_top - middle_zone_height
        middle_zone_center = (middle_zone_top + middle_zone_bottom) / 2

        bottom_zone_top = middle_zone_bottom
        bottom_zone_bottom = bottom_zone_top - bottom_zone_height
        bottom_zone_center = (bottom_zone_top + bottom_zone_bottom) / 2

        # --- Problem values ---
        u_x_val = 200
        s_y_val = 2000
        g_val = 10
        u_y_val = 0

        # --- Calculated values ---
        t_val = np.sqrt(2 * s_y_val / g_val)
        s_x_val = u_x_val * t_val

        # --- Scene 1: Problem Statement ---
        problem_title = Text('โจทย์: เครื่องบินทิ้งระเบิด', font='TH Sarabun New', color=GOLD_B, font_size=38)
        problem_text = Text(
            'เครื่องบินบินในแนวระดับด้วยความเร็ว 200 m/s และสูงจากพื้นดิน 2000 m\n'
            'เมื่อทิ้งระเบิดที่ปีกเครื่องบินลงมา จงหาระยะทางแนวราบที่ระเบิดตกไป',
            font='TH Sarabun New', color=WHITE, font_size=32
        )
        problem_group = VGroup(problem_title, problem_text).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        problem_group.scale_to_fit_width(frame_width * 0.85)
        problem_group.scale_to_fit_height(top_zone_height * 0.9)
        problem_group.move_to(top_zone_center)

        given_title = Text('สิ่งที่โจทย์กำหนด', font='TH Sarabun New', color=GOLD_B, font_size=32)
        given_ux = MathTex(r'u_x = 200 \,\mathrm{m/s}', color=BLUE_D, font_size=36)
        given_sy = MathTex(r's_y = 2000 \,\mathrm{m}', color=GREEN_C, font_size=36)
        given_g = MathTex(r'g = 10 \,\mathrm{m/s^2}', color=RED_C, font_size=36)
        given_group = VGroup(given_ux, given_sy, given_g).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        full_given_group = VGroup(given_title, given_group).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        full_given_group.scale_to_fit_width(frame_width * 0.85)
        full_given_group.scale_to_fit_height(bottom_zone_height * 0.9)
        full_given_group.move_to(bottom_zone_center)

        self.play(FadeIn(problem_group, shift=UP*0.15), run_time=1.5)
        self.wait(2)
        self.play(FadeIn(full_given_group, shift=UP*0.15), run_time=1.5)
        self.wait(3)

        self.play(FadeOut(problem_group, shift=DOWN*0.1), FadeOut(full_given_group, shift=DOWN*0.1))
        self.wait(0.5)

        # --- Scene 2: Find Time (t) ---
        x_max_padded = s_x_val * 1.2
        y_max_padded = s_y_val * 1.2
        x_step = 1000
        y_step = 500

        # Adjust axes length to fit middle zone, leaving some padding
        axes_x_length = frame_width * 0.8
        axes_y_length = middle_zone_height * 0.8

        axes = Axes(
            x_range=[0, x_max_padded, x_step],
            y_range=[0, y_max_padded, y_step],
            x_length=axes_x_length,
            y_length=axes_y_length,
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
        axes.move_to(middle_zone_center)

        x_label = axes.get_x_axis_label(Text('ระยะทางแนวราบ s_x (เมตร)', font='TH Sarabun New', font_size=26, color=GRAY_A)).next_to(axes.x_axis.get_end(), DR, buff=0.1)
        y_label = axes.get_y_axis_label(Text('ระยะทางแนวดิ่ง s_y (เมตร)', font='TH Sarabun New', font_size=26, color=GRAY_A)).next_to(axes.y_axis.get_end(), UL, buff=0.1)
        axes_labels = VGroup(x_label, y_label)

        # Plane Mobject (simple representation)
        plane_body = Rectangle(width=1.5, height=0.3, color=BLUE_C, fill_opacity=1)
        plane_wing = Triangle(color=BLUE_C, fill_opacity=1).scale(0.3).rotate(PI/2).next_to(plane_body, RIGHT, buff=0)
        plane = VGroup(plane_body, plane_wing).arrange(RIGHT, buff=0).move_to(axes.c2p(0, s_y_val) + LEFT * 2)

        # Bomb Mobject
        bomb = Dot(point=plane.get_right(), color=RED_C, radius=0.15)
        bomb_label = Text('ระเบิด', font='TH Sarabun New', font_size=24, color=RED_C).next_to(bomb, UP, buff=0.1)

        # Initial velocity vector for bomb (horizontal)
        initial_velocity_vector = Arrow(
            start=bomb.get_center(),
            end=bomb.get_center() + RIGHT * 1.5,
            color=YELLOW_C,
            buff=0
        )
        initial_velocity_label = MathTex(r'u_x = 200 \,\mathrm{m/s}', color=YELLOW_C, font_size=28).next_to(initial_velocity_vector, UP, buff=0.1)
        initial_velocity_group = VGroup(initial_velocity_vector, initial_velocity_label)

        # Projectile path function
        projectile_path = ParametricFunction(
            lambda t: axes.c2p(u_x_val * t, s_y_val - 0.5 * g_val * t**2),
            t_range=[0, t_val, 0.01],
            color=ORANGE,
            stroke_width=3
        )

        self.play(Create(axes), Write(axes_labels), run_time=2)
        self.play(FadeIn(plane, shift=LEFT*0.5), run_time=1)
        self.wait(0.5)
        self.play(FadeIn(bomb, shift=DOWN*0.1), FadeIn(bomb_label, shift=UP*0.1), run_time=0.8)
        self.play(Create(initial_velocity_vector), FadeIn(initial_velocity_label, shift=UP*0.1), run_time=1.2)
        self.wait(1)

        self.play(
            plane.animate.shift(RIGHT * (axes.c2p(s_x_val, s_y_val)[0] - plane.get_center()[0] + 2)),
            MoveAlongPath(bomb, projectile_path),
            FadeOut(initial_velocity_group, shift=DOWN*0.1),
            run_time=t_val, rate_func=linear
        )
        self.wait(1)

        # Equation for time
        calc_time_title = Text('ขั้นตอนที่ 1: หาเวลา (t)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_sy_general = MathTex(r's_y = u_y t + \frac{1}{2}gt^2', color=WHITE, font_size=36)
        eq_sy_sub = MathTex(r'2000 = (0)t + \frac{1}{2}(10)t^2', color=BLUE_D, font_size=36)
        eq_sy_simplify = MathTex(r'2000 = 5t^2', color=BLUE_D, font_size=36)
        eq_t_sq = MathTex(r't^2 = 400', color=BLUE_D, font_size=36)
        eq_t_final = MathTex(r't = 20 \,\mathrm{s}', color=GOLD_B, font_size=36)

        time_eq_group = VGroup(
            calc_time_title,
            eq_sy_general,
            eq_sy_sub,
            eq_sy_simplify,
            eq_t_sq,
            eq_t_final
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        time_eq_group.scale_to_fit_width(frame_width * 0.85)
        time_eq_group.scale_to_fit_height(bottom_zone_height * 0.9)
        time_eq_group.move_to(bottom_zone_center)

        self.play(Write(calc_time_title), run_time=1)
        self.play(Write(eq_sy_general), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(eq_sy_general, eq_sy_sub), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(eq_sy_sub, eq_sy_simplify), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(eq_sy_simplify, eq_t_sq), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(eq_t_sq, eq_t_final), run_time=1.5)
        self.wait(2)

        # Mark final position on graph
        final_pos_dot = Dot(point=axes.c2p(s_x_val, 0), color=GOLD_B, radius=0.08)
        dashed_line_x = DashedLine(axes.c2p(s_x_val, 0), axes.c2p(s_x_val, s_y_val), color=GRAY_B, stroke_width=1.5, dashed_ratio=0.5)
        dashed_line_y = DashedLine(axes.c2p(0, s_y_val), axes.c2p(s_x_val, s_y_val), color=GRAY_B, stroke_width=1.5, dashed_ratio=0.5)

        sy_label_on_graph = MathTex(r's_y = 2000 \,\mathrm{m}', color=GREEN_C, font_size=28).next_to(axes.c2p(0, s_y_val), LEFT, buff=0.2)
        sx_label_on_graph = MathTex(r's_x = ?', color=BLUE_D, font_size=28).next_to(axes.c2p(s_x_val/2, 0), DOWN, buff=0.2)

        self.play(FadeOut(time_eq_group, shift=DOWN*0.1))
        self.wait(0.5)
        self.play(GrowFromCenter(final_pos_dot), Create(dashed_line_x), Create(dashed_line_y), FadeIn(sy_label_on_graph, shift=UP*0.15), FadeIn(sx_label_on_graph, shift=UP*0.15), run_time=1.5)
        self.wait(1)

        # --- Scene 3: Find Horizontal Distance (s_x) ---
        calc_sx_title = Text('ขั้นตอนที่ 2: หาระยะทางแนวราบ (s_x)', font='TH Sarabun New', color=GOLD_B, font_size=32)
        eq_sx_general = MathTex(r's_x = u_x t', color=WHITE, font_size=36)
        eq_sx_sub = MathTex(r's_x = (200)(20)', color=BLUE_D, font_size=36)
        eq_sx_final = MathTex(r's_x = 4000 \,\mathrm{m}', color=GOLD_B, font_size=36)

        sx_eq_group = VGroup(
            calc_sx_title,
            eq_sx_general,
            eq_sx_sub,
            eq_sx_final
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        sx_eq_group.scale_to_fit_width(frame_width * 0.85)
        sx_eq_group.scale_to_fit_height(bottom_zone_height * 0.9)
        sx_eq_group.move_to(bottom_zone_center)

        self.play(Write(calc_sx_title), run_time=1)
        self.play(Write(eq_sx_general), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(eq_sx_general, eq_sx_sub), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(eq_sx_sub, eq_sx_final), run_time=1.5)
        self.wait(2)

        # Update sx label on graph
        sx_label_on_graph_final = MathTex(r's_x = 4000 \,\mathrm{m}', color=BLUE_D, font_size=28).next_to(axes.c2p(s_x_val/2, 0), DOWN, buff=0.2)
        self.play(Transform(sx_label_on_graph, sx_label_on_graph_final))
        self.wait(1)

        # --- Scene 4: Summary & Call to Action ---
        self.play(
            FadeOut(sx_eq_group, shift=DOWN*0.1),
            FadeOut(plane, shift=UP*0.1),
            FadeOut(bomb, shift=DOWN*0.1),
            FadeOut(bomb_label, shift=DOWN*0.1),
            FadeOut(projectile_path, shift=DOWN*0.1),
            FadeOut(final_pos_dot, shift=DOWN*0.1),
            FadeOut(dashed_line_x, shift=DOWN*0.1),
            FadeOut(dashed_line_y, shift=DOWN*0.1),
            FadeOut(sy_label_on_graph, shift=DOWN*0.1),
            FadeOut(sx_label_on_graph_final, shift=DOWN*0.1),
            FadeOut(axes, shift=DOWN*0.1),
            FadeOut(axes_labels, shift=DOWN*0.1),
            run_time=1.5
        )
        self.wait(0.5)

        summary_title = Text('สรุปผลลัพธ์ (ตอนที่ 1)', font='TH Sarabun New', color=GOLD_B, font_size=38)
        summary_t = MathTex(r't = 20 \,\mathrm{s}', color=GOLD_B, font_size=36)
        summary_sx = MathTex(r's_x = 4000 \,\mathrm{m}', color=BLUE_D, font_size=36)
        summary_next = Text('ในตอนหน้า เราจะมาหาความเร็วสุดท้ายของระเบิดกัน!', font='TH Sarabun New', color=WHITE, font_size=32)

        summary_group = VGroup(
            summary_title,
            summary_t,
            summary_sx,
            summary_next
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        summary_group.scale_to_fit_width(frame_width * 0.85)
        summary_group.scale_to_fit_height(frame_height * 0.8)
        summary_group.move_to(ORIGIN)

        self.play(FadeIn(summary_group, shift=UP*0.15), run_time=2)
        self.wait(3)