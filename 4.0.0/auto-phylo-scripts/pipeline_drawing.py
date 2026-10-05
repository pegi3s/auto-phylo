#!/usr/bin/env python3
import os
import re
import subprocess

pipeline_drawing_autop_version = "4.0.0"
pipeline_drawing_docker_version = "2.43.0"
pipeline_drawing_program_version = "2.43.0"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global pipeline_drawing_autop_version, pipeline_drawing_docker_version, pipeline_drawing_program_version

    config = read_config("dir", "pipeline_drawing_docker_c_version")
    data_dir = config["dir"]

    if config["pipeline_drawing_docker_c_version"]:
        pipeline_drawing_autop_version = "?"
        pipeline_drawing_docker_version = config["pipeline_drawing_docker_c_version"]
        pipeline_drawing_program_version = "?"

    with open("/data/pipeline") as f:
        pipeline_lines = [l for l in f.read().splitlines() if l.strip()]

    # cut -d' ' -f2/-f3: strict single-space-delimited fields
    fields = [l.split(" ") for l in pipeline_lines]
    input_list = sorted({f[1] for f in fields})
    output_list = sorted({f[2] for f in fields})

    # names that appear on exactly one side (input-only or output-only)
    combined = sorted(input_list + output_list)
    counts = {}
    for name in combined:
        counts[name] = counts.get(name, 0) + 1
    unique_list1 = sorted(name for name in combined if counts[name] == 1)

    # inputs that are also "exclusive" (never produced as an output = root inputs)
    combined2 = sorted(input_list + unique_list1)
    counts2 = {}
    for name in combined2:
        counts2[name] = counts2.get(name, 0) + 1
    seen, root_inputs = set(), []
    for name in combined2:
        if counts2[name] > 1 and name not in seen:
            root_inputs.append(name)
            seen.add(name)

    matched_lines = []
    for name in root_inputs:
        for line in pipeline_lines:
            if f" {name} " in line:
                matched_lines.append(line)

    pipeline_with_data = list(pipeline_lines)
    for line in matched_lines:
        third = line.split(" ")[1]
        pipeline_with_data.append(f"data data {third}")
    pipeline_with_data = sorted(set(pipeline_with_data))

    # disambiguate repeated command names with a "§N" suffix, in the style of the original bash script
    seen_counts = {}
    pipeline_mod = []
    for line in pipeline_with_data:
        first_word, second_word, third_word = line.split()[:3]
        count = seen_counts.get(first_word, 0)
        pipeline_mod.append(f"{first_word}§{count} {second_word} {third_word}")
        seen_counts[first_word] = count + 1

    edges = set()
    for o_line in pipeline_mod:
        o_first, _o_second, o_third = o_line.split()
        for n_line in pipeline_mod:
            n_first, n_second, _n_third = n_line.split()
            if n_second == o_third:
                edges.add(f"'{o_first}' '{n_first}'")

    py_lines = ["import graphviz", "dot = graphviz.Digraph('Pipeline')"]
    for edge in sorted(edges):
        value1, value2 = edge.split(" ", 1)
        if value1 != value2:
            py_lines.append(f"dot.edge({value1}, {value2})")
    py_lines.append("dot.format = 'svg'")
    py_lines.append("dot.render(directory='/data').replace('\\\\', '/')")

    with open("/data/pipeline.py", "w") as f:
        f.write("\n".join(py_lines) + "\n")

    subprocess.run(["docker", "run", "-v", f"{data_dir}:/data",
                    f"pegi3s/graphviz:{pipeline_drawing_docker_version}", "bash", "-c",
                    "cd /data && python3 pipeline.py"])

    os.remove("/data/pipeline.py")
    os.remove("/data/Pipeline.gv")

    svg_path = "/data/Pipeline.gv.svg"
    with open(svg_path) as f:
        content = f.read()
    with open(svg_path, "w") as f:
        f.write(re.sub(r"§[0-9]*", "", content))


if __name__ == "__main__":
    print("Drawing pipeline", flush=True)
    main()
