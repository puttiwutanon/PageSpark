from manim import *
import numpy as np

class ProjectileBombDrop(Scene):
    def construct(self):
        # Boilerplate for screen zoning
        frame_height = config.frame_height
        frame_width = config.frame_width

        top_zone_height = frame_height * 0.18
        bottom_zone_height = frame_height * 0.28
        middle_zone_height = frame_height - top_zone_height - bottom_zone_height

        top_zone_top = frame_height / 2
        top_zone_bottom = top_zone_top - top_zone_height
        top_zone_center = (top_zone_top + top_zone_bottom) / 2

        bottom_zone_bottom = -frame_height / 2
        bottom_zone_top = bottom_zone_bottom + bottom_zone_height
        bottom_zone_center = (bottom_zone_top + bottom_zone_bottom) / 2

        middle_zone_top = top_zone_bottom
        middle_zone_bottom = bottom_zone_top
        middle_zone_center = (middle_zone_top + middle_zone_bottom) / 2

        # Problem statement (Top Zone)
        problem_text_title = Text('โจทย์ปัญหา: เครื่องบินทิ้งระเบิด', font='TH Sarabun New', color=YELLOW)
        problem_text_content = Text(
            'เครื่องบินบินในแนวระดับด้วยความเร็ว 200 m/s และสูงจากพื้นดิน 2000 m\nเมื่อทิ้งระเบิด จงหา ก. ระยะทางแนวราบที่ระเบิดตก',
            font='TH Sarabun New',
            color=WHITE,
            line_spacing=1.2
        )
        problem_group = VGroup(problem_text_title, problem_text_content).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        problem_group.scale_to_fit_width(frame_width * 0.85)
        problem_group.scale_to_fit_height(top_zone_height * 0.9)
        problem_group.move_to(top_zone_center)
        self.play(FadeIn(problem_group))
        self.wait(1)

        # Setup Axes (Middle Zone)
        # Max s_x = 4000m, Max s_y = 2000m
        # Add padding: x_max ~ 4800, y_max ~ 2400
        axes = Axes(
            x_range=[0, 5000, 1000],
            y_range=[0, 2500, 500],
            x_length=frame_width * 0.8, # Fit to middle zone width
            y_length=middle_zone_height * 0.8, # Fit to middle zone height
            axis_config={'color': GRAY, 'include_numbers': True}
        )
        axes.move_to(middle_zone_center)

        x_label = axes.get_x_axis_label(Text('ระยะทางแนวราบ s_x (เมตร)', font='TH Sarabun New', color=WHITE).scale(0.6))
        y_label = axes.get_y_axis_label(Text('ระยะทางแนวดิ่ง s_y (เมตร)', font='TH Sarabun New', color=WHITE).scale(0.6)).rotate(90*DEGREES)
        axes_labels = VGroup(x_label, y_label)

        self.play(Create(axes), Create(axes_labels))
        self.wait(0.5)

        # Initial conditions
        u_x_val = 200
        s_y_initial_val = 2000
        g_val = 10

        # Plane and Bomb Mobjects
        plane_body = Rectangle(width=1.5, height=0.5, color=BLUE_E, fill_opacity=1)
        plane_wing = Triangle(color=BLUE_E, fill_opacity=1).scale(0.5).rotate(90*DEGREES).next_to(plane_body, LEFT, buff=0)
        plane = VGroup(plane_body, plane_wing).scale(0.5)
        plane.move_to(axes.c2p(0, s_y_initial_val) + LEFT * 2)

        bomb = Dot(color=RED, radius=0.15)
        bomb.move_to(axes.c2p(0, s_y_initial_val))

        u_x_arrow = Arrow(start=ORIGIN, end=RIGHT * 1.5, color=YELLOW)
        u_x_label = MathTex(r'u_x = 200 \mathrm{\,m/s}', color=YELLOW).scale(0.6)
        u_x_group = VGroup(u_x_arrow, u_x_label).arrange(DOWN, buff=0.1)
        u_x_group.next_to(plane, UP, buff=0.5)

        self.play(FadeIn(plane), FadeIn(bomb), FadeIn(u_x_group))
        self.wait(1)

        # Animation of bomb drop (Middle Zone)
        # Trajectory function: x(t) = u_x * t, y(t) = s_y_initial - 0.5 * g * t^2
        # Time to fall: t = sqrt(2 * s_y_initial / g) = sqrt(2 * 2000 / 10) = sqrt(400) = 20 s
        # Horizontal distance: s_x = u_x * t = 200 * 20 = 4000 m
        time_to_fall = 20
        final_s_x = 4000

        def get_bomb_trajectory(t):
            x = u_x_val * t
            y = s_y_initial_val - 0.5 * g_val * t**2
            return axes.c2p(x, y)

        trajectory = ParametricFunction(get_bomb_trajectory, t_range=[0, time_to_fall], color=ORANGE)

        self.play(
            plane.animate.shift(axes.c2p(final_s_x, 0) - axes.c2p(0, 0)), # Plane moves horizontally
            MoveAlongPath(bomb, trajectory),
            run_time=time_to_fall / 2, # Speed up animation for video
            rate_func=linear
        )
        self.wait(1)

        # Mark impact point and show s_x, s_y
        impact_dot = Dot(axes.c2p(final_s_x, 0), color=YELLOW)
        dashed_line_x = DashedLine(axes.c2p(final_s_x, 0), axes.c2p(final_s_x, s_y_initial_val), color=GRAY)
        dashed_line_y = DashedLine(axes.c2p(final_s_x, 0), axes.c2p(0, 0), color=GRAY)

        s_x_label_math = MathTex(r's_x = 4000 \mathrm{\,m}', color=ORANGE).scale(0.6)
        s_x_label_math.next_to(impact_dot, DR, buff=0.2)

        s_y_label_math = MathTex(r's_y = 2000 \mathrm{\,m}', color=ORANGE).scale(0.6)
        s_y_label_math.next_to(axes.c2p(0, s_y_initial_val), UL, buff=0.2)

        self.play(Create(impact_dot), Create(dashed_line_x), Create(dashed_line_y), FadeIn(s_x_label_math), FadeIn(s_y_label_math))
        self.wait(1)

        # Calculations (Bottom Zone)
        self.play(FadeOut(problem_group), FadeOut(u_x_group))

        # Step 1: Find time (t) from vertical motion
        step1_title = Text('ขั้นตอนที่ 1: หาสมการการเคลื่อนที่แนวดิ่ง', font='TH Sarabun New', color=YELLOW)
        eq1_1 = MathTex(r's_y = u_y t + \frac{1}{2}gt^2', color=WHITE)
        eq1_2 = MathTex(r'2000 = (0)t + \frac{1}{2}(10)t^2', color=WHITE)
        eq1_3 = MathTex(r'2000 = 5t^2', color=WHITE)
        eq1_4 = MathTex(r't^2 = 400', color=WHITE)
        eq1_5 = MathTex(r't = 20 \mathrm{\,s}', color=GREEN)

        step1_content = VGroup(eq1_1, eq1_2, eq1_3, eq1_4, eq1_5).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step1_group = VGroup(step1_title, step1_content).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step1_group.move_to(bottom_zone_center)

        self.play(FadeIn(step1_group))
        self.wait(3)

        # Step 2: Find horizontal distance (s_x) from horizontal motion
        self.play(FadeOut(step1_group))

        step2_title = Text('ขั้นตอนที่ 2: หาสมการการเคลื่อนที่แนวราบ', font='TH Sarabun New', color=YELLOW)
        eq2_1 = MathTex(r's_x = u_x t', color=WHITE)
        eq2_2 = MathTex(r's_x = (200)(20)', color=WHITE)
        eq2_3 = MathTex(r's_x = 4000 \mathrm{\,m}', color=GREEN)

        step2_content = VGroup(eq2_1, eq2_2, eq2_3).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step2_group = VGroup(step2_title, step2_content).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        step2_group.scale_to_fit_width(frame_width * 0.85)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step2_group.move_to(bottom_zone_center)

        self.play(FadeIn(step2_group))
        self.wait(3)

        # Final answer display (optional, can be combined with step 2)
        final_answer_text = Text('ดังนั้น ระเบิดตกไกล 4000 เมตร', font='TH Sarabun New', color=PINK)
        final_answer_text.scale_to_fit_width(frame_width * 0.85)
        final_answer_text.next_to(step2_group, DOWN, buff=0.5)
        self.play(FadeIn(final_answer_text))
        self.wait(2)

        self.play(FadeOut(final_answer_text), FadeOut(step2_group))
        self.wait(1)
        self.play(FadeOut(axes), FadeOut(axes_labels), FadeOut(plane), FadeOut(bomb), FadeOut(trajectory), FadeOut(impact_dot), FadeOut(dashed_line_x), FadeOut(dashed_line_y), FadeOut(s_x_label_math), FadeOut(s_y_label_math))
        self.wait(1)