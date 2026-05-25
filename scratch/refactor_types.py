import os
import re

files_to_check = []
for root, _, files in os.walk("src/promptmc"):
    for file in files:
        if file.endswith(".py") and file != "_typing.py":
            files_to_check.append(os.path.join(root, file))

for filepath in files_to_check:
    with open(filepath, "r") as f:
        content = f.read()
    
    if "str | Path" in content or "Path | str" in content:
        # Import PathLike if not there
        if "from promptmc._typing import PathLike" not in content:
            content = content.replace("from typing import ", "from promptmc._typing import PathLike\nfrom typing import ")
            if "from promptmc._typing import PathLike" not in content:
                # Fallback: add to the top
                content = re.sub(r'^(import|from)', r'from promptmc._typing import PathLike\n\1', content, count=1, flags=re.MULTILINE)
        
        content = content.replace("str | Path", "PathLike")
        content = content.replace("Path | str", "PathLike")
        
        with open(filepath, "w") as f:
            f.write(content)

