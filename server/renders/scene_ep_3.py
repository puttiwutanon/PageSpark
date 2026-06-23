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

        # Helper function for standing wave visualization (for Ep 2 & 3)
        def create_fixed_end_standing_wave_mobject(axes, L, n, amplitude=0.5, color=TEAL_C):
            k = n * np.pi / L
            wave_path = ParametricFunction(
                lambda x: axes.coords_to_point(x, amplitude * np.sin(k * x)),
                t_range=[0, L, 0.01],
                color=color,
                stroke_width=4
            )
            string_line = Line(axes.coords_to_point(0, 0), axes.coords_to_point(L, 0), color=GRAY_C, stroke_width=2)
            
            wall_height = amplitude * 1.5
            left_wall = Line(axes.coords_to_point(0, -wall_height), axes.coords_to_point(0, wall_height), color=GRAY_D, stroke_width=3)
            right_wall = Line(axes.coords_to_point(L, -wall_height), axes.coords_to_point(L, wall_height), color=GRAY_D, stroke_width=3)
            
            nodes = VGroup()
            for i in range(n + 1):
                node_x = i * (L / n)
                nodes.add(Dot(axes.coords_to_point(node_x, 0), color=BLUE_D, radius=0.08))
            
            return VGroup(string_line, wave_path, left_wall, right_wall, nodes)

        # --- Episode 1: Problem 58 ---
        # Python calculations
        f_val_ep1 = 500
        v_val_ep1 = 400
        lambda_val_ep1 = v_val_ep1 / f_val_ep1
        distance_nodes_ep1 = lambda_val_ep1 / 2

        # Problem Text
        title_ep1 = Text('ระยะห่างระหว่างบัพของคลื่นนิ่ง', font='TH Sarabun New', font_size=28, color=WHITE)
        problem_text_ep1 = VGroup(
            Text('ในการทดลองคลื่นนิ่งบนเส้นเชือก ถ้าความถี่ของคลื่นนิ่งเป็น 500 เฮิรตซ์', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('และอัตราเร็วของคลื่นในเส้นเชือกเท่ากับ 400 เมตรต่อวินาที', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('ตำแหน่งบัพสองตำแหน่งที่อยู่ถัดกันจะห่างกันเท่าไร', font='TH Sarabun New', font_size=28, color=WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        
        title_group_ep1 = VGroup(title_ep1, problem_text_ep1).arrange(DOWN, buff=0.2)
        if title_group_ep1.width > frame_width * 0.88:
            title_group_ep1.scale_to_fit_width(frame_width * 0.88)
        if title_group_ep1.height > top_zone_height * 0.88:
            title_group_ep1.scale_to_fit_height(top_zone_height * 0.88)
        title_group_ep1.move_to(top_center)

        # Visualization for Episode 1
        amplitude_ep1 = 0.5
        x_max_plot_ep1 = lambda_val_ep1 * 2.5
        y_max_plot_ep1 = amplitude_ep1 * 1.5
        x_step_plot_ep1 = lambda_val_ep1 / 2
        y_step_plot_ep1 = amplitude_ep1 / 2

        axes_ep1 = Axes(
            x_range=[0, x_max_plot_ep1, x_step_plot_ep1],
            y_range=[-y_max_plot_ep1, y_max_plot_ep1, y_step_plot_ep1],
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
        x_label_ep1 = axes_ep1.get_x_axis_label(
            Text('ตำแหน่ง (m)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )
        y_label_ep1 = axes_ep1.get_y_axis_label(
            Text('การกระจัด', font='TH Sarabun New', font_size=18, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.30
        )
        axes_labels_ep1 = VGroup(x_label_ep1, y_label_ep1)

        k_ep1 = 2 * np.pi / lambda_val_ep1
        wave_path_ep1 = ParametricFunction(
            lambda x: axes_ep1.coords_to_point(x, amplitude_ep1 * np.sin(k_ep1 * x)),
            t_range=[0, x_max_plot_ep1, 0.01],
            color=TEAL_C,
            stroke_width=4
        )

        node_dot1_ep1 = Dot(axes_ep1.coords_to_point(0, 0), color=BLUE_D, radius=0.08)
        node_dot2_ep1 = Dot(axes_ep1.coords_to_point(lambda_val_ep1 / 2, 0), color=BLUE_D, radius=0.08)
        node_dot3_ep1 = Dot(axes_ep1.coords_to_point(lambda_val_ep1, 0), color=BLUE_D, radius=0.08)
        
        brace_ep1 = BraceBetweenPoints(node_dot1_ep1.get_center(), node_dot2_ep1.get_center(), direction=DOWN)
        # Fixed Rule 9: font_size for MathTex (brace_label_ep1) changed from 20 to 26
        brace_label_ep1 = MathTex(r'\frac{\lambda}{2}', font_size=26, color=WHITE).next_to(brace_ep1, DOWN, buff=0.1)
        distance_label_ep1 = Text(f'{distance_nodes_ep1:.1f} m', font='TH Sarabun New', font_size=18, color=WHITE).next_to(brace_label_ep1, DOWN, buff=0.1)

        wave_group_ep1 = VGroup(axes_ep1, axes_labels_ep1, wave_path_ep1, node_dot1_ep1, node_dot2_ep1, node_dot3_ep1, brace_ep1, brace_label_ep1, distance_label_ep1)
        wave_group_ep1.scale_to_fit_width(frame_width * 0.88)
        wave_group_ep1.scale_to_fit_height(middle_zone_height * 0.82)
        if wave_group_ep1.height < middle_zone_height * 0.55:
            wave_group_ep1.scale(middle_zone_height * 0.55 / wave_group_ep1.height)
        if wave_group_ep1.width < frame_width * 0.55:
            wave_group_ep1.scale(frame_width * 0.55 / wave_group_ep1.width)
        wave_group_ep1.move_to(middle_center)
        
        # Equations for Episode 1
        # Fixed Rule 1: [LATEX_IN_TEXT] on original line 135
        step1_title_ep1_part1 = Text('ขั้นตอนที่ 1:', font='TH Sarabun New', font_size=26, color=GOLD_B)
        step1_title_ep1_part2_text = Text('หาความยาวคลื่น', font='TH Sarabun New', font_size=26, color=GOLD_B)
        step1_title_ep1_part2_lambda = MathTex(r'(\lambda)', font_size=26, color=GOLD_B)
        step1_title_ep1_part2_group = VGroup(step1_title_ep1_part2_text, step1_title_ep1_part2_lambda).arrange(RIGHT, buff=0.05)
        step1_title_ep1 = VGroup(step1_title_ep1_part1, step1_title_ep1_part2_group).arrange(RIGHT, buff=0.15)

        eq1_vfl_ep1 = MathTex(r'v = f\lambda', font_size=26, color=BLUE_C)
        eq1_sub_ep1 = MathTex(r'400 \mathrm{ m/s} = (500 \mathrm{ Hz}) \lambda', font_size=26, color=WHITE)
        eq1_ans_ep1 = MathTex(r'\lambda = \frac{400}{500} = 0.8 \mathrm{ m}', font_size=26, color=WHITE)
        
        step2_title_ep1 = VGroup(
            Text('ขั้นตอนที่ 2:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาระยะห่างระหว่างบัพ', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(RIGHT, buff=0.15)
        eq2_d_ep1 = MathTex(r'd = \frac{\lambda}{2}', font_size=26, color=BLUE_C)
        eq2_sub_ep1 = MathTex(r'd = \frac{0.8 \mathrm{ m}}{2}', font_size=26, color=WHITE)
        eq2_ans_ep1 = MathTex(r'd = 0.4 \mathrm{ m}', font_size=26, color=WHITE)

        step_group1_ep1 = VGroup(step1_title_ep1, eq1_vfl_ep1, eq1_sub_ep1, eq1_ans_ep1).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step_group1_ep1.scale_to_fit_width(frame_width * 0.88)
        step_group1_ep1.scale_to_fit_height(bottom_zone_height * 0.88)
        # Fixed Rule 11: Missing move_to for step_group1_ep1
        step_group1_ep1.move_to(bottom_center)

        # Added minimal animations to make the scene runnable (Rule 17)
        self.play(Create(title_group_ep1))
        self.wait(1)
        self.play(Create(wave_group_ep1))
        self.wait(1)
        self.play(Create(step_group1_ep1))
        self.wait(2)