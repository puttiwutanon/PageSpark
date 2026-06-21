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

        # --- Problem Variables ---
        h0 = 50.0
        v0 = 25.0
        angle_deg = -37.0 # Downward angle
        g = 10.0
        theta = np.radians(angle_deg)

        vx = v0 * np.cos(theta)
        vy0 = v0 * np.sin(theta)

        # Calculate t_flight using quadratic formula for 0 = h0 + vy0*t - 0.5*g*t^2
        # 0.5*g*t^2 - vy0*t - h0 = 0
        # t = (vy0 + sqrt(vy0^2 + 2*g*h0)) / g (using positive root for time)
        # The formula t = (vy0 + np.sqrt(vy0**2 + 2*g*h0)) / g is also correct for signed vy0
        # Let's use the one derived from the quadratic formula directly for clarity.
        # t = (-b +/- sqrt(b^2 - 4ac)) / 2a where a=0.5g, b=-vy0, c=-h0
        # t = (vy0 +/- sqrt((-vy0)^2 - 4(0.5g)(-h0))) / (2*0.5g)
        # t = (vy0 +/- sqrt(vy0^2 + 2gh0)) / g
        # Since vy0 is negative, we need the positive root for time.
        t_flight = (vy0 + np.sqrt(vy0**2 + 2*g*h0)) / g

        x_range_total = vx * t_flight

        # Rounded values for display
        t_flight_display = round(t_flight, 2)
        x_range_total_display = round(x_range_total, 2)
        vx_display = round(vx, 2)
        vy0_display = round(vy0, 2)

        # --- Manim Objects ---
        # Top Zone: Title and Problem
        title_text = Text('การเคลื่อนที่แบบโพรเจกไทล์: ปาก้อนหินจากตึก (มุมก้ม)', font='TH Sarabun New', font_size=28, color=WHITE)
        if title_text.width > frame_width * 0.88:
            title_text.scale_to_fit_width(frame_width * 0.88)
        if title_text.height > top_zone_height * 0.88:
            title_text.scale_to_fit_height(top_zone_height * 0.88)
        title_text.move_to(top_center)

        problem_q_thai = Text(
            'ชายคนหนึ่งยืนอยู่บนดาดฟ้าตึกสูง 50 เมตร แล้วปาหินก้อนหินออกไปในแนวทำมุมก้ม 37 องศา\n' # Fixed string concatenation
            'กับแนวระดับ ด้วยความเร็ว 25 เมตร/วินาที',
            font='TH Sarabun New', font_size=26, color=WHITE,
            line_spacing=0.8
        )
        problem_q_a = Text('ก. นานเท่าใดวัตถุจึงจะตกถึงพื้น', font='TH Sarabun New', font_size=26, color=WHITE)
        problem_q_b = Text('ข. ก้อนหินตกห่างจากตัวตึกเท่าใด', font='TH Sarabun New', font_size=26, color=WHITE)

        problem_text_group = VGroup(problem_q_thai, problem_q_a, problem_q_b).arrange(
            DOWN, aligned_edge=LEFT, buff=0.15
        )
        # Rule 11: Every VGroup must pass scale_to_fit_width and scale_to_fit_height before move_to
        problem_text_group.scale_to_fit_width(frame_width * 0.88)
        problem_text_group.scale_to_fit_height(top_zone_height * 0.88)
        problem_text_group.move_to(top_center)

        # Middle Zone: Visualization
        x_max_plot = np.ceil(x_range_total / 10) * 10 + 10
        y_max_plot = np.ceil(h0 / 10) * 10 + 10
        x_max_plot = max(x_max_plot, 50)
        y_max_plot = max(y_max_plot, 60)

        axes = Axes(
            x_range=[0, x_max_plot, 10],
            y_range=[0, y_max_plot, 15],
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
        axes_labels = VGroup(x_label, y_label)

        # Trajectory function
        def trajectory(t):
            x = vx * t
            y = h0 + vy0 * t - 0.5 * g * t**2
            return axes.coords_to_point(x, y)

        trajectory_path = ParametricFunction(
            lambda t: trajectory(t),
            t_range=[0, t_flight],
            color=TEAL_C,
            stroke_width=4,
        )

        # Important points
        start_point = axes.coords_to_point(0, h0)
        end_point = axes.coords_to_point(x_range_total, 0)
        
        start_dot = Dot(start_point, color=ORANGE, radius=0.08)
        end_dot = Dot(end_point, color=RED_C, radius=0.08)

        # Initial velocity vector
        arrow_scale = 0.8
        initial_velocity_vector = Arrow(
            start=start_point,
            end=start_point + axes.x_axis.get_unit_size() * vx * arrow_scale * 0.1 + axes.y_axis.get_unit_size() * vy0 * arrow_scale * 0.1,
            buff=0,
            color=GREEN_C,
            stroke_width=4,
            max_tip_length_to_length_ratio=0.25
        )

        # Angle annotation
        angle_arc = Arc(
            start_angle=0,
            angle=theta,
            radius=0.5,
            arc_center=start_point,
            color=YELLOW_C,
            stroke_width=3
        )
        # Rule 9: font_size for MathTex label (26-28), and fixed extra '}'
        angle_label = MathTex(r'37^{\circ}', font_size=26, color=YELLOW_C).next_to(angle_arc, DR, buff=0.05)
        
        # Dashed lines for h0 and x_range_total
        h0_line = DashedLine(axes.coords_to_point(0, 0), start_point, color=GRAY_A, stroke_width=2)
        # Rule 9: font_size for MathTex and Text (26-28)
        h0_label = VGroup(
            MathTex(r'h_0 =', font_size=26, color=GRAY_A),
            Text(f'{int(h0)} ม.', font='TH Sarabun New', font_size=26, color=GRAY_A)
        ).arrange(RIGHT, buff=0.05).next_to(h0_line, LEFT, buff=0.1)

        x_range_line = DashedLine(axes.coords_to_point(x_range_total, 0), end_point, color=GRAY_A, stroke_width=2)
        # Rule 9: font_size for MathTex and Text (26-28)
        x_range_label = VGroup(
            MathTex(r'x =', font_size=26, color=GRAY_A),
            Text(f'{x_range_total_display} ม.', font='TH Sarabun New', font_size=26, color=GRAY_A)
        ).arrange(RIGHT, buff=0.05).next_to(x_range_line, DOWN, buff=0.1)

        # Group all middle zone objects
        axes_group = VGroup(axes, axes_labels, trajectory_path, start_dot, end_dot,
                            initial_velocity_vector, angle_arc, angle_label,
                            h0_line, h0_label, x_range_line, x_range_label)
        
        # Apply scaling and positioning for middle zone
        # Rule 11: Unconditional scaling for VGroup before move_to
        axes_group.scale_to_fit_width(frame_width * 0.88)
        axes_group.scale_to_fit_height(middle_zone_height * 0.88) # Fixed 0.82 to 0.88 as per Rule 11
        axes_group.move_to(middle_center) # Rule 11: move_to after scaling

        # Add objects to the scene to prevent 'Render timed out' error.
        # The error occurs because no Mobjects are added to the scene by default.
        # Adding the main content VGroups will make the scene render successfully.
        # Assuming problem_text_group is the primary content for the top zone.
        self.add(problem_text_group)
        self.add(axes_group)