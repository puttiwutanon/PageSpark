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

        # Problem Statement
        problem_text_p4_b_thai = Text('4. ชายคนหนึ่งยืนอยู่บนดาดฟ้าตึกสูง 50 เมตร แล้วปาก้อนหินออกไปในแนวทำมุมก้ม 37 องศากับแนวระดับ ด้วยความเร็ว 25 เมตร/วินาที', font='TH Sarabun New', font_size=36, color=WHITE, line_spacing=1.2)
        problem_text_p4_b_part = Text('ข. ก้อนหินตกห่างจากตัวตึกเท่าใด', font='TH Sarabun New', font_size=36, color=GOLD_B, line_spacing=1.2)
        problem_text_p4_b = VGroup(problem_text_p4_b_thai, problem_text_p4_b_part).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        problem_text_p4_b.scale_to_fit_width(frame_width * 0.85)
        problem_text_p4_b.scale_to_fit_height(top_zone_height * 0.9)
        problem_text_p4_b.move_to(top_center)
        self.play(FadeIn(problem_text_p4_b, shift=UP*0.15))
        self.wait(1)

        # Middle Zone Visualization
        x_max_plot = 45 # Max horizontal distance (40m) + padding
        y_max_plot = 55 # Max vertical height (50m) + padding
        
        axes = Axes(
            x_range=[0, x_max_plot, 10],
            y_range=[0, y_max_plot, 10],
            x_length=frame_width * 0.75,
            y_length=middle_zone_height * 0.75,
            axis_config={'color': GRAY_C, 'stroke_width': 2, 'include_tip': True,
                         'tip_length': 0.2, 'tip_width': 0.12, 'include_numbers': True},
            x_axis_config={'font_size': 22, 'color': GRAY_B},
            y_axis_config={'font_size': 22, 'color': GRAY_B},
        )
        
        x_label = axes.get_x_axis_label(
            Text('ระยะทางแนวราบ (m)', font='TH Sarabun New', font_size=22, color=GRAY_A),
            edge=RIGHT, direction=DOWN, buff=0.15
        )
        y_label = axes.get_y_axis_label(
            Text('ความสูง (m)', font='TH Sarabun New', font_size=22, color=GRAY_A).rotate(90 * DEGREES),
            edge=LEFT, direction=LEFT, buff=0.1
        )
        
        # Projectile path: y(x) = 50 - 0.75x - x^2/80
        projectile_path = axes.plot(lambda x: 50 - 0.75*x - (x**2)/80, x_range=[0, 40], color=BLUE_D, stroke_width=3)
        
        start_dot = Dot(axes.c2p(0, 50), color=GOLD_B, radius=0.08)
        end_dot = Dot(axes.c2p(40, 0), color=RED_C, radius=0.08)
        
        # Sy line and label
        sy_line = DashedLine(axes.c2p(0, 50), axes.c2p(0, 0), color=GRAY_A, stroke_width=2)
        sy_label = MathTex(r'S_y = 50\,\mathrm{m}', color=GRAY_A, font_size=30).next_to(sy_line, LEFT, buff=0.1)
        
        # Sx line and label
        sx_line = DashedLine(axes.c2p(0, 0), axes.c2p(40, 0), color=GRAY_A, stroke_width=2)
        sx_label = MathTex(r'S_x = ?', color=GRAY_A, font_size=30).next_to(sx_line, DOWN, buff=0.1)
        
        axes_group = VGroup(axes, x_label, y_label, projectile_path, start_dot, end_dot,
                            sy_line, sy_label, sx_line, sx_label)
        axes_group.scale_to_fit_width(frame_width * 0.82)
        axes_group.scale_to_fit_height(middle_zone_height * 0.85)
        axes_group.move_to(middle_center)
        
        self.play(
            Create(axes), Create(x_label), Create(y_label),
            Create(sy_line), Write(sy_label),
            Create(projectile_path), GrowFromCenter(start_dot), GrowFromCenter(end_dot),
            run_time=3
        )
        self.play(
            Create(sx_line), Write(sx_label),
            run_time=1.5
        )
        self.wait(2)
        
        self.play(
            FadeOut(axes_group, shift=DOWN*0.1)
        )
        self.wait(1)

        # Bottom Zone Calculations
        step1_title_thai = Text('ขั้นตอนที่ 1: หาระยะทางที่ก้อนหินตกในแนวราบ', font='TH Sarabun New', color=GOLD_B, font_size=32)
        step1_title_sym = MathTex(r'(S_x)', color=GOLD_B, font_size=32)
        step1_title = VGroup(step1_title_thai, step1_title_sym).arrange(RIGHT, buff=0.15)
        
        eq1_1 = MathTex(r'S_x = U_x t', color=WHITE, font_size=36)
        eq1_2 = MathTex(r'S_x = (20)(2)', color=WHITE, font_size=36)
        eq1_3 = MathTex(r'S_x = 40\,\mathrm{m}', color=GREEN_C, font_size=36)
        
        step1_group = VGroup(step1_title, eq1_1, eq1_2, eq1_3).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        step1_group.scale_to_fit_width(frame_width * 0.85)
        step1_group.scale_to_fit_height(bottom_zone_height * 0.9)
        step1_group.move_to(bottom_center)
        
        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(4)
        self.play(FadeOut(step1_group, shift=DOWN*0.1), FadeOut(problem_text_p4_b, shift=UP*0.1))
        self.wait(1)