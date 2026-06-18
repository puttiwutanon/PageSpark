import subprocess
import os
import logging
import ast

logging.basicConfig(level=logging.INFO)


class Manim_Engine:
    def __init__(self, output_dir="renders"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def validate_code(self, code_string):
        """
        ตรวจสอบโค้ดที่ได้จาก LLM ก่อนรัน เพื่อป้องกันการเรียกใช้ฟังก์ชัน/โมดูลอันตราย
        ก่อน subprocess.run(['manim', ...]) จะถูกเรียก
        """
        forbidden_names = {
            'eval', 'exec', 'compile', '__import__',
            'os', 'sys', 'shutil', 'subprocess', 'open',
            'socket', 'requests', 'urllib', 'pathlib',
        }

        try:
            tree = ast.parse(code_string)
        except SyntaxError as e:
            return False, f"Code syntax is invalid: {e}"

        for node in ast.walk(tree):
            # import os / import os.path / import shutil, sys
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_module = alias.name.split(".")[0]
                    if root_module in forbidden_names:
                        return False, f"Forbidden import: {alias.name}"

            # from os import system / from os.path import join
            if isinstance(node, ast.ImportFrom):
                root_module = (node.module or "").split(".")[0]
                if root_module in forbidden_names:
                    return False, f"Forbidden import-from: {node.module}"

            # bare name usage: eval(...), exec(...), open(...)
            if isinstance(node, ast.Name) and node.id in forbidden_names:
                return False, f"Forbidden usage: {node.id}"

            # attribute access after aliasing, e.g. some_alias.system(...)
            # catches __import__('os').system(...) and similar patterns
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "__import__":
                    return False, "Forbidden usage: __import__"

        return True, "Code is safe"

    def write_scene_file(self, episode_data, filename):
        """เขียน Code ที่ได้รับจาก LLM ลงไฟล์ .py"""
        filepath = os.path.join(self.output_dir, filename)
        code_content = "\n".join(episode_data["manim_code_lines"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code_content)
        return filepath, code_content

    def render_episode(self, episode_data):
        """ตรวจสอบความปลอดภัยของโค้ดก่อน แล้วสั่งรัน Manim CLI เพื่อ Render วิดีโอ"""
        filename = f"scene_ep_{episode_data['episode_number']}.py"
        filepath, code_content = self.write_scene_file(episode_data, filename)

        # Validate BEFORE shelling out to manim -- this is the actual
        # security boundary since the code came from an LLM, not a developer.
        is_valid, msg = self.validate_code(code_content)
        if not is_valid:
            logging.error(f"Rejected episode {episode_data['episode_number']}: {msg}")
            # Clean up the rejected file so it doesn't linger on disk
            if os.path.exists(filepath):
                os.remove(filepath)
            return {"status": "error", "message": f"Validation failed: {msg}"}

        # คำสั่งรัน Manim (ใช้ -pql เพื่อความเร็วในการทดสอบ, ใช้ -qh สำหรับ Production)
        command = [
            "manim",
            "-pql",
            filepath,
            "PhysicsScene",  # ต้องตรงกับชื่อ class ในไฟล์
            "--media_dir", self.output_dir
        ]

        try:
            logging.info(f"Rendering episode {episode_data['episode_number']}...")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return {"status": "success", "output": result.stdout, "filepath": filepath}
        except subprocess.CalledProcessError as e:
            logging.error(f"Render Failed: {e.stderr}")
            return {"status": "error", "message": e.stderr}


# ตัวอย่างการใช้งาน
# engine = Manim_Engine()
# response = engine.render_episode(json_data['episodes'][0])