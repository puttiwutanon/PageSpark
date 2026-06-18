from manim import *

class Episode3Scene(Scene):
    def construct(self):
        self.camera.frame_width = 9
        self.camera.frame_height = 16
        self.camera.background_color = WHITE

        title = Text('ปาก้อนหินทำมุมจากตึกสูง', font='TH Sarabun New', color=BLACK).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # Building and person
        building_height = 3
        building_width = 1.5
        building = Rectangle(width=building_width, height=building_height, color=GRAY, fill_opacity=0.8)
        building.move_to(LEFT * 3 + DOWN * (self.camera.frame_height/2 - building_height/2 - 0.5))
        ground = Line(LEFT * self.camera.frame_width/2, RIGHT * self.camera.frame_width/2, color=GREEN, stroke_width=5)
        ground.move_to(DOWN * (self.camera.frame_height/2 - 0.5))
        
        person = Circle(radius=0.2, color=BLUE, fill_opacity=1).next_to(building, UP, buff=0).shift(RIGHT * building_width/2)
        initial_pos = person.get_center()
        
        sy_label = MathTex(r'S_y = 50 \text{ m}', color=BLUE).next_to(building, LEFT, buff=0.5)
        u_label = MathTex(r'U = 25 \text{ m/s}', color=RED).next_to(person, UP, buff=0.5)
        theta_label = MathTex(r'\theta = 37^\circ', color=RED).next_to(u_label, RIGHT, buff=0.2)

        self.play(Create(building), Create(ground), Create(person))
        self.play(Write(sy_label), Write(u_label), Write(theta_label))
        self.wait(1)

        # Initial velocity components
        ux_val = 25 * 0.8
        uy_val = 25 * 0.6
        ux_arrow = Arrow(initial_pos, initial_pos + RIGHT * (ux_val/10), color=ORANGE)
        uy_arrow = Arrow(initial_pos, initial_pos + UP * (uy_val/10), color=YELLOW)
        ux_text = MathTex(r'U_x = 20 \text{ m/s}', color=ORANGE).next_to(ux_arrow, RIGHT, buff=0.1)
        uy_text = MathTex(r'U_y = 15 \text{ m/s}', color=YELLOW).next_to(uy_arrow, UP, buff=0.1)

        self.play(Create(ux_arrow), Write(ux_text))
        self.play(Create(uy_arrow), Write(uy_text))
        self.wait(1)

        # Projectile path animation
        stone = Dot(color=RED).move_to(initial_pos)
        path = ArcBetweenPoints(initial_pos, initial_pos + RIGHT * 5 + DOWN * 5, angle=-TAU/8)
        path.set_color(PINK)
        self.play(Create(stone))
        self.play(MoveAlongPath(stone, path), run_time=3)
        self.wait(1)

        # Part A: Find time (t)
        part_a_title = Text('ส่วน ก: หาเวลา (t) ที่ตกถึงพื้น', font='TH Sarabun New', color=PURPLE, font_size=30).next_to(title, DOWN, buff=0.5).align_to(LEFT, LEFT)
        eq_t1 = MathTex(r'S_y = U_y t + \frac{1}{2} g t^2', color=BLUE).next_to(part_a_title, DOWN, buff=0.3).align_to(LEFT, LEFT)
        eq_t2 = MathTex(r'-50 = (15)t + \frac{1}{2} (-10) t^2', color=BLUE).next_to(eq_t1, DOWN, buff=0.1).align_to(LEFT, LEFT)
        eq_t3 = MathTex(r'-50 = 15t - 5t^2', color=BLUE).next_to(eq_t2, DOWN, buff=0.1).align_to(LEFT, LEFT)
        eq_t4 = MathTex(r'5t^2 - 15t - 50 = 0', color=BLUE).next_to(eq_t3, DOWN, buff=0.1).align_to(LEFT, LEFT)
        eq_t5 = MathTex(r't^2 - 3t - 10 = 0', color=BLUE).next_to(eq_t4, DOWN, buff=0.1).align_to(LEFT, LEFT)
        eq_t6 = MathTex(r'(t-5)(t+2) = 0 \Rightarrow t = 5 \text{ s}', color=BLUE).next_to(eq_t5, DOWN, buff=0.1).align_to(LEFT, LEFT)

        self.play(Write(part_a_title))
        self.play(Write(eq_t1), Write(eq_t2), Write(eq_t3), Write(eq_t4), Write(eq_t5), Write(eq_t6))
        self.wait(2.5)

        # Part B: Find horizontal distance (Sx)
        part_b_title = Text('ส่วน ข: หาระยะตกห่างจากตึก (Sx)', font='TH Sarabun New', color=PURPLE, font_size=30).next_to(eq_t6, DOWN, buff=0.5).align_to(LEFT, LEFT)
        eq_sx1 = MathTex(r'S_x = U_x t', color=ORANGE).next_to(part_b_title, DOWN, buff=0.3).align_to(LEFT, LEFT)
        eq_sx2 = MathTex(r'S_x = (20)(5)', color=ORANGE).next_to(eq_sx1, DOWN, buff=0.1).align_to(LEFT, LEFT)
        eq_sx3 = MathTex(r'S_x = 100 \text{ m}', color=ORANGE).next_to(eq_sx2, DOWN, buff=0.1).align_to(LEFT, LEFT)

        self.play(Write(part_b_title))
        self.play(Write(eq_sx1), Write(eq_sx2), Write(eq_sx3))
        self.wait(2)

        cta_text = Text('ลองเปลี่ยนมุมปาดูสิว่า เวลาและระยะทางจะเปลี่ยนไปอย่างไร!', font='TH Sarabun New', color=BLACK, font_size=28).next_to(eq_sx3, DOWN, buff=0.5)
        self.play(Write(cta_text))
        self.wait(1)