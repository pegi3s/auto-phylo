#!/usr/bin/env python3
import os
import shutil
import subprocess
import urllib.request

from module_utils import resolve_module_path

pre_main_autop_version = "4.0.0"

def strip_cr(path):
    with open(path, "rb") as f:
        content = f.read()
    with open(path, "wb") as f:
        f.write(content.replace(b"\r", b""))


def main():
    strip_cr("/data/pipeline")
    strip_cr("/data/config")

    with open("/data/pipeline") as f:
        pipeline_lines = f.read().splitlines()
    check_pipeline = pipeline_lines[0] if pipeline_lines else ""

    if check_pipeline == "pipeline_drawing":
        print("Drawing the pipeline")
        os.makedirs("/data/files_to_keep", exist_ok=True)
        with open("/data/pipeline", "w") as f:
            f.write("\n".join(pipeline_lines[1:]) + ("\n" if len(pipeline_lines) > 1 else ""))
        subprocess.run([resolve_module_path("pipeline_drawing")])
        with open("/data/pipeline") as f:
            rest = f.read()
        with open("/data/pipeline", "w") as f:
            f.write("pipeline_drawing\n" + rest)
        shutil.rmtree("/data/files_to_keep")

    elif check_pipeline == "protocol_description":
        print("Please see the generated protocol description file")
        url = "http://evolution6.i3s.up.pt/static/pegi3s/dockerfiles/auto-phylo_protocols/protocol_description"
        try:
            urllib.request.urlretrieve(url, "/data/protocol_description")
        except Exception:
            pass

    elif "protocol" in check_pipeline:
        for line in pipeline_lines:
            print("Copying the protocol folder", line)
            # sanitize against path traversal since the protocol name comes from the pipeline file
            name = os.path.basename(line)
            url = f"http://evolution6.i3s.up.pt/static/pegi3s/dockerfiles/auto-phylo_protocols/{name}.zip"
            try:
                urllib.request.urlretrieve(url, f"/data/{name}.zip")
            except Exception:
                pass

    else:
        for line in pipeline_lines:
            command = line.split()[0]
            if resolve_module_path(command) is None:
                print("This is an invalid command:", command)
                return
        subprocess.run([resolve_module_path("main")])


if __name__ == "__main__":
    main()
