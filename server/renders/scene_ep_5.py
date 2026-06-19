from manim import *
import numpy as np

class Episode5(Scene):
    def construct(self):
        # Define screen zones
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
        
        # Problem statement (Top Zone)
        problem_text_p4a = Text('4. ชายคนหนึ่งยืนอยู่บนดาดฟ้าตึกสูง 50 เมตร แล้วปาก้อนหินออกไปในแนวทำมุมก้ม 37° กับแนวระดับ ด้วยความเร็ว 25 m/s', font='TH Sarabun New', color=WHITE)
        problem_text_p4b = Text('ข. ก้อนหินตกห่างจากตัวตึกเท่าใด', font='TH Sarabun New', color=WHITE)
        problem_text_p4a.scale_to_fit_width(frame_width * 0.9)
        problem_text_p4b.scale_to_fit_width(frame_width * 0.9)
        problem_text_p4a.move_to(top_zone_center * UP + 0.2 * UP)
        problem_text_p4b.next_to(problem_text_p4a, DOWN, buff=0.1)
        
        problem_group = VGroup(problem_text_p4a, problem_text_p4b)
        self.play(FadeIn(problem_group))
        self.wait(1)
        
        # Physics constants and given values (from previous episode)
        s_y_val = 50
        u_val = 25
        theta_val = 37 * DEGREES
        g_val = 10
        t_total = 5 # Calculated from Episode 4
        
        u_x_val = u_val * np.cos(theta_val) # approx 20
        u_y_val = -u_val * np.sin(theta_val) # approx -15
        
        # Axes setup (Middle Zone)
        s_x_final = u_x_val * t_total # 20 * 5 = 100
        x_max_needed = s_x_final * 1.2 
        y_max_needed = s_y_val * 1.2 
        
        axes_x_length = frame_width * 0.8
        axes_y_length = middle_zone_height * 0.8
        
        axes = Axes(
            x_range=[0, x_max_needed, 20],
            y_range=[0, y_max_needed, 10],
            x_length=axes_x_length,
            y_length=axes_y_length,
            axis_config={'color': GRAY, 'include_numbers': True}
        )
        axes.move_to(middle_zone_center * UP + (frame_width/2 - axes_x_length/2 - 0.5) * LEFT)
        
        x_label = axes.get_x_axis_label(Text('ระยะทางแนวราบ s_x (เมตร)', font='TH Sarabun New', color=WHITE).scale(0.6), edge=DOWN, direction=RIGHT)
        y_label = axes.get_y_axis_label(Text('ระยะทางแนวดิ่ง s_y (เมตร)', font='TH Sarabun New', color=WHITE).scale(0.6), edge=LEFT, direction=UP)
        
        axes_labels = VGroup(x_label, y_label)
        
        self.play(Create(axes), FadeIn(axes_labels))
        self.wait(0.5)
        
        # Building and stone path (re-create from previous episode)
        building_width = axes_x_length * 0.1
        building_height = axes.c2p(0, s_y_val)[1] - axes.c2p(0,0)[1]
        building = Rectangle(width=building_width, height=building_height, color=GRAY_D, fill_opacity=0.8)
        building.move_to(axes.c2p(0, s_y_val/2) + building_width/2 * LEFT)
        
        def projectile_path(t):
            x = u_x_val * t
            y = s_y_val + u_y_val * t - 0.5 * g_val * t**2
            return axes.c2p(x, y)
        
        path = ParametricFunction(projectile_path, t_range=[0, t_total, 0.01], color=BLUE)
        stone_dot = Dot(axes.c2p(s_x_final, 0), color=ORANGE, radius=0.1)
        
        self.play(FadeIn(building), Create(path), FadeIn(stone_dot))
        self.wait(1)
        
        # Display s_x value at impact
        s_x_line = DashedLine(axes.c2p(0, 0), axes.c2p(s_x_final, 0), color=GREEN)
        s_x_label = MathTex(r's_x = ?', color=GREEN).scale(0.7)
        s_x_label.next_to(s_x_line, DOWN, buff=0.2)
        
        self.play(Create(s_x_line), FadeIn(s_x_label))
        self.wait(1)
        
        # Calculations (Bottom Zone)
        calc_title = Text('ขั้นตอนการคำนวณ', font='TH Sarabun New', color=YELLOW).scale(0.8)
        calc_title.move_to(bottom_zone_top * UP + 0.5 * DOWN)
        self.play(FadeIn(calc_title))
        
        # Step 1: Find s_x from horizontal motion
        step1_text = Text('1. หาระยะทางแนวราบ (s_x):', font='TH Sarabun New', color=WHITE).scale(0.7)
        eq1 = MathTex(r's_x = u_x t', color=GREEN).scale(0.7)
        eq2 = MathTex(r's_x = (20)(5)', color=GREEN).scale(0.7)
        eq3 = MathTex(r's_x = 100 \text{ m}', color=GREEN).scale(0.7)
        
        calculations1 = VGroup(step1_text, eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        calculations1.move_to(bottom_zone_center * UP)
        
        self.play(FadeIn(step1_text))
        self.play(Write(eq1))
        self.play(TransformMatchingTex(eq1, eq2))
        self.play(TransformMatchingTex(eq2, eq3))
        self.wait(2)
        
        # Update s_x label on graph
        s_x_label_updated = MathTex(r's_x = 100 \text{ m}', color=GREEN).scale(0.7)
        s_x_label_updated.next_to(s_x_line, DOWN, buff=0.2)
        self.play(Transform(s_x_label, s_x_label_updated))
        self.wait(1)
        
        # Final Answer
        final_answer = Text('ดังนั้น ก้อนหินตกห่างจากตัวตึก 100 เมตร', font='TH Sarabun New', color=YELLOW).scale(0.8)
        final_answer.next_to(eq3, DOWN, buff=0.5)
        self.play(FadeIn(final_answer))
        self.wait(2)
        
        self.play(FadeOut(VGroup(problem_group, axes, axes_labels, building, path, stone_dot, s_x_line, s_x_label, s_x_label_updated, calc_title, calculations1, final_answer)))
        self.wait(1)