import os
import re
from pathlib import Path

import random
import string

def gen_random_title(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def red(text):
    return f"\033[31m{text}\033[0m"

level_map = {
    # document is 0,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
}

def add_to(data: dict, key: Path, line: str):
    # print(f"pwd: {key}") # !
    if key in data:
        data[key].append(line)
    else:
        data[key] = [line]

def fold(tex_path):
    tex_path = Path(tex_path)
    root_folder = tex_path.parent / f"{tex_path.stem}"
    root_folder.mkdir(exist_ok=True)
    lib_folder = root_folder / f"lib"
    lib_folder.mkdir(exist_ok=True)

    with tex_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    # Separate preamble and document ending
    section_re = re.compile(r"\\(?P<level>section|subsection|subsubsection)\*?\{(?P<title>.*?)\}.*")
    end_re = re.compile(r"\\end\{document\}")

    main_lines = []
    lib_data = {}
    pwd = lib_folder

    level = 0
    for line in lines:
        # print("=========================================") # !
        # print(f"line: {line}") # !
        # print(f"level: {level}") # !
        match = section_re.match(line.strip())
        if match:
            title = re.sub(r"[^\w\-]", "_", match.group("title")).strip("_")
            if title == "":
                title = gen_random_title()
            # print(f"match: {title}") # !
            new_level = level_map[match.group("level")]
            if new_level == 1:
                main_lines.append(line)
                main_lines.append(f"\\input{{lib/{title}/_.tex}}\n\n")
                pwd = lib_folder / title
                pwd.mkdir(exist_ok=True)
                level = new_level
                continue
            if new_level == level + 1:
                # from sec to subsec
                add_to(lib_data, pwd, line)
            elif new_level <= level:
                # from subsec to sec or subsec
                pwd = Path(*pwd.parts[:new_level - level - 1])
                add_to(lib_data, pwd, line)
            else:
                raise Exception("structure of latex is incorrect: e.g., subsubsec after sec")

            
            lib_data[pwd].append(f"\\input{{{pwd.relative_to(lib_folder).as_posix()}/{title}/_.tex}}\n")
            pwd = pwd / title
            pwd.mkdir(exist_ok=True)
            level = new_level
            
        else:
            if end_re.match(line.strip()):
                level = 0

            if level == 0:
                main_lines.append(line)
            else:
                add_to(lib_data, pwd, line)

    # Write main_file
    main_file = root_folder / "main.tex"
    with main_file.open("w", encoding="utf-8") as f:
        f.writelines(main_lines)


    # Write each section chunk
    for path, file_lines in lib_data.items():
        with Path(path / "_.tex").open("w", encoding="utf-8") as f:
            f.writelines(file_lines)

    print(f"折叠完成，输出写入: {main_file}")

def unfold(folder_path):
    folder_path = Path(folder_path)
    lib_path = folder_path / "lib"
    main_tex_path = folder_path / "main.tex"

    def unfold_lib_file(file_path):
        output = []
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("\\input{") and stripped.endswith("}"):
                    rel_input = stripped[len("\\input{"):-1]
                    input_path = (lib_path / rel_input).with_suffix(".tex")
                    if input_path.exists():
                        output.extend(unfold_lib_file(input_path))
                    else:
                        output.append(line + f"% Warning: missing file {input_path}")
                else:
                    output.append(line)
        return output

    with main_tex_path.open("r", encoding="utf-8") as f:
        output = []
        for line in f:
            stripped = line.strip()
            if stripped.startswith("\\input{") and stripped.endswith("}"):
                rel_input = stripped[len("\\input{"):-1]
                input_path = (folder_path / rel_input).with_suffix(".tex")
                if input_path.exists():
                    output.extend(unfold_lib_file(input_path))
                else:
                    output.append(line + f"% Warning: missing file {input_path}")
            else:
                output.append(line)

        
    output_file = folder_path.parent / "unfolded_main.tex"
    with output_file.open("w", encoding="utf-8") as f:
        f.writelines(output)
    print(f"反折叠完成，输出写入: {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage:\n  Fold:   python __main__.py fold <file.tex>\n  Unfold: python __main__.py unfold <folded_file.tex>")
    else:
        command, path = sys.argv[1], sys.argv[2]
        if command == "fold":
            fold(path)
        elif command == "unfold":
            unfold(path)
        else:
            print(f"Unknown command: {command}")