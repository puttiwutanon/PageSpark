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
        L2_string = 3.0 # meters
        lambda2 = 0.5 # meters
        lambda2_quarter = lambda2 / 4 # 0.125 meters
        lambda2_half = lambda2 / 2 # 0.25 meters

        nodes_from_antinode = []
        antinodes_from_antinode = []
        current_dist_node = lambda2_quarter
        current_dist_antinode = lambda2_half
        while current_dist_node <= L2_string:
            nodes_from_antinode.append(current_dist_node)
            current_dist_node += lambda2_half
        while current_dist_antinode < L2_string: # Fixed end is a node, so it cannot be an antinode at L2_string
            antinodes_from_antinode.append(current_dist_antinode)
            current_dist_antinode += lambda2_half

        nodes_str = ', '.join([f'{d:.3f}' for d in nodes_from_antinode])
        antinodes_str = ', '.join([f'{d:.2f}' for d in antinodes_from_antinode])

        # --- Mobjects for Hook ---
        problem_text = VGroup(
            Text('เชือกเส้นหนึ่งยาว 3 เมตร ปลายข้างหนึ่งยึดติดกับกำแพง', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('จับปลายอีกข้างหนึ่งสะบัดขึ้นลงอย่างสม่ำเสมอ ทำให้เกิดคลื่น', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('มีความยาวคลื่น 0.5 เมตร จงหาระยะห่างระหว่างปลายเส้นเชือก', font='TH Sarabun New', font_size=28, color=WHITE),
            Text('ที่สะบัดกับตำแหน่งบัพและปฏิบัพ', font='TH Sarabun New', font_size=28, color=WHITE)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        if problem_text.width > frame_width * 0.88:
            problem_text.scale_to_fit_width(frame_width * 0.88)
        if problem_text.height > top_zone_height * 0.88:
            problem_text.scale_to_fit_height(top_zone_height * 0.88)
        problem_text.move_to(top_center)

        # --- Mobjects for Diagram Explain ---
        # Generic standing wave diagram starting with an antinode on the right
        # String line (conceptual, not necessarily 3m length for this visualization)
        string_length_vis = 2.0 # Visual length for the diagram
        string_line_vis = Line(start=[-string_length_vis/2, 0, 0], end=[string_length_vis/2, 0, 0], color=GRAY_C, stroke_width=2)

        # Antinode at the right end of the visual string
        antinode_pos_vis = string_length_vis / 2
        vibrated_end_dot = Dot(point=[antinode_pos_vis, 0, 0], color=ORANGE, radius=0.08)
        vibrated_end_label = Text('ปลายสะบัด (ปฏิบัพ)', font='TH Sarabun New', font_size=18, color=ORANGE).next_to(vibrated_end_dot, RIGHT, buff=0.1)

        # Wave path (starting with antinode at the right, going left)
        # Use a cosine wave shifted so antinode is at x=antinode_pos_vis
        def wave_func_vis(x):
            # Adjust phase to have antinode at antinode_pos_vis
            # k = 2*pi/lambda. For antinode at x=0, use cos(kx). For antinode at x=L, use cos(k(x-L))
            # Let's make the antinode at the rightmost point of the visual string
            # and draw a few loops to the left.
            # A full wavelength is 0.5m. Let's show 2 wavelengths for clarity.
            # So, 2 * 0.5 = 1m. We want to show 2m length. So 4 wavelengths.
            # Let's use a simple cosine wave, where the rightmost point is an antinode.
            # x_relative = x - antinode_pos_vis
            # return 0.15 * np.cos(2 * np.pi * x_relative / lambda2)
            # Let's draw it from left to right, with antinode at the right.
            # So, it's a sine wave if fixed at left, or cosine if antinode at left.
            # Let's draw a wave that ends with an antinode on the right.
            # y(x) = A cos(k(L-x)) for antinode at L, node at 0.
            # Here, we want to show the pattern from an antinode. Let's make the antinode at x=0 for this visual.
            # And then shift the whole group.
            return 0.15 * np.cos(2 * np.pi * x / lambda2)

        # Draw from -2*lambda2 to 0 (where 0 is the antinode)
        wave_path_vis = ParametricFunction(lambda t: [t, wave_func_vis(t), 0], t_range=[-2*lambda2, 0], color=TEAL_C, stroke_width=4)
        wave_path_vis.shift(RIGHT * antinode_pos_vis)

        # Mark first Node and Antinode from the vibrated end (rightmost point)
        first_node_pos = antinode_pos_vis - lambda2_quarter
        first_antinode_pos = antinode_pos_vis - lambda2_half

        first_node_dot = Dot(point=[first_node_pos, 0, 0], color=BLUE_C, radius=0.08)
        first_node_label = Text('บัพ', font='TH Sarabun New', font_size=18, color=BLUE_C).next_to(first_node_dot, DOWN, buff=0.1)

        first_antinode_dot = Dot(point=[first_antinode_pos, 0, 0], color=ORANGE, radius=0.08)
        first_antinode_label = Text('ปฏิบัพ', font='TH Sarabun New', font_size=18, color=ORANGE).next_to(first_antinode_dot, UP, buff=0.1)

        # Braces for distances
        brace_lambda_quarter = Brace(Line([first_node_pos, 0, 0], [antinode_pos_vis, 0, 0]), direction=DOWN, buff=0.1)
        label_lambda_quarter = MathTex('\\frac{\lambda}{4}', font_size=18, color=GRAY_A).next_to(brace_lambda_quarter, DOWN, buff=0.1)

        brace_lambda_half = Brace(Line([first_antinode_pos, 0, 0], [antinode_pos_vis, 0, 0]), direction=UP, buff=0.1)
        label_lambda_half = MathTex('\\frac{\lambda}{2}', font_size=18, color=GRAY_A).next_to(brace_lambda_half, UP, buff=0.1)

        wave_diagram_group = VGroup(
            string_line_vis, wave_path_vis, vibrated_end_dot, vibrated_end_label,
            first_node_dot, first_node_label, first_antinode_dot, first_antinode_label,
            brace_lambda_quarter, label_lambda_quarter, brace_lambda_half, label_lambda_half
        )
        if wave_diagram_group.width > frame_width * 0.88:
            wave_diagram_group.scale_to_fit_width(frame_width * 0.88)
        if wave_diagram_group.height > middle_zone_height * 0.82:
            wave_diagram_group.scale_to_fit_height(middle_zone_height * 0.82)
        # Ensure it's not too small (BUG #4-ก)
        if wave_diagram_group.width < frame_width * 0.55:
            wave_diagram_group.scale_to_fit_width(frame_width * 0.55)
        if wave_diagram_group.height < middle_zone_height * 0.55:
            wave_diagram_group.scale_to_fit_height(middle_zone_height * 0.55)
        wave_diagram_group.move_to(middle_center)

        # --- Mobjects for Step 1 ---
        step1_title = VGroup(
            Text('ขั้นตอนที่ 1:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาระยะห่างจากปลายสะบัด (ปฏิบัพ) ไปยังบัพ', font='TH Sarabun New', font_size=26, color=GOLD_B)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        eq_nodes_general = MathTex('d_N = (2n-1)\\frac{\lambda}{4}', font_size=26, color=WHITE)
        eq_nodes_values = VGroup(
            Text('เมื่อ \\lambda = 0.5 m, จะได้ระยะห่าง (m):', font='TH Sarabun New', font_size=26, color=WHITE),
            Text(nodes_str, font='TH Sarabun New', font_size=26, color=GREEN_C)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        step1_group = VGroup(step1_title, eq_nodes_general, eq_nodes_values).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        if step1_group.width > frame_width * 0.88:
            step1_group.scale_to_fit_width(frame_width * 0.88)
        if step1_group.height > bottom_zone_height * 0.88:
            step1_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step1_group.move_to(bottom_center)

        # --- Mobjects for Step 2 ---
        step2_title = VGroup(
            Text('ขั้นตอนที่ 2:', font='TH Sarabun New', font_size=26, color=GOLD_B),
            Text('หาระยะห่างจากปลายสะบัด (ปฏิบัพ) ไปยังปฏิบัพอื่นๆ', font='TH Sarabun New', font_size=26, color=GOLD_B)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        eq_antinodes_general = MathTex('d_A = n\\frac{\lambda}{2}', font_size=26, color=WHITE)
        eq_antinodes_values = VGroup(
            Text('เมื่อ \\lambda = 0.5 m, จะได้ระยะห่าง (m):', font='TH Sarabun New', font_size=26, color=WHITE),
            Text(antinodes_str, font='TH Sarabun New', font_size=26, color=GREEN_C),
            Text('และที่ 3 เมตร คือตำแหน่งบัพ (ปลายตรึง)', font='TH Sarabun New', font_size=26, color=GRAY_A)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        step2_group = VGroup(step2_title, eq_antinodes_general, eq_antinodes_values).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        if step2_group.width > frame_width * 0.88:
            step2_group.scale_to_fit_width(frame_width * 0.88)
        if step2_group.height > bottom_zone_height * 0.88:
            step2_group.scale_to_fit_height(bottom_zone_height * 0.88)
        step2_group.move_to(bottom_center)

        # --- Mobjects for CTA ---
        cta_text = Text('ลองทบทวนและฝึกฝนเพิ่มเติมนะครับ!', font='TH Sarabun New', font_size=28, color=WHITE)
        if cta_text.width > frame_width * 0.88:
            cta_text.scale_to_fit_width(frame_width * 0.88)
        if cta_text.height > bottom_zone_height * 0.88:
            cta_text.scale_to_fit_height(bottom_zone_height * 0.88)
        cta_text.move_to(bottom_center)

        # --- Animations ---
        self.play(FadeIn(problem_text, shift=UP*0.15))
        self.wait(11.0)

        self.play(
            FadeOut(problem_text, shift=DOWN*0.1),
            Create(wave_diagram_group)
        )
        self.wait(12.5)

        self.play(FadeIn(step1_group, shift=UP*0.15))
        self.wait(18.5)

        self.play(
            FadeOut(step1_group, shift=DOWN*0.1),
            FadeIn(step2_group, shift=UP*0.15)
        )
        self.wait(20.0)

        self.play(
            FadeOut(wave_diagram_group, shift=DOWN*0.1),
            FadeOut(step2_group, shift=DOWN*0.1),
            FadeIn(cta_text, shift=UP*0.15)
        )
        self.wait(7.0)
        self.play(FadeOut(cta_text, shift=DOWN*0.1))