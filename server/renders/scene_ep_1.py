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

        # --- Problem Parameters ---
        g = 10.0  # m/s^2
        h0 = 50.0 # m (initial height)
        v0 = 25.0 # m/s (initial speed)
        angle_deg = -37.0 # degrees (downwards from horizontal)

        theta = np.radians(angle_deg)
        vx = v0 * np.cos(theta)
        vy0 = v0 * np.sin(theta) # This will be negative

        # Calculate time of flight (t_flight) using quadratic formula for y = 0
        # 0 = h0 + vy0*t - 0.5*g*t**2  =>  0.5*g*t**2 - vy0*t - h0 = 0
        a_quad = 0.5 * g
        b_quad = -vy0
        c_quad = -h0
        discriminant = b_quad**2 - 4 * a_quad * c_quad
        t_flight = (-b_quad + np.sqrt(discriminant)) / (2 * a_quad) # Take positive root

        # Calculate total horizontal range (x_range_total)
        x_range_total = vx * t_flight

        # --- Rounded values for display ---
        vx_rounded = 19.97
        vy0_rounded = -15.05
        t_flight_rounded = 5.01
        x_range_total_rounded = 100.0

        # --- Axes Configuration ---
        x_max_val = x_range_total
        y_max_val = h0

        # Ensure nice tick steps and fit within 5 ticks
        x_axis_end = np.ceil(x_max_val / 20) * 20
        if x_axis_end / 20 > 5 or x_axis_end == 0: # If more than 5 ticks with step 20, or zero range
            x_axis_end = np.ceil(x_max_val / 30) * 30
            x_step = 30
        else:
            x_step = 20
        if x_axis_end == 0: x_axis_end = 10 # Avoid zero range for x if x_max_val is very small
        if x_step == 0: x_step = 10

        y_axis_end = np.ceil(y_max_val / 10) * 10
        if y_axis_end / 10 > 5 or y_axis_end == 0: # If more than 5 ticks with step 10, or zero range
            y_axis_end = np.ceil(y_max_val / 15) * 15
            y_step = 15
        else:
            y_step = 10
        if y_axis_end == 0: y_axis_end = 10 # Avoid zero range for y if y_max_val is very small
        if y_step == 0: y_step = 10

        # --- Scene Elements ---
        # Problem Text (Top Zone)
        problem_text_line1 = Text('ชายคนหนึ่งยืนอยู่บนดาดฟ้าตึกสูง 50 เมตร แล้วปาหินก้อนหินออกไป', font='TH Sarabun New', font_size=28, color=WHITE)
        problem_text_line2 = Text('ในแนวทำมุมก้ม 37 องศากับแนวระดับ ด้วยความเร็ว 25 เมตร/วินาที', font='TH Sarabun New', font_size=28, color=WHITE)
        problem_text_line3 = Text('ก. นานเท่าใดวัตถุจึงจะตกถึงพื้น  ข. ก้อนหินตกห่างจากตัวตึกเท่าใด', font='TH Sarabun New', font_size=28, color=WHITE)
        problem_text = VGroup(problem_text_line1, problem_text_line2, problem_text_line3).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center)

        # Axes (Middle Zone)
        axes = Axes(
            x_range=[0, x_axis_end, x_step],
            y_range=[0, y_axis_end, y_step],
            x_length=frame_width * 0.60,
            y_length=middle_zone_height * 0.65,
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            },
            x_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B},
            y_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B},
        )
        x_label = axes.get_x_axis_label(
            Text('ระยะทางแนวราบ (m)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง (m)', font='TH Sarabun New', font_size=18, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.30
        )

        # Trajectory path
        def trajectory(t):
            x = vx * t
            y = h0 + vy0 * t - 0.5 * g * t**2
            return axes.coords_to_point(x, y)

        path = ParametricFunction(
            lambda t: trajectory(t),
            t_range=[0, t_flight],
            color=TEAL_C,
            stroke_width=4,
        )

        # Dots and Vectors
        start_point = axes.coords_to_point(0, h0)
        end_point = axes.coords_to_point(x_range_total, 0)
        start_dot = Dot(start_point, color=ORANGE, radius=0.08)
        end_dot = Dot(end_point, color=RED_C, radius=0.08)

        # Initial velocity vector
        v0_vector_end = start_point + np.array([vx, vy0, 0]) * 0.15 # Scale for visualization
        initial_velocity_vector = Arrow(start_point, v0_vector_end, buff=0, color=GREEN_C, stroke_width=4, tip_length=0.2)
        v0_label = MathTex(r'\vec{v}_0', color=GREEN_C, font_size=20).next_to(initial_velocity_vector, UR, buff=0.1)

        # Dashed lines for h0 and x_range_total
        h0_line = DashedLine(axes.coords_to_point(0, h0), axes.coords_to_point(0, 0), color=GRAY_A, stroke_width=1.5)
        h0_label_text = MathTex(f'h_0 = {h0:.0f}\\,\\\mathrm{{m}}', color=GRAY_A, font_size=18).next_to(axes.coords_to_point(0, h0/2), LEFT, buff=0.2)

        x_range_line = DashedLine(axes.coords_to_point(x_range_total, 0), axes.coords_to_point(0, 0), color=GRAY_A, stroke_width=1.5)
        x_range_label_text = MathTex(f'S_x = {x_range_total_rounded:.0f}\\,\\\mathrm{{m}}', color=GRAY_A, font_size=18).next_to(axes.coords_to_point(x_range_total/2, 0), DOWN, buff=0.2)

        # Group all axes related objects
        axes_group = VGroup(axes, x_label, y_label, path, start_dot, end_dot, initial_velocity_vector, v0_label, h0_line, h0_label_text, x_range_line, x_range_label_text)
        axes_group.scale_to_fit_width(frame_width * 0.88)
        axes_group.scale_to_fit_height(middle_zone_height * 0.88) # Fixed: Changed from 0.82 to 0.88 as per Rule 10
        # Ensure it's not too small (BUG #4-ก)
        if axes_group.width < frame_width * 0.55:
            axes_group.scale_to_fit_width(frame_width * 0.55)
        if axes_group.height < middle_zone_height * 0.55:
            axes_group.scale_to_fit_height(middle_zone_height * 0.55)
        axes_group.move_to(middle_center)

        # --- Call to Action (Bottom Zone) ---
        cta_text_line1 = Text('การแยกวิเคราะห์การเคลื่อนที่ในแต่ละแกน', font='TH Sarabun New', font_size=28, color=WHITE)
        cta_text_line2 = Text('ช่วยให้แก้โจทย์โพรเจกไทล์ได้อย่างเป็นระบบ', font='TH Sarabun New', font_size=28, color=WHITE)
        cta_text = VGroup(cta_text_line1, cta_text_line2).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if cta_text.width > frame_width * 0.88:
            cta_text.scale_to_fit_width(frame_width * 0.88)
        if cta_text.height > bottom_zone_height * 0.88:
            cta_text.scale_to_fit_height(bottom_zone_height * 0.88)
        cta_text.move_to(bottom_center) # Fixed: Added missing move_to for cta_text

        # --- Animations ---
        # Fixed: Added self.play() calls to animate the scene and ensure video duration > 30s (Rule 15)
        self.play(Create(problem_text))
        self.wait(3)
        self.play(Create(axes), Create(x_label), Create(y_label))
        self.wait(3)
        self.play(Create(path), Create(start_dot), Create(end_dot))
        self.wait(5)
        self.play(Create(initial_velocity_vector), Write(v0_label))
        self.wait(5)
        self.play(Create(h0_line), Write(h0_label_text))
        self.wait(5)
        self.play(Create(x_range_line), Write(x_range_label_text))
        self.wait(5)
        self.play(Create(cta_text))
        self.wait(5)