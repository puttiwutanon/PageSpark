from manim import *
import numpy as np

class Episode2Problem3(Scene):
    def construct(self):
        # 1. Top Section: Problem Statement
        problem_text = Text(
            '3. เครื่องบินทิ้งระเบิด บินในแนวระดับด้วยความเร็ว 200 เมตร/วินาที และสูงจากพื้นดิน 2000 เมตร เมื่อทิ้งระเบิดที่ปีก ลงมา จงหา ก. ระเบิดตกไกลจากตำแหน่งที่ทิ้งตามแนวระดับเท่าใด ข. ระเบิดกระทบพื้นดินด้วยอัตราเร็วเท่าใด',
            font='TH Sarabun New',
            font_size=28,
            color=WHITE
        ).to_edge(UP)
        self.play(Write(problem_text))
        self.wait(1)

        # 2. Middle Section: Animation and Axes
        axes = Axes(
            x_range=[0, 4500, 1000],
            y_range=[0, 2500, 500],
            x_length=7,
            y_length=6,
            axis_config={"color": GRAY, "stroke_width": 2},
            tips=False
        ).to_edge(LEFT, buff=0.5).shift(DOWN*0.5)

        x_label = Text('ระยะทาง (เมตร)', font='TH Sarabun New', font_size=20, color=GRAY).next_to(axes.x_axis, RIGHT, buff=0.1)
        y_label = Text('ความสูง (เมตร)', font='TH Sarabun New', font_size=20, color=GRAY).next_to(axes.y_axis, UP, buff=0.1)
        axes_labels = VGroup(x_label, y_label)

        self.play(Create(axes), Write(axes_labels))
        self.wait(0.5)

        # Airplane (simplified using Manim primitives)
        plane_body = Rectangle(width=1.5, height=0.3, color=WHITE, fill_opacity=1)
        plane_wing = Triangle(color=WHITE, fill_opacity=1).scale(0.2).rotate(PI/2).next_to(plane_body, DOWN, buff=0)
        plane_tail = Triangle(color=WHITE, fill_opacity=1).scale(0.15).rotate(PI/2).next_to(plane_body, LEFT, buff=0)
        plane = VGroup(plane_body, plane_wing, plane_tail).move_to(axes.c2p(0, 2000)).shift(LEFT*1.5)
        self.play(FadeIn(plane))

        # Initial conditions
        ux_val = 200 # m/s
        sy_val = 2000 # m
        g = 10 # m/s^2

        ux_label_plane = MathTex(r'u_x = 200 \text{ m/s}', font='TH Sarabun New', font_size=25, color=BLUE).next_to(plane, UP, buff=0.2)
        sy_label_plane = MathTex(r'S_y = 2000 \text{ m}', font='TH Sarabun New', font_size=25, color=GREEN).next_to(plane, LEFT, buff=0.2)
        self.play(Write(ux_label_plane), Write(sy_label_plane))
        self.wait(1)

        # Calculate time of flight
        # sy = 0.5 * g * t^2 => 2000 = 0.5 * 10 * t^2 => 2000 = 5t^2 => t^2 = 400 => t = 20s
        t_flight = 20 # seconds
        sx_val = ux_val * t_flight # 200 * 20 = 4000 m

        # Bomb drop animation
        bomb = Dot(plane.get_center(), color=RED, radius=0.15)
        self.play(FadeIn(bomb))

        def get_bomb_path(t):
            x = ux_val * t
            y = sy_val - 0.5 * g * t**2
            return axes.c2p(x, y)

        path = ParametricFunction(get_bomb_path, t_range=[0, t_flight, 0.01], color=YELLOW)
        self.play(
            plane.animate.shift(axes.c2p(sx_val, 0) - axes.c2p(0,0)), # Move plane horizontally
            MoveAlongPath(bomb, path),
            run_time=t_flight,
            rate_func=linear
        )

        # Mark landing point
        landing_point = axes.c2p(sx_val, 0)
        landing_dot = Dot(landing_point, color=YELLOW)
        self.play(FadeIn(landing_dot))

        # Dashed line for sx
        sx_line = DashedLine(axes.c2p(0, 0), landing_point, color=RED)
        sx_label = MathTex(r'S_x = 4000 \text{ เมตร}', font='TH Sarabun New', font_size=30, color=RED).next_to(sx_line, DOWN, buff=0.2)
        self.play(Create(sx_line), Write(sx_label))
        self.wait(1)

        # 3. Bottom Section: Calculations
        calc_title = Text('ขั้นตอนการคำนวณ', font='TH Sarabun New', font_size=30, color=WHITE).to_edge(DOWN).shift(UP*2.5).to_edge(LEFT, buff=0.5)
        self.play(Write(calc_title))

        # Part ก: Find sx
        part_a_title = Text('ก. หาระยะที่ระเบิดตกในแนวราบ (S_x)', font='TH Sarabun New', font_size=24, color=WHITE).next_to(calc_title, DOWN, aligned_edge=LEFT, buff=0.3)
        eq_sy_general = MathTex(r'S_y = u_y t + \frac{1}{2}gt^2', font_size=30).next_to(part_a_title, DOWN, aligned_edge=LEFT, buff=0.2)
        eq_sy_sub = MathTex(r'2000 = (0)t + \frac{1}{2}(10)t^2', font_size=30).next_to(eq_sy_general, DOWN, aligned_edge=LEFT, buff=0.1)
        eq_sy_solve = MathTex(r't = 20 \text{ วินาที}', font='TH Sarabun New', font_size=30, color=YELLOW).next_to(eq_sy_sub, DOWN, aligned_edge=LEFT, buff=0.1)

        eq_sx_general = MathTex(r'S_x = u_x t', font_size=30).next_to(eq_sy_solve, DOWN, aligned_edge=LEFT, buff=0.2)
        eq_sx_sub = MathTex(r'S_x = (200)(20)', font_size=30).next_to(eq_sx_general, DOWN, aligned_edge=LEFT, buff=0.1)
        eq_sx_ans = MathTex(r'S_x = 4000 \text{ เมตร}', font='TH Sarabun New', font_size=30, color=RED).next_to(eq_sx_sub, DOWN, aligned_edge=LEFT, buff=0.1)

        self.play(Write(part_a_title))
        self.play(Write(eq_sy_general))
        self.play(TransformMatchingTex(eq_sy_general, eq_sy_sub))
        self.play(TransformMatchingTex(eq_sy_sub, eq_sy_solve))
        self.wait(1)
        self.play(Write(eq_sx_general))
        self.play(TransformMatchingTex(eq_sx_general, eq_sx_sub))
        self.play(TransformMatchingTex(eq_sx_sub, eq_sx_ans))
        self.wait(2)

        self.play(FadeOut(VGroup(part_a_title, eq_sy_solve, eq_sx_ans, eq_sx_sub, eq_sx_general, eq_sy_general, eq_sy_sub)))

        # Part ข: Find final velocity V
        part_b_title = Text('ข. หาอัตราเร็วของระเบิดตอนกระทบพื้น (V)', font='TH Sarabun New', font_size=24, color=WHITE).next_to(calc_title, DOWN, aligned_edge=LEFT, buff=0.3)
        
        # Calculate vy
        eq_vy_general = MathTex(r'v_y = u_y + gt', font_size=30).next_to(part_b_title, DOWN, aligned_edge=LEFT, buff=0.2)
        eq_vy_sub = MathTex(r'v_y = 0 + (10)(20)', font_size=30).next_to(eq_vy_general, DOWN, aligned_edge=LEFT, buff=0.1)
        eq_vy_ans = MathTex(r'v_y = 200 \text{ m/s}', font='TH Sarabun New', font_size=30, color=BLUE).next_to(eq_vy_sub, DOWN, aligned_edge=LEFT, buff=0.1)

        # Calculate V
        eq_v_general = MathTex(r'V = \sqrt{v_x^2 + v_y^2}', font_size=30).next_to(eq_vy_ans, DOWN, aligned_edge=LEFT, buff=0.2)
        eq_v_sub = MathTex(r'V = \sqrt{(200)^2 + (200)^2}', font_size=30).next_to(eq_v_general, DOWN, aligned_edge=LEFT, buff=0.1)
        eq_v_ans = MathTex(r'V = 200\sqrt{2} \text{ m/s}', font='TH Sarabun New', font_size=30, color=YELLOW).next_to(eq_v_sub, DOWN, aligned_edge=LEFT, buff=0.1)

        self.play(Write(part_b_title))
        self.play(Write(eq_vy_general))
        self.play(TransformMatchingTex(eq_vy_general, eq_vy_sub))
        self.play(TransformMatchingTex(eq_vy_sub, eq_vy_ans))
        self.wait(1)
        self.play(Write(eq_v_general))
        self.play(TransformMatchingTex(eq_v_general, eq_v_sub))
        self.play(TransformMatchingTex(eq_v_sub, eq_v_ans))
        self.wait(2)

        # Show final velocity vector on animation (simplified direction for clarity)
        final_v_vec = Arrow(start=landing_point, end=axes.c2p(sx_val + 100, -100), buff=0, color=YELLOW, stroke_width=5)
        final_vx_vec = Arrow(start=landing_point, end=axes.c2p(sx_val + 100, 0), buff=0, color=BLUE, stroke_width=3)
        final_vy_vec = Arrow(start=landing_point, end=axes.c2p(sx_val, -100), buff=0, color=RED, stroke_width=3)
        
        v_label = MathTex(r'V = 200\sqrt{2} \text{ m/s}', font='TH Sarabun New', font_size=25, color=YELLOW).next_to(final_v_vec, DR, buff=0.1)
        vx_label = MathTex(r'v_x = 200 \text{ m/s}', font='TH Sarabun New', font_size=20, color=BLUE).next_to(final_vx_vec, RIGHT, buff=0.1)
        vy_label = MathTex(r'v_y = 200 \text{ m/s}', font='TH Sarabun New', font_size=20, color=RED).next_to(final_vy_vec, DOWN, buff=0.1)

        self.play(Create(final_vx_vec), Create(final_vy_vec))
        self.play(Create(final_v_vec), Write(v_label), Write(vx_label), Write(vy_label))
        self.wait(2)

        self.play(FadeOut(VGroup(problem_text, axes, axes_labels, plane, bomb, landing_dot, sx_line, sx_label, calc_title, part_b_title, eq_vy_general, eq_vy_sub, eq_vy_ans, eq_v_general, eq_v_sub, eq_v_ans, final_v_vec, final_vx_vec, final_vy_vec, v_label, vx_label, vy_label, ux_label_plane, sy_label_plane)))