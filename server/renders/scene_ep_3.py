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

        # Problem 22 Data
        f1 = 120 # Hz
        f2 = 122 # Hz
        t_time = 1.2 # s

        # Calculations
        delta_f = f2 - f1 # 2 Hz
        delta_phi = 2 * PI * delta_f * t_time # 2 * PI * 2 * 1.2 = 4.8 * PI radians

        # --- Top Zone: Problem Statement ---
        problem_text = VGroup(
            Text('22. คลื่นต่อเนื่องสองขบวน มีความถี่ 120 Hz และ 122 Hz เริ่มเคลื่อนที่ออกจากจุดเดียวกัน', font='TH Sarabun New', font_size=28, color=GRAY_A),
            Text('ด้วยเฟสตรงกัน เมื่อเวลา 1.2 วินาที คลื่นทั้งสองจะมีเฟสต่างกันเท่าไร', font='TH Sarabun New', font_size=28, color=GRAY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center)
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(11.0) # Hook duration

        # --- Middle Zone: Two Waves Visualization ---
        # Axes for displacement vs time
        t_max_display = 1.2 # Display up to the given time
        y_amplitude = 0.5
        axes_time_two_waves = Axes(
            x_range=[0, t_max_display, 0.2],
            y_range=[-y_amplitude, y_amplitude, y_amplitude],
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
        x_label_time_two_waves = axes_time_two_waves.get_x_axis_label(
            Text('เวลา (s)', font='TH Sarabun New', font_size=18, color=GRAY_A),
            edge=DOWN, direction=DOWN, buff=0.35
        )
        y_label_time_two_waves = axes_time_two_waves.get_y_axis_label(
            Text('การกระจัด', font='TH Sarabun New', font_size=18, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.30
        )

        def wave_func1(t):
            return y_amplitude * np.sin(2 * PI * f1 * t)

        def wave_func2(t):
            return y_amplitude * np.sin(2 * PI * f2 * t)

        wave_graph1 = axes_time_two_waves.plot(wave_func1, x_range=[0, t_max_display, 0.001], color=BLUE_C)
        wave_graph2 = axes_time_two_waves.plot(wave_func2, x_range=[0, t_max_display, 0.001], color=ORANGE)

        label_f1 = VGroup(
            Text('f', font='TH Sarabun New', font_size=18, color=BLUE_C),
            MathTex(r'_1', font_size=18, color=BLUE_C),
            Text('= 120 Hz', font='TH Sarabun New', font_size=18, color=BLUE_C)
        ).arrange(RIGHT, buff=0.05).next_to(axes_time_two_waves.coords_to_point(t_max_display*0.2, y_amplitude*0.8), UP, buff=0.1)

        label_f2 = VGroup(
            Text('f', font='TH Sarabun New', font_size=18, color=ORANGE),
            MathTex(r'_2', font_size=18, color=ORANGE),
            Text('= 122 Hz', font='TH Sarabun New', font_size=18, color=ORANGE)
        ).arrange(RIGHT, buff=0.05).next_to(axes_time_two_waves.coords_to_point(t_max_display*0.8, y_amplitude*0.8), UP, buff=0.1)

        axes_group = VGroup(axes_time_two_waves, x_label_time_two_waves, y_label_time_two_waves)
        axes_group.scale_to_fit_width(frame_width * 0.88)
        axes_group.scale_to_fit_height(middle_zone_height * 0.82)
        if axes_group.width < frame_width * 0.55:
            axes_group.scale_to_fit_width(frame_width * 0.55)
        if axes_group.height < middle_zone_height * 0.55:
            axes_group.scale_to_fit_height(middle_zone_height * 0.55)
        axes_group.move_to(middle_center)

        self.play(Create(axes_time_two_waves), Write(x_label_time_two_waves), Write(y_label_time_two_waves))
        self.wait(0.8)
        self.play(Create(wave_graph1), Write(label_f1))
        self.play(Create(wave_graph2), Write(label_f2))
        self.wait(0.8)

        # Animate the waves over time to show phase difference building up
        line_at_t = axes_time_two_waves.get_vertical_line(axes_time_two_waves.coords_to_point(t_time, 0), color=GRAY_A, stroke_width=2, stroke_dash_offset=0.1)
        dot_f1 = Dot(axes_time_two_waves.coords_to_point(t_time, wave_func1(t_time)), color=BLUE_C, radius=0.08)
        dot_f2 = Dot(axes_time_two_waves.coords_to_point(t_time, wave_func2(t_time)), color=ORANGE, radius=0.08)
        
        self.play(Create(line_at_t), GrowFromCenter(dot_f1), GrowFromCenter(dot_f2))
        self.wait(11.0) # Hook duration, but also for visualization.

        # --- Bottom Zone: Calculations ---
        # Step 1: Phase formula
        step1_title = Text('ขั้นตอนที่ 1: หาสูตรเฟสของคลื่น', font='TH Sarabun New', font_size=26, color=BLUE_C)
        eq_phi = MathTex(r'\phi = 2\pi ft', font_size=26, color=GREEN_C)
        eq_phi1 = MathTex(r'\phi_1 = 2\pi f_1 t', font_size=26, color=BLUE_C)
        eq_phi2 = MathTex(r'\phi_2 = 2\pi f_2 t', font_size=26, color=ORANGE)

        step1_group = VGroup(step1_title, eq_phi, eq_phi1, eq_phi2).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step1_group.scale_to_fit_width(frame_width * 0.88)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        self.play(FadeIn(step1_title, shift=UP*0.15))
        self.wait(0.8)
        self.play(Write(eq_phi))
        self.wait(7.5) # phi formula duration
        self.play(Write(eq_phi1), Write(eq_phi2))
        self.wait(8.0) # phi1 phi2 duration

        # Step 2: Calculate Phase Difference (Δφ)
        self.play(FadeOut(step1_group, shift=DOWN*0.1))
        self.wait(0.5)

        step2_title = Text('ขั้นตอนที่ 2: หาเฟสที่ต่างกัน (Δφ)', font='TH Sarabun New', font_size=26, color=BLUE_C)
        eq_delta_phi_def = MathTex(r'\Delta\phi = |\phi_2 - \phi_1|', font_size=26, color=GREEN_C)
        eq_delta_phi_sub = MathTex(r'\Delta\phi = |2\pi f_2 t - 2\pi f_1 t|', font_size=26, color=GREEN_C)
        eq_delta_phi_factor = MathTex(r'\Delta\phi = 2\pi |f_2 - f_1| t', font_size=26, color=GREEN_C)
        eq_delta_phi_values = MathTex(r'\Delta\phi = 2\pi |122\,\mathrm{Hz} - 120\,\mathrm{Hz}| (1.2\,\mathrm{s})', font_size=26, color=GREEN_C)
        eq_delta_phi_calc = MathTex(r'\Delta\phi = 2\pi (2)(1.2) = 4.8\pi\,\mathrm{rad}', font_size=26, color=GREEN_C)

        step2_group = VGroup(step2_title, eq_delta_phi_def, eq_delta_phi_sub, eq_delta_phi_factor, eq_delta_phi_values, eq_delta_phi_calc).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        step2_group.scale_to_fit_width(frame_width * 0.88)
        step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        self.play(FadeIn(step2_title, shift=UP*0.15))
        self.wait(0.8)
        self.play(Write(eq_delta_phi_def))
        self.wait(6.0) # delta phi def duration
        self.play(Write(eq_delta_phi_sub))
        self.wait(0.8)
        self.play(TransformMatchingTex(eq_delta_phi_sub, eq_delta_phi_factor))
        self.wait(8.0) # delta phi factor duration
        self.play(Write(eq_delta_phi_values))
        self.wait(8.5) # delta phi values duration
        self.play(Write(eq_delta_phi_calc))
        self.wait(5.5) # delta phi calc duration

        # Final Answer
        final_answer_text = VGroup(
            Text('ดังนั้น เมื่อเวลาผ่านไป 1.2 วินาที คลื่นทั้งสอง', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('จะมีเฟสต่างกัน 4.8π เรเดียน', font='TH Sarabun New', font_size=26, color=GOLD_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        final_answer_text.scale_to_fit_width(frame_width * 0.88)
        final_answer_text.scale_to_fit_height(bottom_zone_height * 0.88)
        final_answer_text.move_to(bottom_center)

        self.play(FadeOut(step2_group, shift=DOWN*0.1))
        self.wait(0.5)
        self.play(FadeIn(final_answer_text, shift=UP*0.15))
        self.wait(6.5) # CTA duration
        self.wait(1.0) # Final pause