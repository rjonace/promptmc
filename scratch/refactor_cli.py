import re

with open("src/promptmc/cli.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_command = False
command_indent = 0
in_try = False
try_indent = 0

i = 0
while i < len(lines):
    line = lines[i]
    
    # Check for @app.command()
    if re.match(r'^@app\.command\(', line):
        new_lines.append(line)
        # Find def
        while not lines[i+1].strip().startswith("def "):
            i += 1
            new_lines.append(lines[i])
        
        # We are at def. Let's insert @_handle_errors right before it.
        new_lines.append("@_handle_errors\n")
        
        i += 1
        new_lines.append(lines[i])
        
        # Advance until we find docstring or try
        # Actually just let the loop handle it, but we need to track that we're inside a command.
        command_indent = len(lines[i]) - len(lines[i].lstrip())
        in_command = True
        
        i += 1
        continue

    # Find the top-level try inside command
    if in_command and not in_try and line.strip() == "try:":
        indent = len(line) - len(line.lstrip())
        if indent == command_indent + 4: # First level try
            in_try = True
            try_indent = indent
            i += 1
            continue
            
    # If we are inside the try block, unindent lines by 4 spaces until we hit an except matching the try's indent
    if in_try:
        indent = len(line) - len(line.lstrip())
        if line.strip().startswith("except ") and indent == try_indent:
            # Skip all except blocks
            while i < len(lines) and (lines[i].strip().startswith("except ") or (len(lines[i]) - len(lines[i].lstrip()) > try_indent) or not lines[i].strip()):
                if not lines[i].strip() and i + 1 < len(lines) and not lines[i+1].strip().startswith("except"):
                    # Break out if we hit an empty line that isn't followed by another except
                    break
                i += 1
            in_try = False
            in_command = False
            continue
        
        # Unindent
        if line.startswith(" " * 4):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
        i += 1
        continue
        
    new_lines.append(line)
    i += 1

# Prepend the decorator definition
decorator = """
from functools import wraps
from typing import Any, Callable

def _handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except OpenMCValidationError as e:
            console.print(f"[red]Validation error: {e}[/red]")
            raise typer.Exit(1) from e
        except OpenMCNotFoundError as e:
            console.print(f"[red]OpenMC not found: {e}[/red]")
            raise typer.Exit(1) from e
        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e
    return wrapper

"""

final_content = "".join(new_lines)
final_content = final_content.replace("app = typer.Typer(", decorator + "app = typer.Typer(")

with open("src/promptmc/cli.py", "w") as f:
    f.write(final_content)

