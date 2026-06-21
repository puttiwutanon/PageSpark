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

        # --- Problem 4 Variables and Calculations ---
        h0 = 50.0  # initial height in meters
        v0 = 25.0  # initial speed in m/s
        angle_deg = -37.0  # angle below horizontal in degrees
        g = 10.0  # acceleration due to gravity in m/s^2

        # Calculate derived values
        theta = np.radians(angle_deg)
        vx_calculated = v0 * np.cos(theta)
        vy0_calculated = v0 * np.sin(theta)

        # Solve quadratic equation for time: 0 = h0 + vy0*t - 0.5*g*t^2
        # 0 = 50 + (-15)*t - 0.5*10*t^2  (using approx vx=20, vy0=-15)
        # 5t^2 + 15t - 50 = 0
        # t^2 + 3t - 10 = 0
        # (t+5)(t-2) = 0
        # t = 2 seconds (positive root)
        a = -0.5 * g
        b = vy0_calculated
        c = h0
        discriminant = b**2 - 4*a*c
        t_flight = (-b + np.sqrt(discriminant)) / (2*a)
        if t_flight < 0: # Take the positive root if both are valid, or the only positive one
            t_flight = (-b - np.sqrt(discriminant)) / (2*a)
        t_flight = 2.0 # Use the exact integer from problem's implied solution

        sx_calculated = vx_calculated * t_flight
        sx_calculated = 40.0 # Use the exact integer from problem's implied solution
        vx_calculated = 20.0 # Use the exact integer from problem's implied solution
        vy0_calculated = -15.0 # Use the exact integer from problem's implied solution

        # --- Episode 3: Problem 4 ---
        # 1. Title and Problem Text
        title = Text('การเคลื่อนที่แบบโพรเจกไทล์: ปาก้อนหินทำมุมก้ม', font='TH Sarabun New', font_size=28, color=WHITE)
        if title.width > frame_width * 0.88:
            title.scale_to_fit_width(frame_width * 0.88)
        if title.height > top_zone_height * 0.88:
            title.scale_to_fit_height(top_zone_height * 0.88)
        title.move_to(top_center + UP * top_zone_height * 0.25)

        problem_text_lines = [
            'ชายคนหนึ่งยืนอยู่บนดาดฟ้าตึกสูง 50 เมตร แล้วปาก้อนหินออกไป',
            'ในแนวทำมุมก้ม 37 องศากับแนวระดับ ด้วยความเร็ว 25 เมตร/วินาที',
            'ก. นานเท่าใดวัตถุจึงจะตกถึงพื้น',
            'ข. ก้อนหินตกห่างจากตัวตึกเท่าใด'
        ]
        problem_text = VGroup(*[
            Text(line, font='TH Sarabun New', font_size=26, color=GRAY_A)
            for line in problem_text_lines
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center + DOWN * top_zone_height * 0.15)

        problem_group = VGroup(title, problem_text)
        if problem_group.width > frame_width * 0.88:
            problem_group.scale_to_fit_width(frame_width * 0.88)
        if problem_group.height > top_zone_height * 0.88:
            problem_group.scale_to_fit_height(top_zone_height * 0.88)
        problem_group.move_to(top_center)

        self.play(FadeIn(problem_group, shift=UP*0.15), run_time=3.0)
        self.wait(16.0)

        # 2. Visualization (Middle Zone)
        x_max_val = sx_calculated * 1.25
        y_max_val = h0 * 1.25
        x_step_val = 10
        y_step_val = 15

        axes = Axes(
            x_range=[0, x_max_val, x_step_val],
            y_range=[0, y_max_val, y_step_val],
            x_length=frame_width * 0.60,
            y_length=middle_zone_height * 0.65,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            },
            x_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B, 'numbers_to_exclude': [0]},
            y_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B, 'numbers_to_exclude': [0]},
        )
        
        x_label = axes.get_x_axis_label(
            Text('ระยะทางแนวราบ (m)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง (m)', font='TH Sarabun New', font_size=18, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.30
        )

        def trajectory(t):
            x = vx_calculated * t
            y = h0 + vy0_calculated * t - 0.5 * g * t**2
            return axes.coords_to_point(x, y)

        trajectory_path = ParametricFunction(
            lambda t: trajectory(t),
            t_range=[0, t_flight],
            color=TEAL_C,
            stroke_width=4,
        )

        start_point = axes.coords_to_point(0, h0)
        end_point = axes.coords_to_point(sx_calculated, 0)
        
        start_dot = Dot(start_point, color=ORANGE, radius=0.08)
        end_dot = Dot(end_point, color=RED_C, radius=0.08)

        # Initial velocity vector and components
        v0_vec_length = 1.5
        v0_vec_end_x = 0 + v0_vec_length * np.cos(theta)
        v0_vec_end_y = h0 + v0_vec_length * np.sin(theta)
        initial_velocity_vector = Arrow(
            start=start_point,
            end=axes.coords_to_point(v0_vec_end_x, v0_vec_end_y),
            buff=0,
            color=GREEN_C,
            stroke_width=4,
            tip_length=0.2
        )
        v0_label = MathTex(r'V_0 = 25\,\mathrm{m/s}', font_size=20, color=GREEN_C).next_to(initial_velocity_vector, UR, buff=0.1)

        vx_line = DashedLine(start_point, axes.coords_to_point(v0_vec_end_x, h0), color=GRAY_A)
        vy0_line = DashedLine(axes.coords_to_point(v0_vec_end_x, h0), axes.coords_to_point(v0_vec_end_x, v0_vec_end_y), color=GRAY_A)

        vx_label = MathTex(r'V_x = 20\,\mathrm{m/s}', font_size=20, color=GREEN_C).next_to(vx_line, DOWN, buff=0.1)
        vy0_label = MathTex(r'U_y = -15\,\mathrm{m/s}', font_size=20, color=GREEN_C).next_to(vy0_line, RIGHT, buff=0.1)

        angle_arc = Arc(
            radius=0.5,
            start_angle=0,
            angle=theta,
            arc_center=start_point,
            color=YELLOW_C
        )
        angle_label = MathTex(r'37^\circ', font_size=18, color=YELLOW_C).next_to(angle_arc, DR, buff=0.1)

        h_label_line = DashedLine(start_point, axes.coords_to_point(0, 0), color=GRAY_A)
        h_label_text = MathTex(r'h_0 = 50\,\mathrm{m}', font_size=20, color=GRAY_A).next_to(axes.coords_to_point(0, h0/2), LEFT, buff=0.2)
        h_label = VGroup(h_label_line, h_label_text)

        s_label_line = DashedLine(end_point, axes.coords_to_point(sx_calculated, 0), color=GRAY_A)
        s_label_text = MathTex(r'S_x = ?', font_size=20, color=GRAY_A).next_to(axes.coords_to_point(sx_calculated/2, 0), DOWN, buff=0.2)
        s_label = VGroup(s_label_line, s_label_text)

        axes_group = VGroup(axes, x_label, y_label, trajectory_path, start_dot, end_dot, initial_velocity_vector, v0_label, vx_line, vy0_line, vx_label, vy0_label, angle_arc, angle_label, h_label, s_label)
        
        if axes_group.width > frame_width * 0.88:
            axes_group.scale_to_fit_width(frame_width * 0.88)
        if axes_group.height > middle_zone_height * 0.82:
            axes_group.scale_to_fit_height(middle_zone_height * 0.82)
        
        if axes_group.width < frame_width * 0.55:
            axes_group.scale_to_fit_width(frame_width * 0.55)
        if axes_group.height < middle_zone_height * 0.55:
            axes_group.scale_to_fit_height(middle_zone_height * 0.55)
        
        axes_group.move_to(middle_center)

        self.play(
            Create(axes),
            Create(x_label),
            Create(y_label),
            Create(trajectory_path),
            GrowFromCenter(start_dot),
            GrowFromCenter(end_dot),
            Create(initial_velocity_vector),
            FadeIn(v0_label, shift=UP*0.15),
            Create(vx_line),
            Create(vy0_line),
            FadeIn(vx_label, shift=UP*0.15),
            FadeIn(vy0_label, shift=UP*0.15),
            Create(angle_arc),
            FadeIn(angle_label, shift=UP*0.15),
            Create(h_label),
            Create(s_label),
            run_time=8.0
        )
        self.wait(20.0)

        # 3. Step 1: Resolve initial velocity components
        step1_title = VGroup(
            Text('ขั้นตอนที่ 1:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('แยกองค์ประกอบความเร็วต้น (Vx, Uy)', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15, aligned_edge=LEFT)

        eq_vx_comp = MathTex(r'V_x = V_0 \cos\theta', font_size=26, color=BLUE_C)
        eq_vx_sub = MathTex(r'V_x = 25 \cos(-37^\circ) \approx 20\,\mathrm{m/s}', font_size=26, color=WHITE)
        eq_vy0_comp = MathTex(r'U_y = V_0 \sin\theta', font_size=26, color=BLUE_C)
        eq_vy0_sub = MathTex(r'U_y = 25 \sin(-37^\circ) \approx -15\,\mathrm{m/s}', font_size=26, color=WHITE)

        step1_group = VGroup(step1_title, eq_vx_comp, eq_vx_sub, eq_vy0_comp, eq_vy0_sub).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        
        if step1_group.width > frame_width * 0.88:
            step1_group.scale_to_fit_width(frame_width * 0.88)
        if step1_group.height > bottom_zone_height * 0.88:
            step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15), run_time=1.5)
        self.wait(0.8)
        self.play(Write(eq_vx_comp), run_time=2.0)
        self.wait(0.8)
        self.play(Write(eq_vx_sub), run_time=2.5)
        self.wait(0.8)
        self.play(Write(eq_vy0_comp), run_time=2.0)
        self.wait(0.8)
        self.play(Write(eq_vy0_sub), run_time=2.5)
        self.wait(17.3)

        # 4. Step 2: Find time of flight (t)
        step2_title = VGroup(
            Text('ขั้นตอนที่ 2:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาเวลาที่ก้อนหินตกถึงพื้น (t)', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15, aligned_edge=LEFT)

        eq_sy = MathTex(r'S_y = U_y t + \frac{1}{2} g t^2', font_size=26, color=BLUE_C)
        eq_sy_sub = MathTex(r'0 = h_0 + U_y t - \frac{1}{2} g t^2', font_size=26, color=WHITE)
        eq_quadratic = MathTex(r'0 = 50 - 15t - 5t^2', font_size=26, color=WHITE)
        eq_factor = MathTex(r't^2 + 3t - 10 = 0 \implies (t+5)(t-2) = 0', font_size=26, color=WHITE)
        eq_t_final = MathTex(r't = 2\,\mathrm{s}', font_size=26, color=GREEN_C)

        step2_group = VGroup(step2_title, eq_sy, eq_sy_sub, eq_quadratic, eq_factor, eq_t_final).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        
        if step2_group.width > frame_width * 0.88:
            step2_group.scale_to_fit_width(frame_width * 0.88)
        if step2_group.height > bottom_zone_height * 0.88:
            step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        self.play(FadeOut(step1_group, shift=DOWN*0.1), FadeIn(step2_group, shift=UP*0.15), run_time=1.5)
        self.wait(0.8)
        self.play(Write(eq_sy), run_time=1.5)
        self.wait(0.8)
        self.play(Write(eq_sy_sub), run_time=2.0)
        self.wait(0.8)
        self.play(Write(eq_quadratic), run_time=2.0)
        self.wait(0.8)
        self.play(Write(eq_factor), run_time=2.5)
        self.wait(0.8)
        self.play(Write(eq_t_final), run_time=1.5)
        self.wait(29.0)

        # 5. Step 3: Find horizontal range (sx)
        step3_title = VGroup(
            Text('ขั้นตอนที่ 3:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาระยะทางแนวราบที่ก้อนหินตกห่างจากตัวตึก (Sx)', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15, aligned_edge=LEFT)

        eq_sx = MathTex(r'S_x = V_x t', font_size=26, color=BLUE_C)
        eq_sx_sub = MathTex(r'S_x = 20 (2)', font_size=26, color=WHITE)
        eq_sx_final = MathTex(r'S_x = 40\,\mathrm{m}', font_size=26, color=GREEN_C)

        step3_group = VGroup(step3_title, eq_sx, eq_sx_sub, eq_sx_final).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        
        if step3_group.width > frame_width * 0.88:
            step3_group.scale_to_fit_width(frame_width * 0.88)
        if step3_group.height > bottom_zone_height * 0.88:
            step3_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step3_group.move_to(bottom_center)

        self.play(FadeOut(step2_group, shift=DOWN*0.1), FadeIn(step3_group, shift=UP*0.15), run_time=1.5)
        self.wait(0.8)
        self.play(Write(eq_sx), run_time=1.5)
        self.wait(0.8)
        self.play(Write(eq_sx_sub), run_time=1.5)
        self.wait(0.8)
        self.play(Write(eq_sx_final), run_time=1.5)
        self.wait(14.6)

        # 6. Call to Action
        final_answer_text = Text('ก้อนหินจะใช้เวลา 2 วินาทีในการตกถึงพื้น และตกห่างจากตัวตึก 40 เมตร', font='TH Sarabun New', font_size=28, color=YELLOW_C)
        if final_answer_text.width > frame_width * 0.88:
            final_answer_text.scale_to_fit_width(frame_width * 0.88)
        final_answer_text.move_to(bottom_center)

        self.play(FadeOut(step3_group, shift=DOWN*0.1), FadeIn(final_answer_text, shift=UP*0.15), run_time=1.5)
        self.wait(8.0)
        self.play(FadeOut(final_answer_text, shift=DOWN*0.1), FadeOut(axes_group, shift=DOWN*0.1), FadeOut(problem_group, shift=DOWN*0.1), run_time=2.0)
        self.wait(0.5)