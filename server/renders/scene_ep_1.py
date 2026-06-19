from manim import *

class ProjectileMotionProblem2(Scene):
    def construct(self):
        # --- 1. Problem Statement (Top Section) ---
        problem_text = Text(
            '2. เมื่อปาวัตถุออกไปในแนวระดับจากที่สูง 80 เมตร ปรากฏว่าวัตถุตกห่างจากจุดที่ปาในแนวราบ 20 เมตร จงหาอัตราเร็วของวัตถุที่ถูกปาออกไป',
            font='TH Sarabun New', font_size=30, color=WHITE
        ).to_edge(UP, buff=0.5).set_width(config.frame_width * 0.9)
        self.play(Write(problem_text))
        self.wait(1)

        # --- 2. Setup Axes and Initial State (Middle Section) ---
        # Adjust axes for vertical video format and problem scale
        # x_range: 0 to 25 (for sx=20), y_range: 0 to 90 (for sy=80)
        axes = Axes(
            x_range=[0, 25, 5], y_range=[0, 90, 10],
            x_length=6, y_length=8,
            axis_config={'color': GRAY, 'include_numbers': True, 'font_size': 20}
        )
        # Position axes in the middle section, slightly left to allow labels
        axes.move_to(ORIGIN + LEFT * 0.5 + UP * 1.5) # Adjusted position for vertical format
        axes.add_coordinates()

        x_label = Text('ระยะทางแนวราบ (เมตร)', font='TH Sarabun New', font_size=20, color=GRAY).next_to(axes.x_axis, RIGHT, buff=0.1)
        y_label = Text('ความสูง (เมตร)', font='TH Sarabun New', font_size=20, color=GRAY).next_to(axes.y_axis, UP, buff=0.1)
        labels = VGroup(x_label, y_label)

        self.play(Create(axes), Write(labels))
        self.wait(0.5)

        # Initial position of the object (top-left of the path)
        start_point = axes.c2p(0, 80)
        end_point = axes.c2p(20, 0)
        object_dot = Dot(start_point, color=BLUE, radius=0.15)
        self.play(FadeIn(object_dot, scale=0.5))

        # Path of the projectile (parabolic)
        # x(t) = u_x * t, y(t) = H - 0.5 * g * t^2
        # From calculations: u_x = 5 m/s, H = 80 m, g = 10 m/s^2, t_total = 4s
        # So, x(t) = 5t, y(t) = 80 - 5t^2
        projectile_path = ParametricFunction(
            lambda t: axes.c2p(5 * t, 80 - 5 * t**2),
            t_range=[0, 4, 0.01], color=YELLOW
        )

        # Initial horizontal velocity vector
        initial_velocity_arrow = Arrow(start_point, axes.c2p(5, 80), buff=0, color=RED, max_stroke_width_to_length_ratio=0.1)
        initial_velocity_label = MathTex(r'u_x', color=RED).next_to(initial_velocity_arrow, UP, buff=0.1)
        self.play(GrowArrow(initial_velocity_arrow), Write(initial_velocity_label))
        self.wait(0.5)

        # Animate the object moving along the path
        self.play(MoveAlongPath(object_dot, projectile_path), Create(projectile_path), run_time=4)
        self.wait(1)

        # Show s_y and s_x
        s_y_line = DashedLine(axes.c2p(0, 80), axes.c2p(0, 0), color=GREEN)
        s_y_label = MathTex(r's_y = 80 \text{ m}', color=GREEN).next_to(s_y_line, LEFT, buff=0.1)
        s_x_line = DashedLine(axes.c2p(0, 0), axes.c2p(20, 0), color=ORANGE)
        s_x_label = MathTex(r's_x = 20 \text{ m}', color=ORANGE).next_to(s_x_line, DOWN, buff=0.1)

        self.play(Create(s_y_line), Write(s_y_label))
        self.play(Create(s_x_line), Write(s_x_label))
        self.wait(1)

        # Fade out animation elements to make space for calculations
        self.play(
            FadeOut(object_dot), FadeOut(projectile_path), FadeOut(initial_velocity_arrow), FadeOut(initial_velocity_label),
            FadeOut(s_y_line), FadeOut(s_y_label), FadeOut(s_x_line), FadeOut(s_x_label),
            FadeOut(axes), FadeOut(labels)
        )
        self.wait(0.5)

        # --- 3. Calculations (Bottom Section) ---
        # Calculation 1: Find time (t) from vertical motion
        calc_title_1 = Text('ขั้นตอนที่ 1: หาเวลา (t) จากการเคลื่อนที่แนวดิ่ง', font='TH Sarabun New', font_size=28, color=WHITE)
        eq_sy_formula = MathTex(r's_y = u_y t + \frac{1}{2}gt^2', color=YELLOW)
        eq_sy_sub = MathTex(r'80 = (0)t + \frac{1}{2}(10)t^2', color=YELLOW)
        eq_sy_simplify = MathTex(r'80 = 5t^2', color=YELLOW)
        eq_t_squared = MathTex(r't^2 = 16', color=YELLOW)
        
        # Corrected: Separate Thai unit from MathTex to prevent LaTeX render issues
        eq_t_final_val = MathTex(r't = 4', color=YELLOW)
        eq_t_final_unit = Text('วินาที', font='TH Sarabun New', font_size=28, color=YELLOW)
        eq_t_final = VGroup(eq_t_final_val, eq_t_final_unit).arrange(RIGHT, buff=0.1)

        vertical_calcs = VGroup(calc_title_1, eq_sy_formula, eq_sy_sub, eq_sy_simplify, eq_t_squared, eq_t_final)
        vertical_calcs.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        vertical_calcs.to_edge(DOWN, buff=0.5).to_edge(LEFT, buff=0.5)

        self.play(Write(calc_title_1))
        self.play(Write(eq_sy_formula))
        self.wait(1)
        self.play(TransformMatchingTex(eq_sy_formula, eq_sy_sub))
        self.wait(1)
        self.play(TransformMatchingTex(eq_sy_sub, eq_sy_simplify))
        self.wait(1)
        self.play(TransformMatchingTex(eq_sy_simplify, eq_t_squared))
        self.wait(1)
        self.play(FadeOut(eq_t_squared), Write(eq_t_final)) # Fade out old, write VGroup
        self.wait(2)

        # Fade out vertical calculations to make space for horizontal
        self.play(FadeOut(vertical_calcs))
        self.wait(0.5)

        # Calculation 2: Find initial horizontal velocity (u_x)
        calc_title_2 = Text('ขั้นตอนที่ 2: หาความเร็วต้นแนวราบ (u_x)', font='TH Sarabun New', font_size=28, color=WHITE)
        eq_sx_formula = MathTex(r's_x = u_x t', color=BLUE)
        eq_sx_sub = MathTex(r'20 = u_x (4)', color=BLUE)
        eq_ux_final = MathTex(r'u_x = \frac{20}{4}', color=BLUE)
        eq_ux_answer = MathTex(r'u_x = 5 \text{ m/s}', color=BLUE)

        horizontal_calcs = VGroup(calc_title_2, eq_sx_formula, eq_sx_sub, eq_ux_final, eq_ux_answer)
        horizontal_calcs.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        horizontal_calcs.to_edge(DOWN, buff=0.5).to_edge(LEFT, buff=0.5)

        self.play(Write(calc_title_2))
        self.play(Write(eq_sx_formula))
        self.wait(1)
        self.play(TransformMatchingTex(eq_sx_formula, eq_sx_sub))
        self.wait(1)
        self.play(TransformMatchingTex(eq_sx_sub, eq_ux_final))
        self.wait(1)
        self.play(TransformMatchingTex(eq_ux_final, eq_ux_answer))
        self.wait(2)

        # Final Answer
        final_answer_text = Text('ดังนั้น อัตราเร็วของวัตถุที่ถูกปาออกไปคือ 5 เมตร/วินาที', font='TH Sarabun New', font_size=32, color=GREEN)
        final_answer_text.next_to(horizontal_calcs, DOWN, buff=0.5).to_edge(LEFT, buff=0.5)
        self.play(Write(final_answer_text))
        self.wait(3)

        self.play(FadeOut(problem_text), FadeOut(horizontal_calcs), FadeOut(final_answer_text))
        self.wait(1)