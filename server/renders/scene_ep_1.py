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

        # --- Problem Constants ---
        f_val = 500  # Hz
        v_val = 400  # m/s
        lambda_val = v_val / f_val  # 0.8 m
        dist_nodes_val = lambda_val / 2  # 0.4 m

        # --- Top Zone: Problem Statement ---
        problem_text = VGroup(
            Text('ในการทดลองคลื่นนิ่งบนเส้นเชือก ถ้าความถี่ของคลื่นนิ่งเป็น 500 เฮิรตซ์', font='TH Sarabun New', font_size=28, color=GRAY_A),
            Text('และอัตราเร็วของคลื่นในเส้นเชือกเท่ากับ 400 เมตรต่อวินาที', font='TH Sarabun New', font_size=28, color=GRAY_A),
            Text('ตำแหน่งบัพสองตำแหน่งที่อยู่ถัดกันจะห่างกันเท่าไร', font='TH Sarabun New', font_size=28, color=GRAY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center)

        self.play(FadeIn(problem_text, shift=UP * 0.15))
        self.wait(2.5)

        # --- Middle Zone: Visualization of Standing Wave ---
        x_min_wave = 0
        x_max_wave = lambda_val * 2.5 # Show a bit more than two wavelengths for context
        x_step_wave = lambda_val / 2

        axes = Axes(
            x_range=[x_min_wave, x_max_wave, x_step_wave],
            y_range=[-1, 1, 0.5], # Amplitude for visualization
            x_length=frame_width * 0.60, # Clamped x_length
            y_length=middle_zone_height * 0.30, # Shorter y-length for wave
            axis_config={
                'color': GRAY_C,
                'stroke_width': 2,
                'include_tip': True,
                'tip_length': 0.15,
                'tip_width': 0.10,
            },
            x_axis_config={'include_numbers': True, 'font_size': 16, 'color': GRAY_B},
            y_axis_config={'include_numbers': False}, # No numbers on y-axis for wave amplitude
        )
        x_label = axes.get_x_axis_label(
            Text('ระยะทาง (m)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )

        # Wave function for standing wave envelope
        def wave_func(x):
            k = 2 * np.pi / lambda_val
            return 0.7 * np.sin(k * x) # 0.7 is amplitude for visualization

        wave_graph = axes.plot(wave_func, x_range=[x_min_wave, x_max_wave], color=TEAL_C)

        # Nodes (where y = 0)
        node_dots = VGroup()
        # Iterate to place nodes at 0, lambda/2, lambda, 3*lambda/2, ...
        for i in range(int(x_max_wave / (lambda_val / 2)) + 1):
            node_x = i * (lambda_val / 2)
            node_dot = Dot(axes.coords_to_point(node_x, 0), color=RED_C, radius=0.08)
            node_dots.add(node_dot)

        # Highlight two adjacent nodes for the answer
        # Let's pick the first two nodes after x=0 for clarity (at lambda/2 and lambda)
        node1_for_brace_pos = axes.coords_to_point(lambda_val/2, 0)
        node2_for_brace_pos = axes.coords_to_point(lambda_val, 0)

        brace_nodes = BraceBetweenPoints(node1_for_brace_pos, node2_for_brace_pos, direction=UP, buff=0.1)
        brace_label = MathTex(r'\\frac{\\lambda}{2}', font_size=22, color=GOLD_B).next_to(brace_nodes, UP, buff=0.1)
        brace_value_text = VGroup(
            MathTex(r'0.4', font_size=22, color=GOLD_B),
            Text(' m', font='TH Sarabun New', font_size=22, color=GOLD_B)
        ).arrange(RIGHT, buff=0.05).next_to(brace_label, UP, buff=0.1)

        # Group all visualization elements
        wave_viz_group = VGroup(axes, x_label, wave_graph, node_dots, brace_nodes, brace_label, brace_value_text)

        # Apply clamping to the entire visualization group
        wave_viz_group.scale_to_fit_width(frame_width * 0.88)
        wave_viz_group.scale_to_fit_height(middle_zone_height * 0.82)
        if wave_viz_group.width < frame_width * 0.55:
            wave_viz_group.scale_to_fit_width(frame_width * 0.55)
        if wave_viz_group.height < middle_zone_height * 0.55:
            wave_viz_group.scale_to_fit_height(middle_zone_height * 0.55)
        wave_viz_group.move_to(middle_center)

        self.play(Create(axes), Create(x_label))
        self.play(Create(wave_graph), GrowFromCenter(node_dots))
        self.play(Create(brace_nodes), Write(brace_label), Write(brace_value_text))
        self.wait(3)

        # --- Bottom Zone: Step 1 - Given Values ---
        step1_title = Text('ขั้นตอนที่ 1: ระบุค่าที่โจทย์กำหนด', font='TH Sarabun New', font_size=26, color=BLUE_D)
        given_f = VGroup(
            Text('ความถี่ (f) =', font='TH Sarabun New', font_size=26, color=GRAY_A),
            MathTex(r'500\,\mathrm{Hz}', font_size=26, color=GREEN_C)
        ).arrange(RIGHT, buff=0.1)
        given_v = VGroup(
            Text('อัตราเร็วคลื่น (v) =', font='TH Sarabun New', font_size=26, color=GRAY_A),
            MathTex(r'400\,\mathrm{m/s}', font_size=26, color=GREEN_C)
        ).arrange(RIGHT, buff=0.1)

        step1_group = VGroup(step1_title, given_f, given_v).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_group, shift=UP * 0.15))
        self.wait(3)

        # --- Bottom Zone: Step 2 - Calculate Wavelength (lambda) ---
        step2_title = Text('ขั้นตอนที่ 2: คำนวณความยาวคลื่น (λ)', font='TH Sarabun New', font_size=26, color=BLUE_D)
        formula_vfl = MathTex(r'v = f\lambda', font_size=26, color=ORANGE)
        sub_values = MathTex(r'400 = 500 \times \lambda', font_size=26, color=ORANGE)
        calc_lambda_eq = MathTex(r'\lambda = \frac{400}{500} = 0.8\,\mathrm{m}', font_size=26, color=GREEN_C)

        step2_group = VGroup(step2_title, formula_vfl, sub_values, calc_lambda_eq).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        self.play(FadeOut(step1_group, shift=DOWN * 0.1), FadeIn(step2_group, shift=UP * 0.15))
        self.wait(4)

        # --- Bottom Zone: Step 3 - Calculate Distance Between Nodes ---
        step3_title = Text('ขั้นตอนที่ 3: คำนวณระยะห่างระหว่างบัพ', font='TH Sarabun New', font_size=26, color=BLUE_D)
        # Rule 3: No Thai in MathTex. Split 'ระยะห่างบัพ' to Text.
        formula_dist_thai = VGroup(
            Text('ระยะห่างบัพ =', font='TH Sarabun New', font_size=26, color=ORANGE),
            MathTex(r'\frac{\lambda}{2}', font_size=26, color=ORANGE)
        ).arrange(RIGHT, buff=0.1)

        calc_dist_eq = MathTex(r'= \frac{0.8}{2} = 0.4\,\mathrm{m}', font_size=26, color=GREEN_C)

        final_answer_text = VGroup(
            Text('ดังนั้น ตำแหน่งบัพสองตำแหน่งที่อยู่ถัดกันจะห่างกัน', font='TH Sarabun New', font_size=26, color=GRAY_A),
            MathTex(r'0.4\,\mathrm{m}', font_size=26, color=GREEN_C)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

        step3_group = VGroup(step3_title, formula_dist_thai, calc_dist_eq, final_answer_text).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step3_group.scale_to_fit_width(frame_width * 0.88)
        step3_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step3_group.move_to(bottom_center)

        self.play(FadeOut(step2_group, shift=DOWN * 0.1), FadeIn(step3_group, shift=UP * 0.15))
        self.wait(5)

        # Final highlight of the answer on the visualization (replacing Indicate)
        answer_highlight = brace_value_text.copy().scale(1.2).set_color(YELLOW_C)
        self.play(FadeIn(answer_highlight, scale=1.2))
        self.wait(1)
        self.play(FadeOut(answer_highlight))
        self.wait(0.5)

        self.play(FadeOut(problem_text, shift=UP*0.1), FadeOut(wave_viz_group, shift=UP*0.1), FadeOut(step3_group, shift=DOWN*0.1))
        self.wait(0.5)